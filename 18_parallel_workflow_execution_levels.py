# “This is Kahn’s topological sort extended to return execution levels. 
# I maintain an adjacency list of downstream dependents and an indegree count of remaining 
# prerequisites. The queue contains tasks that are ready to execute. At the start of each 
# round, I snapshot the queue length, process exactly those tasks as one parallel level, 
# and queue any tasks newly unblocked for the next level. If the processed count is less 
# than the requested task count, a cycle prevented some tasks from becoming ready, so I 
# return None. 
# 
# The time complexity is O(V+E), and total storage is O(V+E).”

# “This function identifies dependency-valid execution stages. A production scheduler 
# would add persisted task state, retries and idempotency, timeouts and cancellation, 
# resource/concurrency limits, authorization for actions, and audit/trace events. 
# 
# I would not impose a full-level barrier unless the customer’s workflow semantics 
# require it—independent tasks can often begin as soon as their own prerequisites complete.”

from collections import deque
from operator import le
def topo_sort_level(tasks, dependencies):

    indegree = {}
    graph = {}   
    levels = []

# Create graph:
#     For each task, prepare an empty list of dependents.
# Create indegree:
#     For each task, begin with zero unmet prerequisites.
    for task in tasks:
        graph[task] = []
        indegree[task] = 0

# Read each dependency pair:
#     prerequisite, dependent

#     Add dependent to graph[prerequisite].
#     Increase indegree[dependent] by one.
    for prerequisite, dependency in dependencies:
        graph[prerequisite].append(dependency)
        indegree[dependency] +=1

# Create ready queue:
#     Add every task whose indegree is zero.

    ready = deque()
    for task, num_dependencies in indegree.items():
        if num_dependencies == 0:
            ready.append(task)
            

# Create empty output order list.
    output = []

# While ready queue is not empty:
#     Remove one ready task.
#     Add it to output order.

    while (ready):
        level = []
        level_size = len(ready)
        for _ in range(level_size):
            task = ready.popleft()
            output.append(task)
            level.append(task)

    #     For every dependent unlocked by this task:
    #         Decrease that dependent’s indegree by one.

            for dependency in graph[task]:
                indegree[dependency] -= 1
    #         If its indegree is now zero:
    #             Add it to ready queue.
                if indegree[dependency] == 0:
                    ready.append(dependency)

        levels.append(level)

# If output contains fewer tasks than the input:
#     Return None because a cycle prevented some tasks from becoming ready.
    if (len(output) != len(tasks)):
        return None
    
# Return output order.
    return(levels)


tasks = [
    "collect",
    "verify",
    "check",
    "submit",
]

dependencies = [
    ("collect", "verify"),
    ("collect", "check"),
    ("verify", "submit"),
    ("check", "submit"),
]

print(topo_sort_level(tasks, dependencies))

tasks = ["A", "B", "C"]

dependencies = [
    ("A", "B"),
    ("B", "C"),
    ("C", "A"),
]

print(topo_sort_level(tasks, dependencies))
