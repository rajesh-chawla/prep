# Dataset Join: CRM Customers + Billing Accounts
#
# Goal:
# Perform a full outer join using customer_id as the shared key.
#
# Full outer join contract:
# - Include every customer/account found in either source.
# - For matching IDs, return both the CRM and billing records.
# - For CRM-only IDs, return the CRM record and billing=None.
# - For billing-only IDs, return crm=None and the billing record.
#
# Example output:
#
#     {
#         "customer_id": "contoso",
#         "crm": {...},
#         "billing": {...},
#     }
#
#     {
#         "customer_id": "adventure-works",
#         "crm": {...},
#         "billing": None,
#     }
#
# -------------------------------------------------------------------------------
# Interview explanation
# -------------------------------------------------------------------------------
#
# - I index each collection by customer_id using a hash map.
# - I take the union of customer IDs from both maps.
# - For each ID, I look up the CRM and billing records independently.
# - A missing lookup becomes None, preserving unmatched records from either source.
# - This implements a full outer join in O(n + m) expected time, where n and m
#   are the collection sizes.
# - The current implementation assumes at most one record per customer_id in each
#   input and does not impose a business-defined output order.
#
# -------------------------------------------------------------------------------
# Where an FDE sees this pattern
# -------------------------------------------------------------------------------
#
# Dataset joins are common when customer data exists in multiple systems and an
# FDE needs a unified view or a reconciliation report.
#
# Customer/account reconciliation:
# - CRM customer records joined with billing/subscription accounts.
# - Entitlements joined with identity/account records.
# - Customer configuration joined with deployed-resource inventory.
# - Customer onboarding records joined with actual provisioned resources.
#
# Support and incident investigation:
# - Support cases joined with CRM account/plan/owner information.
# - Error/trace events joined with customer, deployment, region, or version data.
# - Agent-run traces joined with tool configuration, permissions, and connector
#   status to determine why a customer workflow failed.
#
# Data ingestion and integration:
# - Partner source exports joined with internal canonical records.
# - Orders joined with payments, fulfillment, invoices, or shipment state.
# - Webhook events joined with the internal entity they should update.
# - Data-lake records joined with reference data or dimension tables.
#
# Security and governance:
# - Identities joined with role assignments, entitlements, tenant boundaries, or
#   audit events.
# - A full outer join can reveal orphaned accounts, missing entitlement records,
#   stale configurations, and sync/migration gaps.
#
# Why a full outer join is useful:
# - CRM-only records may represent customers missing provisioning/billing data.
# - Billing-only records may represent orphaned accounts, migrations, deleted CRM
#   entries, key mismatches, or delayed synchronization.
# - Matched records with conflicting values may identify data-quality or system-of-
#   record problems.
# - An inner join would hide unmatched records and can make reconciliation look
#   healthier than it actually is.
#
# -------------------------------------------------------------------------------
# Contract questions to clarify before coding
# -------------------------------------------------------------------------------
#
# Join semantics:
# - Do we need inner, left outer, right outer, full outer, or anti join behavior?
# - Which source is primary, if any?
# - Are unmatched records errors, expected states, or records to exclude?
#
# Key and cardinality:
# - What is the authoritative join key: customer_id, tenant_id, account_id,
#   external ID, or a composite key?
# - Is the join key globally unique, tenant-scoped, case-sensitive, and normalized?
# - Is this one-to-one, one-to-many, many-to-one, or many-to-many?
# - Can join keys be missing, malformed, duplicated, renamed, or recycled?
#
# Conflicts and source authority:
# - If CRM and billing disagree, should we retain both values, select a system of
#   record, select by freshness/version, or emit a conflict record?
# - Which timestamp/version is authoritative when data arrives late or out of order?
#
# Output:
# - Should results preserve CRM order, billing order, event-time order, or use a
#   deterministic sorted key order?
# - Should unmatched records be returned as None, a status field, or a separate
#   remediation queue?
# - Do consumers need full source records, selected fields, or a normalized result?
#
# Operations:
# - Is this a finite batch reconciliation or a continuously changing data stream?
# - What volume, latency, retention, replay, and audit requirements apply?
# - Who is authorized to join and view tenant/customer information?
# - Which PII/sensitive fields must be minimized, redacted, or protected?
#
# -------------------------------------------------------------------------------
# Important limitations of this in-memory implementation
# -------------------------------------------------------------------------------
#
# - Duplicate keys are silently overwritten in dictionary comprehensions:
#
#       {record["customer_id"]: record for record in records}
#
#   If a customer can have multiple accounts or records, use:
#
#       customer_id -> list[record]
#
#   and define the intended one-to-many/many-to-many output shape.
#
# - Using a set for all_customer_ids does not preserve a business-defined order.
#   Sort keys for deterministic order, or retain source order if it is meaningful.
#
# - All source records and indexes must fit in memory.
# - This does not validate schema, key normalization, authorization, PII controls,
#   source freshness, version conflicts, or malformed-record behavior.
# - It does not solve stream ordering, late data, recovery, or state durability.
#
# -------------------------------------------------------------------------------
# Production direction: where to push the join
# -------------------------------------------------------------------------------
#
# Choose the processing system based on data shape and operating requirements.
#
# 1. Small bounded dataset / FDE investigation:
# - Python in memory is appropriate for a one-time analysis, incident artifact,
#   test fixture, small CSV/JSON export, or interview problem.
#
# 2. Operational serving data:
# - Push the join to the transactional/operational database when both datasets
#   are current, indexed, and the request needs low-latency customer-scoped reads.
# - MongoDB can be suitable for flexible, denormalized customer-support documents
#   or materialized per-tenant views, but do not repeatedly scan all raw event data
#   for every support-page request at large scale.
#
# 3. Scheduled batch reconciliation / files / SaaS exports:
# - Use an orchestrated ETL/ELT pipeline, such as Azure Data Factory, a warehouse,
#   SQL engine, Spark, or a lakehouse processing job.
# - Use a full outer join plus explicit missing-left/missing-right/conflict outputs.
# - Persist reconciliation results, source versions, timestamps, and remediation
#   status for auditability and replay.
#
# 4. High-volume logs, telemetry, and interactive incident analysis:
# - Push raw events and reference data to an analytics system such as Azure Data
#   Explorer or Log Analytics, then execute server-side joins/queries.
# - Keep customer/tenant filtering and access control close to the data boundary.
#
# 5. Continuous stream:
# - Use durable ingestion, such as Event Hubs, then a stream processor such as
#   Azure Stream Analytics, Functions for lightweight enrichment, or Spark
#   Structured Streaming for high-volume/stateful joins.
# - Define event-time windows, late/out-of-order-event policy, deduplication,
#   checkpointing, state retention, and source-of-truth behavior.
# - A stream-stream full outer join requires bounded windows/state; otherwise the
#   system cannot know indefinitely whether a matching record may arrive later.
#
# 6. Large-scale joins / data lake / complicated transformations:
# - Use Spark, Databricks, Fabric/Synapse-style compute, or another distributed
#   data engine when datasets do not fit in one process, need large joins, require
#   backfills, or combine batch and streaming sources.
#
# Summary:
#
#     Python dicts               -> small, bounded analysis or coding exercise
#     SQL/operational database   -> low-latency current-state customer queries
#     ADF / ETL / warehouse      -> scheduled cross-system reconciliation
#     ADX / Log Analytics        -> high-volume telemetry investigation
#     Event Hubs + stream engine -> continuous event processing
#     Spark/lakehouse            -> large, stateful, distributed data processing
#
# Production systems should return or persist reconciliation state such as:
#
#     MATCHED
#     MISSING_CRM
#     MISSING_BILLING
#     CONFLICT
#     MALFORMED_KEY
#     PENDING_LATE_DATA
#
# That makes the output actionable for customer support, onboarding, data quality,
# migration, and remediation workflows.

