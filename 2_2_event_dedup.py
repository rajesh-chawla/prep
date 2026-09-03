# Event Deduplication — Python and FDE Design Notes
#
# Goal:
# Prevent the same immutable business event from changing an aggregate more than
# once, while continuing to count separate, legitimate business actions.
#
# -----------------------------------------------------------------------------
# Core Python pattern
# -----------------------------------------------------------------------------
# A set stores unique values, so it can track event IDs processed by one Python
# process during its lifetime.
#
# seen_event_ids: set[str] = set()
#
# for sale in sales:
#     event_id = sale["event_id"]
#
#     if event_id in seen_event_ids:
#         continue
#
#     seen_event_ids.add(event_id)
#     # Safely update aggregate state here.
#
# `continue` skips the remainder of the current loop iteration. Therefore, a
# duplicate event never reaches the count/total aggregation logic.
#
# This is appropriate for learning, demos, or small bounded in-memory inputs.
# A Python set is not a complete production deduplication solution because it:
# - Is lost when the process restarts.
# - Is not shared across multiple workers/replicas.
# - Grows as new event IDs arrive unless IDs are expired.
# - Cannot, by itself, atomically coordinate dedupe state, aggregate updates,
#   and source-offset/checkpoint commits.
#
# -----------------------------------------------------------------------------
# The critical distinction: business duplicates vs. delivery duplicates
# -----------------------------------------------------------------------------
# Two events can have matching business fields but still be two valid purchases.
# Do NOT deduplicate based only on matching customer, product, amount, or time.
#
# Valid separate purchases:
#
# {
#     "event_id": "evt-101",
#     "order_id": "order-5001",
#     "customer_id": "customer-77",
#     "product_id": "coffee",
#     "amount": 4.50,
# }
#
# {
#     "event_id": "evt-102",
#     "order_id": "order-5002",
#     "customer_id": "customer-77",
#     "product_id": "coffee",
#     "amount": 4.50,
# }
#
# These both count because they represent different domain events/orders.
#
# A duplicate delivery is the same immutable event sent or processed again:
#
# {
#     "event_id": "evt-101",
#     "order_id": "order-5001",
#     "customer_id": "customer-77",
#     "product_id": "coffee",
#     "amount": 4.50,
# }
#
# This should not increment an aggregate a second time.
#
# -----------------------------------------------------------------------------
# Questions for FDE discovery
# -----------------------------------------------------------------------------
# 1. Business semantics
# - Can a user legitimately buy the same item multiple times?
# - Which identifier defines a duplicate: event_id, order_id, payment_id, or a
#   domain-specific composite key?
# - Is the chosen identity globally unique and immutable?
# - Is one event an immutable fact, or can it be corrected/cancelled later?
#
# 2. Event identity contract
# - Who creates the event_id: the client, producer service, or central platform?
# - Is event_id generated once per immutable business event?
# - Does a producer retry reuse the same event_id?
# - Do not use a fresh ID for every delivery attempt; doing so prevents consumers
#   from recognizing infrastructure retries as duplicates.
# - Document ID format, uniqueness scope, ownership, and lifecycle in the event
#   data contract.
#
# 3. Where duplicates originate
# - User/business behavior: two separate orders can be valid and must both count.
# - Producer retry: a timeout can leave the producer unsure whether a publish
#   succeeded, so it may send the same event again.
# - Consumer retry: a consumer can update a sink, fail before committing its
#   checkpoint/offset, then process the event again after restart.
# - Replay/backfill: intentionally reading historical events can repeat earlier
#   deliveries.
# - Downstream write retry: a sink may receive the same update more than once.
#
# Design conclusion:
# - Assume duplicates are possible in distributed systems.
# - Design the consumer/aggregate update to be idempotent: applying the same
#   event more than once has the same final effect as applying it once.
#
# 4. Invalid duplicate handling
# - If an already-seen event_id has the same payload, do not apply it again.
# - Record duplicate metrics/logs with event ID, producer, partition/offset,
#   receive time, and dedupe decision.
# - If an already-seen event_id arrives with a different payload, do not silently
#   ignore it. Treat it as a data-integrity conflict:
#   capture both payloads safely, route to quarantine/dead-letter handling, and
#   alert the responsible owner.
# - Establish whether the conflict is a producer bug, event mutation, ID reuse,
#   fraud/security concern, or an expected correction workflow.
#
# 5. Contract, schema, and drift
# - Define required fields: event_id, schema_version, event_time, aggregation
#   key, amount/value, currency/unit, and producer/source metadata as needed.
# - Define validation for missing/invalid fields and a quarantine/dead-letter
#   path for events that should not reach aggregates.
# - Version the contract and document compatibility rules.
# - Structural compatibility is not enough: semantic changes to an amount, its
#   currency, timestamp meaning, or identifier format can corrupt aggregates.
# - Normalize compatible versions before aggregating, or separately handle
#   incompatible versions.
#
# 6. Scale and retention
# - What are average/peak events per second, burst profile, and event size?
# - How many unique event IDs arrive during the dedupe period?
# - How long can producer retries, consumer retries, and source replays occur?
# - How long must IDs be retained to prevent duplicate effects safely?
# - Is there key skew, a retry storm, or a hot producer that could overload one
#   partition or dedupe shard?
#
# Design conclusion:
# - Production dedupe needs a durable, scalable, partitioned state store or a
#   processor with managed/checkpointed state.
# - Apply TTL/expiry to dedupe records only after the permitted retry/replay
#   horizon, plus an operational safety margin.
# - A longer dedupe horizon improves protection against delayed duplicates but
#   increases storage and lookup cost.
#
# 7. Atomicity, failure, and replay
# - Can these happen atomically: mark an event ID processed, update the aggregate,
#   write output, and commit the consumer checkpoint/offset?
# - If not, identify the failure windows and use an idempotent recovery design.
# - Are output writes idempotent/upsertable?
# - Is replay used to resume normal processing or to recompute outputs from
#   scratch? These workflows may require separate output namespaces, a reset of
#   dedupe state, or a versioned aggregate output.
# - Retain raw immutable events long enough for debugging, reconciliation,
#   backfills, auditability, and rebuilding aggregates.
#
# 8. Observability
# - Monitor duplicate count/rate, duplicate ID conflicts, dedupe-store latency,
#   errors, state size, TTL expiration, producer retry rate, consumer restarts,
#   partition lag, and dedupe decisions by producer/partition.
# - Alert on unusual duplicate spikes and all conflicting-payload ID reuse.
#
# -----------------------------------------------------------------------------
# Security assumption for this learning exercise
# -----------------------------------------------------------------------------
# Assumption:
# Producers and consumers run in a trusted, private environment. This exercise
# focuses on correctness, replay, scale, and operations rather than detailed
# authentication and authorization design.
#
# Production follow-up:
# Validate publisher/consumer authorization, least-privilege service identities,
# network boundaries/private access, encryption in transit and at rest, secret
# management, audit logging, and data classification/PII requirements.
#
# -----------------------------------------------------------------------------
# Suggested production contract statement
# -----------------------------------------------------------------------------
# Each immutable business event must have a globally unique, stable event_id.
# A producer retry must reuse that event_id. Consumers must ensure that an event
# ID has at most one aggregate effect within the retained deduplication window.
#
# A good output key for windowed aggregates may be:
#     (window_start_utc, window_end_utc, aggregation_key)
#
# This supports idempotent upserts and late-event corrections without creating a
# second aggregate record for the same logical window and aggregation key.

