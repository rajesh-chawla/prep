# I would use a Python aggregation loop to validate the grouping logic or 
# analyze a bounded local dataset. For production logs, I would emit structured 
# events to Azure Monitor/Application Insights and use Log Analytics with 
# KQL for centralized, time-bounded aggregation, dashboards, investigations, 
# and alerts. 
# 
# I would aggregate on stable, low-cardinality fields such as service, severity, 
# event name, error code, or exception type—not unbounded raw message text.

# Because Log Analytics already provides managed ingestion and time-based 
# partitioning, I would focus the scale review on ingestion volume and cost, 
# structured low-cardinality schema design, workspace and access boundaries, 
# table-specific retention/archive policies, query patterns that filter time 
# and columns early, and summary rules for repeatedly queried high-volume logs. 
# 
# I would also monitor the telemetry pipeline itself—collection delay, 
# data gaps, volume spikes, and alert storms—so observability remains reliable 
# as the application scales.”

logs = [
    {
        "timestamp": "2026-09-03T18:00:00Z",
        "service": "orders-api",
        "level": "INFO",
        "message": "Order created",
    },
    {
        "timestamp": "2026-09-03T18:00:05Z",
        "service": "orders-api",
        "level": "ERROR",
        "message": "Payment provider timed out",
    },
    {
        "timestamp": "2026-09-03T18:00:07Z",
        "service": "inventory-api",
        "level": "WARNING",
        "message": "Low stock for product coffee",
    },
    {
        "timestamp": "2026-09-03T18:00:10Z",
        "service": "orders-api",
        "level": "ERROR",
        "message": "Payment provider timed out",
    },
    {
        "timestamp": "2026-09-03T18:00:15Z",
        "service": "inventory-api",
        "level": "ERROR",
        "message": "Inventory lookup failed",
    },
]

# Output:
# {
#     "orders-api": {
#         "INFO": {
#             "Order created": 1,
#         },
#         "ERROR": {
#             "Payment provider timed out": 2,
#         },
#     },
#     "inventory-api": {
#         "WARNING": {
#             "Low stock for product coffee": 1,
#         },
#         "ERROR": {
#             "Inventory lookup failed": 1,
#         },
#     },
# }

# Pseudocode:
# FUNCTION aggregate_logs(logs):
def aggregate_logs(logs):
#     CREATE an empty dictionary called summary
    summary = {}
#     FOR EACH log_event IN logs:

    for log_event in logs:
        service = log_event["service"]
        level = log_event["level"]
        message = log_event["message"]

#         IF service does not exist in summary:
#             CREATE an empty dictionary for that service
        if service not in summary:
            summary[service] = {}

#         IF level does not exist under that service:
#             CREATE an empty dictionary for that level

        if level not in summary[service]:
            summary[service][level] = {}

#         IF message does not exist under that service and level:
#             SET that message count to 0

        if message not in summary[service][level]:
            summary[service][level][message] = 0

#         INCREMENT that message count by 1

        summary[service][level][message] += 1

    return summary


summary = aggregate_logs(logs)
print(summary)