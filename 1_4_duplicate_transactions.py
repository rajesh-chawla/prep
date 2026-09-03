# Duplicate Transaction Detection Within a Time Window
#
# Goal:
# Identify later transactions that reuse the same transaction_id within a
# configured time window.
#
# Base contract for this example:
# - A duplicate means the same transaction_id occurs more than once.
# - A duplicate must occur within `time_window` seconds of the prior occurrence.
# - Return the later transaction record(s) identified as duplicates.
# - Input is assumed to arrive in nondecreasing timestamp order.
#
# Example:
#
#     txn-100 at timestamp 100
#     txn-100 at timestamp 125
#
# With a 30-second window, the gap is 25 seconds, so the second event is
# considered a duplicate.
#
# -------------------------------------------------------------------------------
# Interview explanation
# -------------------------------------------------------------------------------
#
# - I store the most recent timestamp for each transaction_id in a hash map.
# - For each incoming transaction, I compare its timestamp to the previous
#   timestamp for that same ID.
# - If the gap is within the configured window, I flag the later record as a
#   duplicate.
# - I then update the stored timestamp so future records compare with the most
#   recent occurrence.
# - With timestamp-ordered input, this is expected O(n) time and O(u) space,
#   where u is the number of distinct transaction IDs.
#
# -------------------------------------------------------------------------------
# Where an FDE uses this pattern
# -------------------------------------------------------------------------------
#
# The same pattern appears whenever retries, replay, unreliable networks, or
# at-least-once delivery can cause a logical event to arrive more than once.
#
# 1. Orders, payments, and fulfillment
# - Detect repeated payment/order requests after a client or provider timeout.
# - Prevent duplicate charges, duplicate orders, repeated refunds, or duplicate
#   shipments.
#
# 2. Customer data ingestion and reconciliation
# - Detect repeated partner records, invoice rows, CRM updates, product records,
#   or external-order messages.
# - Prevent duplicated customer records and corrupted totals/aggregates.
#
# 3. Webhooks and SaaS integrations
# - Detect providers retrying webhook notifications after an unacknowledged or
#   timed-out delivery.
# - Avoid processing the same subscription, order, or account-change event twice.
#
# 4. Logs, telemetry, and usage reporting
# - Detect replayed request, trace, exception, audit, metric, or usage events.
# - Prevent inflated alert severity, inaccurate dashboards, incorrect cost/usage
#   reporting, and misleading incident investigation.
#
# 5. AI-agent workflows and tool calls
# - Detect retries/replays of tool calls or side-effecting workflow actions.
# - Prevent duplicate tickets, emails, CRM updates, workflow starts, refunds,
#   notifications, permission updates, or other customer-impacting actions.
#
# 6. Batch, backfill, and stream recovery
# - Detect overlap between normal processing and a replay/backfill.
# - Prevent duplicate aggregates after a worker restart or checkpoint rollback.
#
# -------------------------------------------------------------------------------
# Critical FDE distinction: what kind of duplicate is this?
# -------------------------------------------------------------------------------
#
# "Duplicate" is a business-contract decision, not only a hash-map lookup.
#
# - Duplicate delivery:
#   The same immutable event/message is delivered more than once.
#   Preferred identity: event_id or message_id.
#
# - Duplicate processing attempt:
#   A consumer retries processing after a crash, timeout, or unknown outcome.
#   Preferred identity: event_id, message ID, or processing record.
#
# - Duplicate business action:
#   A customer intended one action, but a retry could execute it multiple times.
#   Preferred identity: idempotency_key.
#
# - Equivalent transaction:
#   Different IDs appear similar according to selected business fields.
#   Possible signature: customer + merchant + amount + payment method + time range.
#
# Do NOT treat "same customer + same amount + nearby timestamp" as automatically
# duplicate. A customer may legitimately make two identical purchases close
# together. Equivalent-transaction rules must be explicitly approved because
# false positives can block legitimate customer activity.
#
# -------------------------------------------------------------------------------
# Event Hubs / event bus considerations
# -------------------------------------------------------------------------------
#
# An event hub/event bus is part of a resilient ingestion architecture, but it
# does not eliminate the need for deduplication or idempotent consumers.
#
# A durable broker can:
# - Absorb bursty traffic.
# - Retain events for replay.
# - Decouple producers from consumers.
# - Partition work for parallel processing.
# - Preserve arrival order for related events within a chosen partition key.
#
# A durable broker does NOT by itself:
# - Guarantee that a consumer receives/processes an event exactly once.
# - Prevent redelivery after retry, restart, replay, or checkpoint recovery.
# - Define whether two business records are duplicates.
# - Prevent duplicate external side effects such as a second payment or email.
#
# For side-effecting operations, use:
#
#     stable event_id       -> identifies one delivered message/event
#     idempotency_key       -> identifies one intended business action
#     durable processed log -> records completed work/result
#
# Production flow:
#
#     producer
#       -> event containing event_id + business ID + idempotency_key
#       -> durable event bus
#       -> idempotent consumer
#       -> atomic durable state/action record
#       -> external side effect only if action was not already completed
#       -> checkpoint/acknowledge
#
# The durable "already processed?" check and the result/action record must be
# atomic or otherwise safely recoverable. An in-memory Python dictionary is
# only appropriate for an interview or local batch demonstration.
#
# -------------------------------------------------------------------------------
# Key tradeoffs and contract questions
# -------------------------------------------------------------------------------
#
# Identity and false positives:
# - Is duplicate identity transaction_id, event_id, external order ID, or
#   idempotency_key?
# - Are identical business fields close in time suspicious or legitimate?
# - What is the cost of a false positive (blocking a valid action) versus a
#   false negative (allowing a repeated side effect)?
#
# Time:
# - Is the window based on event time, ingestion/arrival time, or processing time?
# - Is the time window inclusive? In this example, <= time_window is inclusive.
# - Can events arrive late or out of order?
# - Is the input guaranteed to be ordered by the authoritative timestamp?
#
# Output:
# - Should we return every later duplicate record?
# - Should we return each duplicate ID only once?
# - Should we return original/duplicate pairs for investigation?
# - Should we silently suppress duplicates, flag them for review, or reject them?
#
# Scale and memory:
# - This dictionary stores one entry per distinct transaction_id.
# - For an unbounded stream, memory grows without a retention/expiry policy.
# - In production, bound dedupe state using a time window, TTL, or retention
#   period that matches the business replay/duplicate risk.
# - Partition by a stable key when scaling; watch for hot keys and partition skew.
#
# Reliability:
# - Define behavior after a worker restart, event replay, or partial write.
# - Persist dedupe/idempotency state when duplicate side effects are harmful.
# - Decide whether duplicates are delivery attempts to measure or records to ignore.
#
# Security and auditability:
# - Enforce tenant/customer authorization before looking up or exposing records.
# - Avoid logging sensitive payment or customer fields unnecessarily.
# - Retain enough audit information to explain why an event was flagged or
#   suppressed: event_id, transaction_id, timestamps, source, decision, and trace ID.
#
# -------------------------------------------------------------------------------
# Limitation of this exact implementation
# -------------------------------------------------------------------------------
#
# The subtraction below assumes transactions are timestamp ordered:
#
#     timestamp - previous_timestamp
#
# If timestamps can arrive out of order, a negative difference can create unclear
# behavior and updating state can overwrite a newer timestamp with an older one.
#
# For a bounded, unordered batch:
# - Sort by timestamp first, then scan. Complexity becomes O(n log n).
#
# For a live stream:
# - Define an event-time lateness allowance/watermark policy.
# - Decide whether late events can revise prior dedupe decisions.
# - Persist state and use bounded retention rather than an unbounded dictionary.


