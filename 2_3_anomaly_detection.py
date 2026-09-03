"""
I would instrument infrastructure, application, dependency, and business/workflow metrics. 
I would use rolling or managed dynamic baselines to detect unexpected deviations, but pair 
them with absolute safety thresholds for customer-impacting or capacity-risk conditions. 

Before paging on an anomaly, I would define warm-up behavior for new deployments, 
persistence requirements to avoid one-sample noise, metric dimensions, seasonal patterns, 
and escalation rules. I would also correlate signals—such as latency, errors, 
and dependency failures—so an alert maps to likely user impact rather than a 
single noisy metric.

Anomaly detection is not just infrastructure monitoring. It can detect unusual behavior 
in operational metrics, data quality, security events, customer activity, financial transactions, 
supply-chain systems, and sensor data. The required model and response depend on whether 
the anomaly is informational, needs human review, or can safely drive an automated action.
"""

latencies = [
    102,
    98,
    101,
    99,
    100,
    103,
    97,
    102,
    160,
    101,
    250,  # likely anomaly
    99,
    102,
]

from collections import deque
import re
from statistics import mean, stdev

def find_rolling_anomalies(
    latencies: list[int],
    window_size: int,
    threshold: float,
) -> list[dict[str, float]]:

    recent_values = deque(maxlen=window_size)
    anomalies:list[dict[str, float]] = []

    # simple anomaly detection by finding items <threshold> stddevs away from a rolling mean of window size

    # for each item in latencies
    for index, item in enumerate(latencies):
        if(len(recent_values) > 2):
            window_mean = mean(recent_values)
            window_stdev = stdev(recent_values)

            z_score = (item - window_mean) / window_stdev

            if (abs(z_score) > threshold):
                an_anomoly = {
                    "index": index,
                    "mean" : window_mean,
                    "stdev": window_stdev,
                    "z_score": z_score
                }
                anomalies.append(an_anomoly)
        recent_values.append(item)

    return anomalies



def find_rolling_anomalies_orig(
    values: list[int],
    window_size: int,
    threshold: float,
) -> list[dict[str, float | int]]:
    recent_values: deque[float] = deque(maxlen=window_size)
    anomalies: list[dict[str, float | int]] = []

    for index, value in enumerate(values):
        # Do not score values until there is enough history.
        if len(recent_values) >= 2:
            baseline_mean = mean(recent_values)
            baseline_stdev = stdev(recent_values)

            # Avoid division by zero if all prior values are identical.
            if baseline_stdev > 0:
                z_score = (value - baseline_mean) / baseline_stdev

                if abs(z_score) >= threshold:
                    anomaly = {
                        "index": index,
                        "value": value,
                        "mean": baseline_mean,
                        "stdev": baseline_stdev,
                        "z_score": z_score,
                    }
                    anomalies.append(anomaly)

        # Add only after scoring, so a potentially anomalous value does not
        # influence the baseline used to judge itself.
        recent_values.append(value)

    return anomalies


anomalies = find_rolling_anomalies(
    latencies,
    window_size=10,
    threshold=2.0,
)

for anomaly in anomalies:
    print(anomaly)


"""
from collections import deque

recent_values = deque(maxlen=3)

recent_values.append(10)
recent_values.append(20)
recent_values.append(30)

print(recent_values)
# deque([10, 20, 30], maxlen=3)

recent_values.append(40)

print(recent_values)
# deque([20, 30, 40], maxlen=3)

from statistics import mean, stdev

window = [98, 101, 99, 100, 103]

average = mean(window)
standard_deviation = stdev(window)

print(average)
print(standard_deviation)
"""