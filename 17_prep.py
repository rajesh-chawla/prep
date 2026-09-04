# Contract: input / output / constraints
# Assumptions: empty? duplicates? ordering? malformed?
# Representation: ___ because ___
# Complexity: time ___ / space ___
#
# Implement: smallest correct happy path
# Invariant:
#
# Test: normal / boundary / duplicate / invalid
# If stuck: tiny example -> trace -> simplify
# Production: one relevant extension after correctness

# Input -
# {
#     "source_node": "destination_node"
#     "source_node": "destination"    
# }

# As an FDE, I would use this representation whenever the customer problem has meaningful 
# relationships rather than just independent records—for example workflow dependencies, 
# service topology, data lineage, access relationships, or a knowledge graph. The adjacency 
# list gives a compact way to represent each node’s direct relationships, then graph 
# algorithms can answer questions such as what is reachable, what depends on a failed service, 
# what can run in parallel, whether there is a cycle, or what related context should be retrieved.

# At production scale, the same conceptual graph may live in a graph database, a relational 
# relationship table, a document/indexing pipeline, or a distributed service catalog. The 
# representation and storage choice depend on graph size, update rate, query patterns, tenancy, 
# authorization requirements, and latency targets.

# For knowledge-graph context, an adjacency list can represent entity relationships in a simple 
# prototype. Given a query-relevant entity, traversal can expand to related documents, claims, 
# owners, systems, or dependencies. In a production GraphRAG system, I would filter every traversal 
# by tenant and authorization boundaries, rank or bound the retrieved subgraph, preserve source 
# provenance, and evaluate whether the extra graph context improves the customer outcome.

def build_adjacency_list(edges):
    adjacency_list = {}
    
    for source, target in edges:
        if source not in adjacency_list:
            adjacency_list[source] = set()
        if target not in adjacency_list:
            adjacency_list[target] = set()
        adjacency_list[source].add(target) 
    
    return (adjacency_list)
    
edges = [
    ("A", "B"),
    ("A", "C"),
    ("B", "D"),
    ("A", "B"),  # Duplicate edge
]

#result = build_adjacency_list(edges)
#print(result)

# “I use a deque as a FIFO queue so I process nodes breadth-first. The visited set ensures each node is 
# discovered only once, which prevents repeated work and cycles. Since the required output is traversal 
# order, I retain a list and append each node in BFS processing order. The traversal is 
# 𝑂(𝑉+𝐸) time and uses 𝑂(𝑉) additional space.”

# “BFS is nearest-first with respect to graph hop count. It visits direct neighbors before two-hop 
# neighbors, so it finds minimum-hop paths in an unweighted graph. I would not call it generic 
# nearest-neighbor search, because that term often means similarity search in vector or geometric space. 
# If proximity means latency, cost, or risk rather than hop count, I would use a weighted shortest-path 
# algorithm such as Dijkstra’s.”

from collections import deque

graph = {
    "api": {"auth", "orders"},
    "auth": {"database"},
    "orders": {"database", "email"},
    "database": set(),
    "email": set(),
}

def breadth_first(graph, start_node):
    visited = set()
    order_visited = []
    bfs = deque()
    
    if start_node in graph:
        bfs.append(start_node)
        visited.add(start_node)
        order_visited.append(start_node)
    
    while len(bfs) > 0:
        node = bfs.popleft()
        order_visited.append(node)

        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                bfs.append(neighbor)
    
    return (order_visited) 
       
#result = breadth_first(graph, "api")
#print(result)

# “Given an unweighted graph, a start node, and a target node, I will use breadth-first search to 
# return the minimum-hop path if one exists. BFS explores nodes level by level, so the first time 
# it discovers the target, it has found a shortest path measured by number of edges. I’ll maintain a 
# FIFO queue for nodes to explore, a visited set so each node is discovered once, and a predecessor 
# dictionary that records the node from which each node was first reached. I can then reconstruct 
# the path by walking backward from the target to the start and reversing the result.”

graph = {
    "api": {"auth", "orders"},
    "auth": {"database"},
    "orders": {"database", "email"},
    "database": set(),
    "email": set(),

    "billing": {"ledger"},
    "ledger": set(),
}

def shortest_path(graph, start_node, target_node):
    visited = set()
    # order_visited = []
    bfs = deque()

    if target_node not in graph:
        return None

    if start_node not in graph:
        return None

    if start_node == target_node:
        return [start_node]
    
    bfs.append(start_node)
    visited.add(start_node)
    #order_visited.append(start_node)
    previous = {start_node: None}
    
    while bfs:
        node = bfs.popleft()
        #order_visited.append(node)

        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                bfs.append(neighbor)
                previous[neighbor] = node

    path = []
    current = target_node

    if target_node not in previous:
        return None
    
    while current is not None:
        path.append(current)
        current = previous[current]

    path.reverse()
    return (path) 
       
result = shortest_path(graph, "api", "ledger")
print(result)