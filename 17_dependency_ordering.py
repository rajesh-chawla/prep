# “I use an adjacency list to map each prerequisite to the tasks it unlocks, and an 
# indegree dictionary to count each task’s unresolved prerequisites. I initialize a 
# FIFO queue with every zero-indegree task. When I process a task, I decrement the 
# indegree of each dependent; 
# 
# a dependent joins the queue only when its count reaches zero. If I cannot process all tasks, 
# the remaining tasks are blocked by a cycle, so I return None. The time complexity is 𝑂(𝑉+𝐸), 
# and total space including the graph is 𝑂(V+E).”

# “I use topological sort when the edges represent precedence constraints rather than merely 
# relationships. It gives a valid execution order for a DAG, and the same indegree-based 
# process detects impossible workflows: if some tasks never reach zero unmet prerequisites, 
# the graph contains a cycle.”

from collections import deque
def topo_sort(tasks, dependencies):

    indegree = {}
    graph = {}   

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
        task = ready.popleft()
        output.append(task)

#     For every dependent unlocked by this task:
#         Decrease that dependent’s indegree by one.

        for dependency in graph[task]:
            indegree[dependency] -= 1
#         If its indegree is now zero:
#             Add it to ready queue.
            if indegree[dependency] == 0:
                ready.append(dependency)

# If output contains fewer tasks than the input:
#     Return None because a cycle prevented some tasks from becoming ready.
    if (len(output) != len(tasks)):
        return None
    
# Return output order.
    return(output)


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

print(topo_sort(tasks, dependencies))

tasks = ["A", "B", "C"]

dependencies = [
    ("A", "B"),
    ("B", "C"),
    ("C", "A"),
]

print(topo_sort(tasks, dependencies))