# -------------------------------------------------------------------------------
# FDE context: why this dataset-join pattern matters
# -------------------------------------------------------------------------------
#
# This in-memory hash-map join models a common FDE task:
#
#     Combine information from multiple disparate systems into one
#     customer-relevant operational or reconciliation view.
#
# A single system rarely contains the complete answer to a customer problem.
# An FDE often correlates records across CRM, billing, identity, telemetry,
# support, agent traces, tool calls, deployment inventory, and external systems.
#
# Common FDE join use cases:
#
# - CRM + billing/subscriptions:
#   "Does every customer entitlement have an active billing account?"
#
# - Identity + product entitlements:
#   "Why can this customer authenticate but not access a feature?"
#
# - Support case + telemetry/traces:
#   "What technically happened during the customer's reported incident?"
#
# - Agent traces + tool/dependency logs:
#   "Which tool, connector, or dependency caused a customer workflow to fail?"
#
# - Orders + payments + fulfillment:
#   "Was this order paid, duplicated, refunded, or left unfulfilled?"
#
# - Customer source export + internal canonical records:
#   "Which records are missing, stale, duplicated, or conflicting?"
#
# - Customer configuration + deployment/resource inventory:
#   "Which tenants were affected by a rollout, configuration change, or outage?"
#
# - Audit events + identity/role assignments:
#   "Was an action authorized, and under which tenant, role, and policy?"
#
# - Usage/cost telemetry + customer plan/contract:
#   "Which customers are exceeding quotas, generating unexpected cost, or
#   using a feature outside their expected entitlement?"
#
# The join connects otherwise isolated facts into an operational story:
#
#     Customer symptom
#       -> tenant/account identity
#       -> support case or workflow
#       -> application/agent trace
#       -> tool call or dependency event
#       -> configuration/deployment state
#       -> root-cause hypothesis and safe remediation
#
# -------------------------------------------------------------------------------
# Join-key guidance
# -------------------------------------------------------------------------------
#
# Use a stable identity/correlation key that represents the same entity in both
# systems. Common keys include:
#
#     customer_id
#     tenant_id
#     account_id
#     external_customer_id
#     subscription_id
#     order_id
#     invoice_id
#     transaction_id
#     resource_id
#     event_id
#     trace_id
#     correlation_id
#     agent_run_id
#     tool_call_id
#     idempotency_key
#
# Timestamps are usually NOT sufficient as the only join key:
#
# - Different systems can record timestamps at different precision.
# - Clocks can drift.
# - Events can be delayed, batched, retried, or received out of order.
# - Event time, ingestion time, and processing time can differ.
#
# Use timestamps for ordering, freshness, time-window constraints, and sequence.
# When possible, join using a stable ID such as trace_id or order_id plus tenant
# scope, then use timestamps to confirm timing and causal sequence.
#
# Example safer correlation rule:
#
#     same tenant_id
#     AND same trace_id/correlation_id
#     AND event timestamps within an expected diagnostic window
#
# -------------------------------------------------------------------------------
# Production limitations of Python dictionaries
# -------------------------------------------------------------------------------
#
# This code creates an application-level, in-memory hash index:
#
#     customer_id -> full source record
#
# It has the same general purpose as a database index: avoid repeatedly scanning
# all billing records when looking up a matching customer ID.
#
# However, a Python dictionary is not a production database index:
#
# Python dictionary:
# - Exists only in one process's memory.
# - Disappears when the process exits, crashes, or is redeployed.
# - Must fit in available process memory.
# - Is built and maintained by application code.
# - Has no built-in transaction isolation, durable writes, query planner,
#   concurrency coordination, authorization enforcement, encryption, retention,
#   backup, replication, monitoring, or audit history.
# - Supports expected O(1) equality lookup, but does not naturally provide
#   efficient range queries, ordered scans, server-side query optimization, or
#   cross-process/shared access.
# - Silently overwrites earlier values if duplicate keys are used in a basic
#   dictionary comprehension.
#
# Production database/analytics indexes:
# - Are durable and maintained as data changes.
# - Support concurrent access and transaction/recovery semantics.
# - Can be distributed, replicated, backed up, monitored, and access-controlled.
# - Often use B-tree/B+tree or engine-specific structures that support equality,
#   range queries, ordered scans, and query-planner-selected join strategies.
# - Can index unique and non-unique values, often mapping one key to multiple
#   records/row locations.
# - Push filtering, joining, aggregation, and projection close to the data so
#   large datasets do not need to be copied into one application process.
#
# -------------------------------------------------------------------------------
# Production design choices
# -------------------------------------------------------------------------------
#
# For small, bounded data:
# - Use Python dictionaries for a coding exercise, test fixture, one-time
#   reconciliation, local incident analysis, or small CSV/JSON export.
#
# For current-state, low-latency operational data:
# - Push the join to an indexed transactional/operational database.
# - Index the join key(s), enforce uniqueness where appropriate, and use a
#   database join/query or materialized per-tenant view.
#
# For scheduled cross-system reconciliation:
# - Use SQL, a warehouse/lakehouse, Azure Data Factory, Spark, or another
#   ETL/ELT pipeline.
# - Persist MATCHED, MISSING_LEFT, MISSING_RIGHT, CONFLICT, and MALFORMED_KEY
#   results with source versions, timestamps, and remediation state.
#
# For logs, traces, and high-volume telemetry:
# - Push data to an analytics platform such as Azure Data Explorer/Log Analytics.
# - Perform server-side, tenant-scoped joins and retain links to trace IDs,
#   event IDs, source timestamps, deployment versions, and dependency context.
#
# For continuous streams:
# - Use durable ingestion plus a stream processor.
# - Define windowing, state retention, late/out-of-order-event policy,
#   deduplication, checkpointing, replay, and reconciliation behavior.
# - Do not attempt an indefinite full outer join of two unbounded streams without
#   bounded state/window semantics; a matching record might arrive arbitrarily late.
#
# -------------------------------------------------------------------------------
# Critical contract questions for every production join
# -------------------------------------------------------------------------------
#
# - What is the authoritative join key, and is it normalized consistently?
# - Is the key globally unique or scoped by tenant/customer/environment?
# - Is the relationship one-to-one, one-to-many, many-to-one, or many-to-many?
# - Which system owns each field when source values conflict?
# - What does an unmatched record mean: expected state, sync delay, data defect,
#   deleted record, migration gap, or a security issue?
# - Which records must appear: inner, left, right, full outer, or anti join?
# - What ordering, determinism, audit evidence, and source freshness are required?
# - Is the caller authorized to correlate and view both source datasets?
# - Which customer/PII fields should be minimized, redacted, or excluded?
#
# FDE summary:
#
#     Hash-map join in Python
#         -> demonstrates the core algorithm
#         -> acts like a temporary application-level equality index
#         -> enables a unified view across systems
#
#     Production join
#         -> requires correct identity, tenant isolation, cardinality, source
#            authority, freshness, scalability, durability, and auditability
#