# -------------------------------------------------------------------------------
# Remediation decision tree after duplicate detection
# -------------------------------------------------------------------------------
#
# Detecting a duplicate is not the final decision. First classify what was
# duplicated, then choose a remediation that matches the customer/business risk.
#
# Is this the same immutable delivered event/message?
#
#     Same event_id/message_id?
#         |
#         +-- No:
#         |     This may be an equivalent/similar transaction rather than an
#         |     exact delivery duplicate. Do not automatically suppress it unless
#         |     the business contract explicitly permits it.
#         |
#         +-- Yes:
#               Has this event/action already completed successfully?
#                   |
#                   +-- Yes:
#                   |     - Do not execute the side effect again.
#                   |     - Return or retain the previously established result.
#                   |     - Record duplicate delivery for audit/telemetry.
#                   |
#                   +-- No / outcome unknown:
#                         - Do not blindly execute a new action.
#                         - Check whether work is in progress, retry safely, or
#                           reconcile with the downstream system.
#                         - Persist a PENDING/UNKNOWN state when needed.
#                         - Route unresolved outcomes to an exception workflow.
#
# Is this the same idempotency key for a side-effecting business action?
#
#     Same idempotency_key?
#         |
#         +-- Yes:
#               Does the new request have the same request/payload fingerprint?
#                   |
#                   +-- Yes:
#                   |     - Treat it as a safe retry of the same intended action.
#                   |     - Return the original COMPLETED result or current
#                   |       PENDING status.
#                   |     - Do not create a second payment, refund, ticket,
#                   |       email, CRM update, workflow run, or permission change.
#                   |
#                   +-- No:
#                         - Reject the request as an idempotency-key conflict.
#                         - Preserve both request hashes and trace/correlation IDs.
#                         - Require a new idempotency key for a new intended action.
#
# Is this only an "equivalent" transaction?
#
#     Same customer + amount + merchant + short time window?
#         |
#         +-- Yes:
#               - This is not automatically a duplicate.
#               - A customer can make legitimate identical purchases close together.
#               - For low-risk workflows: flag/score for review.
#               - For high-risk workflows: hold/review/reconcile only under an
#                 explicit business policy.
#               - Avoid automatic suppression unless false-positive risk is accepted.
#
# Is this duplicate telemetry/log data?
#
#     Same event/trace/metric delivered more than once?
#         |
#         +-- Yes:
#               - Decide whether the metric represents delivery attempts,
#                 processing attempts, or unique business/customer events.
#               - Optionally retain raw duplicate evidence for debugging/audit.
#               - Deduplicate downstream customer-impact metrics, dashboards,
#                 alerts, cost/usage reports, or aggregates when required.
#               - Monitor duplicate rate because spikes may indicate exporter retry,
#                 consumer restart, checkpoint failure, replay, or source instability.
#
# Recommended durable action-state record:
#
#     event_id:         immutable message/event identity
#     transaction_id:   business transaction identity
#     idempotency_key:  one intended side-effecting action across retries
#     request_hash:     detects same key used with different payloads
#     status:           PENDING | COMPLETED | FAILED | UNKNOWN | CONFLICT
#     result:           prior external reference, such as payment_id or ticket_id
#     tenant_id:        customer/authorization scope
#     trace_id:         investigation correlation
#     timestamps:       created, updated, completed, duplicate-detected
#
# For side-effecting actions, the lookup of prior action state and recording of
# the resulting business state must be atomic or safely recoverable. A local
# Python dictionary demonstrates the algorithm but is not durable enough for
# payments, refunds, emails, tickets, CRM changes, or permission updates.

