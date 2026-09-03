# “For incremental reconciliation, I would first validate that source and target share a stable, 
# immutable, non-null matching key. If not, I would define a documented composite business key 
# or a different matching strategy, because dictionary-style matching otherwise silently 
# overwrites non-unique records. 
# 
# I would define the reconciliation population using a durable batch ID, CDC range, 
# offset range, or persisted watermark—not an ambiguous calendar period—and include an overlap 
# policy for late data. 
# 
# Finally, I would size the approach by volume: use counts, distinct-key counts, totals, 
# and partition-level checksums as scalable checks, then deep-compare only mismatched 
# partitions and retain an auditable exception report.”



# Inputs:

source_sales = [
    {"event_id": "evt-001", "product": "coffee", "amount": 4.50},
    {"event_id": "evt-002", "product": "tea", "amount": 3.25},
    {"event_id": "evt-003", "product": "coffee", "amount": 5.00},
]

target_sales = [
    {"event_id": "evt-001", "product": "coffee", "amount": 4.50},
    {"event_id": "evt-002", "product": "tea", "amount": 3.50},
    {"event_id": "evt-004", "product": "muffin", "amount": 2.75},
]

# Expected output:
# {
#     "missing_from_target": ["evt-003"],
#     "unexpected_in_target": ["evt-004"],
#     "mismatched_records": [
#         {
#             "event_id": "evt-002",
#             "source_amount": 3.25,
#             "target_amount": 3.50,
#         },
#     ],
# }

# FUNCTION reconcile_incremental(source_sales, target_sales):

def reconcile_incremental(source_sales, target_sales):

#     CREATE source_by_event_id as an empty dictionary
#     CREATE target_by_event_id as an empty dictionary

    source_by_event_id = {}
    target_by_event_id = {}

#     FOR EACH sale IN source_sales:
#         GET event_id FROM sale
#         STORE sale in source_by_event_id using event_id as the key

    for sale in source_sales:
        event_id = sale["event_id"]
        source_by_event_id[event_id] = sale

#     FOR EACH sale IN target_sales:
#         GET event_id FROM sale
#         STORE sale in target_by_event_id using event_id as the key

    for sale in target_sales:
        event_id = sale["event_id"]
        target_by_event_id[event_id] = sale

#     CREATE an empty list called missing_from_target
#     CREATE an empty list called unexpected_in_target
#     CREATE an empty list called mismatched_records

    missing_from_target = []
    unexpected_in_target = []
    mismatched_records = []

#     # TODO:
#     # Compare source IDs with target IDs.
#     # Add source-only IDs to missing_from_target.

#     # Add target-only IDs to unexpected_in_target.
#     # For IDs that exist in both, compare product and amount.
#     # Add enough source/target detail to mismatched_records to investigate.

    for source_id in source_by_event_id:
        if source_id not in target_by_event_id:
            missing_from_target.append(source_id)

        mismatch = {
            "event_id": source_id
        }

        if source_id in target_by_event_id:
            if source_by_event_id[source_id]["product"] != target_by_event_id[source_id]["product"]:
                mismatch["source_product"] = source_by_event_id[source_id]["product"]
                mismatch["target_product"] = target_by_event_id[source_id]["product"]

            if source_by_event_id[source_id]["amount"] != target_by_event_id[source_id]["amount"]:
                mismatch["source_amount"] = source_by_event_id[source_id]["amount"]
                mismatch["target_amount"] = target_by_event_id[source_id]["amount"]

        if (len(mismatch) > 1):
            mismatched_records.append(mismatch)

    for target_id in target_by_event_id:
        if target_id not in source_by_event_id:
            unexpected_in_target.append(target_id)


#     RETURN a dictionary containing:
#         missing_from_target
#         unexpected_in_target
#         mismatched_records
    return {
        "missing_from_target": missing_from_target,
        "unexpected_in_target": unexpected_in_target,
        "mismatched_records": mismatched_records,
    }