crm_customers = [
    {"customer_id": "contoso", "contact": "Ava", "plan": "enterprise"},
    {"customer_id": "fabrikam", "contact": "Ben", "plan": "standard"},
    {"customer_id": "adventure-works", "contact": "Cara", "plan": "premium"},
]

billing_accounts = [
    {"customer_id": "contoso", "account_status": "active", "balance": 1200},
    {"customer_id": "fabrikam", "account_status": "past_due", "balance": 300},
    {"customer_id": "northwind", "account_status": "active", "balance": 0},
]


# Build a hash-map lookup for each source:
#
#     customer_id -> source record
#
# Assumption: each source contains at most one record per customer ID.
# In production, validate/aggregate duplicate keys or store a list per key.
billing_by_customer_id = {}

for account in billing_accounts:
    customer_id = account["customer_id"]
    billing_by_customer_id[customer_id] = account

crm_by_customer_id = {
    customer["customer_id"]: customer
    for customer in crm_customers
}


# Union gives every key found in either source, which implements the "full" part
# of the full outer join.
#
# A set has no business-defined order. Use sorted(...) for deterministic output,
# or preserve source order when that is part of the contract.
all_customer_ids = (
    set(billing_by_customer_id)
    | set(crm_by_customer_id)
)

joined_data = []

for customer_id in sorted(all_customer_ids):
    crm_record = crm_by_customer_id.get(customer_id)
    billing_record = billing_by_customer_id.get(customer_id)

    # In a richer reconciliation output, add a status such as:
    #
    #     MATCHED
    #     MISSING_CRM
    #     MISSING_BILLING
    #
    # and separately detect conflicting fields when both records exist.
    joined_data.append(
        {
            "customer_id": customer_id,
            "crm": crm_record,
            "billing": billing_record,
        }
    )

print("Full outer join result:")
for record in joined_data:
    print(record)