"""
Interview:

- First, I would determine whether this is a repeated delivery, a processing retry, a repeated business 
action, or merely a similar-looking transaction.
- For an exact replay of a completed event, I would suppress the repeat side effect and return the 
previously persisted result.
- For side-effecting operations, I would use a stable idempotency key, persist the action state and 
result durably, and make the check-and-record path atomic.
- If the same idempotency key arrives with a different request payload, I would reject it as a conflict 
rather than assume it is a safe retry.
- If the original outcome is unknown after a timeout, I would not blindly retry; I would reconcile with 
the downstream system or route it to an exception workflow.
- For equivalent transactions—same customer, amount, and nearby time—I would be conservative because 
legitimate transactions can look similar. I would flag or review them unless business policy explicitly permits automatic suppression.
- For telemetry and ingestion events, I would decide whether to retain every raw delivery for audit while 
deduplicating materialized records, customer-impact metrics, dashboards, and alerts.
"""

transactions = [
    {
        "transaction_id": "txn-100",
        "customer_id": "contoso",
        "amount": 49.99,
        "timestamp": 100,
    },
    {
        "transaction_id": "txn-101",
        "customer_id": "fabrikam",
        "amount": 19.99,
        "timestamp": 110,
    },
    {
        "transaction_id": "txn-100",
        "customer_id": "contoso",
        "amount": 49.99,
        "timestamp": 125,
    },
]

# Duplicate window in seconds.
# The current implementation treats exactly 30 seconds apart as a duplicate.
time_window = 30

# Maps transaction_id -> most recent timestamp seen for that ID.
# This representation is enough for the stated contract, but not enough to retain
# original records, trace IDs, source metadata, or durable idempotency state.
seen_transactions: dict[str, int] = {}

# Stores each later transaction record identified as a duplicate.
duplicate_transactions: list[dict] = []


for transaction in transactions:
    # Production input-validation decision:
    # A real ingestion service must define how to handle missing/invalid IDs,
    # timestamps, tenant data, schema versions, and unauthorized records.
    txn_id = transaction["transaction_id"]
    timestamp = transaction["timestamp"]

    previous_timestamp = seen_transactions.get(txn_id)

    # If this ID was seen earlier and the timestamp gap is inside the configured
    # inclusive window, flag the later record as a duplicate.
    if (
        previous_timestamp is not None
        and timestamp - previous_timestamp <= time_window
    ):
        duplicate_transactions.append(transaction)

    # Always record the current timestamp so the next transaction with this ID
    # compares to the most recent prior occurrence.
    seen_transactions[txn_id] = timestamp


print("Duplicate transactions within time window:")
for transaction in duplicate_transactions:
    print(transaction)