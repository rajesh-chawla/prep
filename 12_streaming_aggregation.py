
# Streaming Aggregation — Python and FDE Design Notes
#
# This file records the questions and architecture decisions to clarify before
# turning a simple in-memory Python aggregation into a production streaming
# system. The basic aggregation logic stays similar; production requirements
# determine how events, state, windows, recovery, and outputs are handled.
#
# -----------------------------------------------------------------------------
# Core Python aggregation pattern
# -----------------------------------------------------------------------------
# - Initialize a record when an aggregation key is first seen.
# - For each incoming event, increment its count and running total.
# - Derive values such as average from total / count.
# - An in-memory dict is appropriate for learning, a demo, or a small,
#   single-process workload. It is not durable across restarts and is not a
#   safe shared state store across multiple workers.
#
# Example shape of in-memory state:
#
# summary = {
#     "coffee": {
#         "count": 2,
#         "total": 9.50,
#         "average": 4.75,
#     },
#     "tea": {
#         "count": 2,
#         "total": 6.50,
#         "average": 3.25,
#     },
# }
#
# -----------------------------------------------------------------------------
# 1. Input scale and key distribution
# -----------------------------------------------------------------------------
# Questions:
# - What are the average and peak event rates?
# - What are payload sizes, burst patterns, and total daily volume?
# - How many distinct aggregation keys are expected?
# - Are keys evenly distributed, or are there hot keys that receive a large
#   share of traffic?
#
# Why it matters:
# - Determines event-bus throughput, partition count, consumer parallelism,
#   backlog/lag behavior, state size, and recovery/checkpoint capacity.
# - Key skew matters: one hot key can overload a partition even if total system
#   throughput is manageable.
# - Scale constrains feasible window duration and allowed lateness because both
#   increase the amount of active aggregation state that must be retained.
#
# -----------------------------------------------------------------------------
# 2. Aggregation semantics and time windows
# -----------------------------------------------------------------------------
# Questions:
# - What is the aggregation key: product, customer, account, device, region?
# - Is the aggregation all-time, tumbling, sliding, session-based, or rolling?
# - What is the window duration: one minute, five minutes, one hour, one day?
# - Which timezone defines window boundaries?
# - When should results be emitted: continuously, periodically, at window close,
#   or only after a window is final?
#
# Why it matters:
# - The window defines the business meaning of an aggregate and bounds state.
# - An all-time aggregate can grow indefinitely as new keys arrive.
# - Business requirements determine the desired window; infrastructure scale
#   determines whether that window is practical and affordable.
#
# -----------------------------------------------------------------------------
# 3. Out-of-order events and lateness
# -----------------------------------------------------------------------------
# Questions:
# - Is order guaranteed, especially within one aggregation key?
# - Does the business use event time (when an event happened) or processing time
#   (when the consumer processes it)?
# - How late can an event arrive and still be included in its original window?
# - Should a valid late event revise a previously emitted result?
# - What happens to events beyond the allowed-lateness threshold: discard, store
#   separately, or reconcile later?
#
# Why it matters:
# - Event-time aggregation keeps an event in the window where it actually
#   occurred, even if it arrives late.
# - Streaming engines commonly use watermarks to measure progress in event time,
#   finalize old windows, and eventually clean up their state.
# - Longer allowed lateness improves late-data correctness but increases retained
#   state and delays a truly final result.
#
# -----------------------------------------------------------------------------
# 4. Input data contract and schema evolution
# -----------------------------------------------------------------------------
# Questions:
# - What fields are required for every event?
# - Which fields represent event ID, event timestamp, aggregation key, and
#   numeric value or amount?
# - How are invalid, missing, malformed, or impossible values handled?
# - Is the schema owned and versioned by producers?
# - Can fields be added, removed, renamed, or changed in type?
# - Can field meaning change, such as currency, timestamp definition, or product
#   identifier format?
#
# Why it matters:
# - Malformed or semantically changed data can silently corrupt aggregates.
# - A stable event_id supports deduplication and replay safety.
# - Use a versioned contract (for example, JSON Schema, Avro, or Protobuf) and
#   compatibility rules. Different schema versions may require normalization
#   before their events can be safely aggregated together.
#
# Example event envelope:
#
# {
#     "event_id": "3e4b5e37-0cb9-4df3-82c8-57b46e0e7c16",
#     "schema_version": 1,
#     "event_time": "2026-09-03T16:12:04Z",
#     "product_id": "coffee",
#     "amount": 4.50,
#     "currency": "USD",
# }
#
# -----------------------------------------------------------------------------
# 5. State and output storage
# -----------------------------------------------------------------------------
# Questions:
# - Where does active aggregation state live: process memory, a state store,
#   database, or another durable system?
# - Where are materialized/final aggregates written?
# - Who reads the output: a dashboard, API, downstream pipeline, finance/audit,
#   or ad hoc analytics users?
# - How long are raw events, active state, aggregates, corrections, and late
#   event records retained?
#
# Why it matters:
# - In-memory state is easy to demonstrate but disappears on restart and cannot
#   safely coordinate state between multiple worker instances.
# - Separate raw-event storage from materialized aggregate storage. Raw data is
#   useful for debugging, auditability, backfills, reconciliation, and rebuilding
#   aggregates after a logic or schema change.
#
# -----------------------------------------------------------------------------
# 6. Failure, delivery, and replay
# -----------------------------------------------------------------------------
# Questions:
# - What delivery guarantee does the source provide: at-most-once,
#   at-least-once, or exactly-once/effectively-once?
# - Can the source retain and replay events after a failure?
# - Are events uniquely identified with an event_id for deduplication?
# - Are output writes idempotent, so a replay does not double-count?
# - How are stream position and aggregation state checkpointed and restored?
# - How far back must raw events be retained for troubleshooting, reconciliation,
#   auditability, and backfills?
#
# Important distinction:
# - Recovery resumes safely after a worker, deployment, or infrastructure failure.
# - Replay/audit reproduces or investigates results from retained raw history.
#
# A useful aggregate output key can be:
#     (window_start_utc, window_end_utc, product_id)
#
# This enables idempotent upserts and corrections when late events change a
# previously emitted window aggregate.
#
# -----------------------------------------------------------------------------
# 7. Tool choices: Azure-oriented reference architecture
# -----------------------------------------------------------------------------
# Event bus / ingestion: Azure Event Hubs
# - Use for high-throughput event ingestion, buffering, partitions, retention,
#   and multiple independent consumer groups.
# - Event Hubs moves and retains events. It is not itself the component that
#   performs stateful window aggregation, deduplication, or late-event handling.
#
# Stream-processing layer: Azure Stream Analytics (first managed option)
# - Use for straightforward SQL-like filters, joins, event-time windows, and
#   aggregations with managed operations.
# - This is the layer that implements group-by/window calculations, late-data
#   policy, and output emission for a basic streaming design.
# - Consider Databricks/Spark Structured Streaming for larger-scale or more
#   complex transformations, enrichment, lakehouse workflows, or existing Spark
#   expertise.
# - Consider Azure Functions for light per-event work, but do not assume they are
#   the best primary engine for high-volume, stateful windowed aggregation.
# - Consider Apache Flink when advanced event-time and stateful processing needs
#   justify its additional operational complexity.
#
# Raw-event archive: ADLS Gen2 or Azure Blob Storage
# - Keep an immutable, durable raw-event copy independent of the aggregate.
# - Use it for debugging, auditability, reconciliation, backfills, and rebuilding
#   aggregates after logic or contract changes.
# - Event Hubs Capture or a separate Event Hubs consumer can land raw data here.
# - Do not make a short-retention event bus or a materialized aggregate table the
#   only source of historical truth.
#
# Relational aggregate store: PostgreSQL, SQL Server, or Azure SQL
# - Good choice for small-to-medium materialized aggregate tables, transactional
#   requirements, relational queries, APIs, and familiar Power BI integration.
# - Avoid assuming a relational database is the best target for sustained,
#   high-rate per-event writes. Store raw events separately and write aggregate
#   updates in a designed, idempotent pattern.
#
# High-throughput / distributed serving store: MongoDB or Azure Cosmos DB
# - Consider when access patterns use documents, very high write/read throughput,
#   low latency, horizontal scale, or global distribution.
# - Choose based on required data model, consistency, query pattern, partitioning,
#   operational model, and cost--not simply because the input rate is high.
# - Cosmos DB may be the Azure-native option when its capabilities fit the team's
#   platform and operational requirements.
#
# Analytics / historical query layer: lakehouse or warehouse
# - For large-scale historical scans, analytics, backfills, and reporting, use an
#   appropriate analytical platform such as Databricks + Delta Lake, Microsoft
#   Fabric, Synapse, or the organization's chosen warehouse/lakehouse.
# - This is distinct from an operational serving database for current aggregate
#   results.
#
# Visualization: Power BI
# - Use Power BI for dashboards, exploration, and presenting near-real-time or
#   historical aggregate results.
# - Power BI should consume materialized aggregate output from the stream
#   processor or analytics store; it should not be treated as the canonical
#   aggregation engine or system of record.
#
# Logs, metrics, traces, and alerting: Azure Monitor + Log Analytics
# - Use Log Analytics for centralized application/platform logs, diagnostics,
#   operational queries, and alert rules.
# - Monitor input rate, consumer lag, processing latency, invalid events,
#   duplicates, late events, state size, checkpoint health, output failures, and
#   partition/key skew.
#
# Application telemetry: Application Insights
# - Instrument producers, stream consumers, APIs, and workers for requests,
#   dependencies, exceptions, custom metrics, and distributed traces.
# - Application Insights integrates with Azure Monitor and Log Analytics, so use
#   them together rather than as alternatives.
#
# Schema/governance and bad-event handling
# - Add a versioned schema/contract registry or equivalent governance process.
# - Validate events near ingestion where practical.
# - Send malformed or incompatible events to a dead-letter/quarantine destination
#   with enough context to investigate and replay after correction.
#
# -----------------------------------------------------------------------------
# Reference data flow
# -----------------------------------------------------------------------------
# Event-producing applications/services
#     |
#     |-- Application Insights instrumentation
#     v
# Azure Event Hubs
#     |
#     |-- Raw-event capture --> ADLS Gen2 / Blob Storage
#     |
#     |-- Stream-processing consumer --> Azure Stream Analytics
#     |       |-- validate/normalize event contract
#     |       |-- event-time window aggregation
#     |       |-- allowed-lateness / late-event policy
#     |       |-- deduplication and recovery strategy
#     |       v
#     |   Aggregate serving store --> Azure SQL / PostgreSQL / Cosmos DB
#     |       |-- Power BI dashboards
#     |       `-- APIs and downstream consumers
#     |
#     `-- Optional independent consumers for audit, diagnostics, or backfills
#
# Producers, processors, databases, and APIs
#     `-- Azure Monitor / Log Analytics / Application Insights
#
# -----------------------------------------------------------------------------
# Practical first architecture for this sales-aggregation example
# -----------------------------------------------------------------------------
# Event Hubs
#     --> Azure Stream Analytics
#     --> Azure SQL or PostgreSQL (materialized window/product aggregates)
#     --> Power BI
#
# In parallel:
# Event Hubs Capture --> ADLS Gen2 / Blob Storage (durable raw event history)
#
# Reassess the stream processor and serving store if cardinality, update rate,
# latency, global distribution, or transformation complexity increases

sales = [
    ("coffee", 4.50),
    ("tea", 3.25),
    ("coffee", 5.00),
    ("muffin", 2.75),
    ("tea", 3.25),
]

"""
Output:
{
    "coffee": {"count": 2, "total": 9.5, "average": 4.75},
    "tea": {"count": 2, "total": 6.5, "average": 3.25},
    "muffin": {"count": 1, "total": 2.75, "average": 2.75},
}
"""

from collections import Counter

def aggregate_sales(sales: list[tuple[str, float]]) -> dict[str, dict[str, float]]:
    summary = {}

    for product, amount in sales:
        if product not in summary:
            summary[product] = {
                "count" : 0,
                "total": 0.0,
                "average": 0.0
            }
        summary[product]["count"] += 1
        summary[product]["total"] += amount

    for key, value in summary.items():
        value["average"] = value["total"] / value["count"]

    return summary