sales = [
    {
        "event_id": "evt-001",
        "product": "coffee",
        "amount": 4.50,
    },
    {
        "event_id": "evt-002",
        "product": "tea",
        "amount": 3.25,
    },
    {
        "event_id": "evt-002",
        "product": "tea",
        "amount": 3.25,
    },
    {
        "event_id": "evt-003",
        "product": "coffee",
        "amount": 5.00,
    },
]

"""
Corrected:
{
    "coffee": {
        "count": 2,
        "total": 9.5,
        "average": 4.75,
    },
    "tea": {
        "count": 1,
        "total": 3.25,
        "average": 3.25,
    },
}
"""

def aggregate_unique_sales(
    sales: list[dict[str, str | float]],
) -> dict[str, dict[str, float | int]]:
    
    seen_event_ids: set[str] = set()
    summary = {}

        # 1. If event_id was already processed, skip this event.
        # 2. Otherwise, record event_id in seen_event_ids.
        # 3. Initialize summary[product] if this is a new product.
        # 4. Increment that product's count and total.

    for sale in sales:
        event_id = str(sale["event_id"])
        product = sale["product"]
        amount = sale["amount"]

        if event_id in seen_event_ids:
            continue

        seen_event_ids.add(event_id)

        if product not in summary:
            summary[product] = {
                "count": 0,
                "total": 0.0,
                "average": 0.0
            }

        summary[product]["count"] += 1
        summary[product]["total"] += amount

    # 5. Use a second loop to add each product's average.
    for key, value in summary.items():
        value["average"] = value["total"] / value["count"]

    return summary


summary = aggregate_unique_sales(sales)
print(f"Summary: {summary}")