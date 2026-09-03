# -------------------------------------------------------------------------------
# FDE context: latest event per entity
# -------------------------------------------------------------------------------
#
# This hash-map pattern answers:
#
#     "For each entity, what is the newest event according to the defined
#     ordering rule?"
#
# In this example:
#
#     entity_id -> event with greatest timestamp seen so far
#
# The Python implementation is useful for a coding interview, a bounded log
# export, a small local investigation, a backfill test, or an in-memory batch.
# In production, the same logical problem is usually pushed to a database,
# analytics platform, stream processor, or durable materialized-state service.
#
# -------------------------------------------------------------------------------
# Common FDE use cases
# -------------------------------------------------------------------------------
#
# 1. Logs and service telemetry
#
#     entity_id = service_id, resource_id, device_id, endpoint, tenant_id
#
# Questions:
# - What is the latest reported health state for every service?
# - What is the most recent configuration/deployment event for each resource?
# - What is the latest known customer-impacting error for each tenant?
#
# Important:
# "Latest event" is not always equivalent to "current health." A later success
# may not mean an incident is resolved. Health often requires a state machine,
# rolling error-rate calculation, alert lifecycle, or explicit resolution event.
#
# 2. Customer support and incident investigation
#
#     entity_id = customer_id, tenant_id, support_case_id, incident_id
#
# Questions:
# - What was the latest observed status for this customer during an incident?
# - What is the latest diagnostic event attached to each support case?
# - Which customers were last affected by a deployment, dependency, or outage?
#
# Preserve trace_id, correlation_id, deployment version, region, and source
# timestamp so the "latest" result leads to inspectable evidence.
#
# 3. AI-agent runs
#
#     entity_id = agent_run_id
#
# Questions:
# - What is the latest state of each agent run?
# - Which runs are completed, failed, waiting for approval, or still in progress?
# - Which run should an operator inspect or resume?
#
# Typical states:
#
#     STARTED
#     MODEL_IN_PROGRESS
#     TOOL_CALL_IN_PROGRESS
#     WAITING_FOR_APPROVAL
#     COMPLETED
#     FAILED
#     CANCELLED
#     MAX_ITERATIONS_EXCEEDED
#
# 4. Agent tool calls
#
#     entity_id = tool_call_id
#
# Questions:
# - What is the latest/terminal result of each tool invocation?
# - Which calls are still pending, retried, failed, or completed?
# - Which customer workflows have an unresolved external side effect?
#
# Use agent_run_id to track an entire run and tool_call_id to track an individual
# tool invocation. Retain trace_id to correlate both with downstream logs.
#
# 5. Customer workflows and business processes
#
#     entity_id = workflow_id, order_id, case_id, subscription_id, job_id
#
# Questions:
# - What is the latest state of each onboarding workflow?
# - Which orders are paid but not fulfilled?
# - Which subscriptions have the newest entitlement update?
# - Which jobs are stuck in PENDING or RUNNING?
#
# 6. Configuration, inventory, and deployment state
#
#     entity_id = tenant_id + resource_id, configuration_id, deployment_id
#
# Questions:
# - What is the latest deployed version for each customer resource?
# - Which configuration was most recently applied to each tenant?
# - Which deployment action last changed a customer's environment?
#
# -------------------------------------------------------------------------------
# Critical FDE contract questions
# -------------------------------------------------------------------------------
#
# Before writing the algorithm or query, define:
#
# - What is the entity key: tenant, service, resource, request, trace, agent run,
#   tool call, workflow, case, order, or another business identity?
# - What does "latest" mean: event time, ingestion/arrival time, processing time,
#   most recent successful event, or highest authoritative source version?
# - Can events arrive late, out of order, be duplicated, replayed, or corrected?
# - How should equal timestamps be resolved: event_id, source sequence number,
#   version, source priority, or deterministic arrival order?
# - Can an older timestamp be authoritative because it is a correction with a
#   higher source version?
# - Is this a historical query or a customer-facing current-state view?
# - What state retention, freshness, authorization, audit, and PII controls apply?
#
# Timestamps alone are often insufficient. A production comparison may use:
#
#     (event_timestamp, source_version, source_priority, event_id)
#
# instead of only:
#
#     event_timestamp
#
# -------------------------------------------------------------------------------
# Python limitations versus production implementation
# -------------------------------------------------------------------------------
#
# This Python dictionary is an in-memory, process-local materialized view:
#
#     entity_id -> latest event
#
# It is not a durable production state store.
#
# Python dictionary limitations:
#
# - State disappears on process restart, crash, deployment, or eviction.
# - All retained entities must fit in one process's memory.
# - It has no built-in checkpointing, replay, persistence, replication, backup,
#   transaction isolation, distributed locking, access control, or audit trail.
# - It has no event-time watermark, late-event policy, bounded state expiry, or
#   automatic correction/revision semantics.
# - It assumes application code handles malformed data, key normalization,
#   tenant isolation, deduplication, versioning, concurrency, and conflicts.
# - It is appropriate only when the input is a finite batch or state can safely
#   remain local and ephemeral.
#
# -------------------------------------------------------------------------------
# Production alternatives
# -------------------------------------------------------------------------------
#
# 1. SQL database: latest row per group
#
# Use a window function when events are stored in SQL:
#
#     ROW_NUMBER() OVER (
#         PARTITION BY entity_id
#         ORDER BY event_timestamp DESC, event_id DESC
#     )
#
# Filter to row_number = 1 to return the newest record for each entity.
#
# 2. MongoDB: aggregation pipeline
#
# Sort newest-first, then group by entity_id and preserve the first document:
#
#     $sort  -> entity_id ascending, timestamp descending, event_id descending
#     $group -> _id: "$entity_id", latest_event: { $first: "$$ROOT" }
#
# 3. Analytics/log platform
#
# Use Azure Data Explorer, Log Analytics, a warehouse, or a lakehouse when
# analyzing high-volume logs, traces, telemetry, customer usage, or incidents.
# Push filtering, grouping, joining, and aggregation close to the stored data
# instead of loading the complete event history into one Python process.
#
# 4. Durable current-state/materialized view
#
# For repeatedly queried current state, write an indexed record such as:
#
#     tenant_id + entity_id -> latest validated state, version, timestamp,
#                               trace_id, updated_at
#
# This supports support portals, workflow dashboards, operations tooling, and
# low-latency customer-scoped reads without recomputing raw event history.
#
# 5. Stream processing
#
# For a continuous event stream:
#
#     durable ingestion
#       -> partitioned consumer/stream processor
#       -> event-time window/lateness policy
#       -> durable/checkpointed state
#       -> materialized current-state view or analytics output
#
# Define:
# - Partition key and hot-key/skew behavior.
# - Event-time versus ingestion-time semantics.
# - State retention and expiry.
# - Late/out-of-order event policy and whether outputs are revised.
# - Duplicate/replay/idempotency behavior.
# - Recovery, replay, checkpointing, and reconciliation procedures.
#
# -------------------------------------------------------------------------------
# Indexing and query design
# -------------------------------------------------------------------------------
#
# For a tenant-scoped "latest per entity" query, a useful conceptual index is:
#
#     (tenant_id, entity_id, event_timestamp DESC, event_id DESC)
#
# Why:
# - tenant_id enforces/query-scopes customer data.
# - entity_id identifies the group.
# - timestamp supports newest-first ordering.
# - event_id creates deterministic ordering when timestamps tie.
#
# Exact index design depends on database engine, query patterns, cardinality,
# write rate, retention, and tenant-isolation architecture.
#
# -------------------------------------------------------------------------------
# Important distinction: latest raw event vs current valid state
# -------------------------------------------------------------------------------
#
# "Latest raw event" is not automatically "current valid business state."
#
# Example:
#
#     PENDING -> RUNNING -> COMPLETED
#
# A late/replayed RUNNING event should not necessarily overwrite a completed
# workflow state merely because it arrives later. For workflows, payments,
# entitlements, permissions, incidents, and agent side effects:
#
# - Validate allowed state transitions.
# - Use durable idempotency/deduplication state.
# - Apply authoritative versions/source rules.
# - Preserve history and audit evidence.
# - Define correction and reconciliation behavior.
#
# FDE summary:
#
#     Python hash map
#         -> demonstrates "latest row per entity" in a bounded batch
#
#     Database/analytics query
#         -> computes latest records efficiently near durable data
#
#     Durable state machine/materialized view
#         -> represents customer-facing current state safely in production
#

events = [
    {
        "entity_id": "contoso",
        "timestamp": 100,
        "status": "provisioning",
    },
    {
        "entity_id": "fabrikam",
        "timestamp": 110,
        "status": "active",
    },
    {
        "entity_id": "contoso",
        "timestamp": 120,
        "status": "active",
    },
    {
        "entity_id": "contoso",
        "timestamp": 105,
        "status": "pending_review",
    },
    {
        "entity_id": "fabrikam",
        "timestamp": 125,
        "status": "suspended",
    },
]
latest_by_entity = {}

for event in events:
    entity_id = event["entity_id"]
    current_latest = latest_by_entity.get(entity_id)

    if (current_latest is None or 
        event["timestamp"] > current_latest["timestamp"] 
    ):
        latest_by_entity[entity_id] = event

print(latest_by_entity)