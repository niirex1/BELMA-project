import hashlib

class DHTLoadBalancer:
    def __init__(self, nodes):
        self.nodes = sorted(nodes)
        self.DHT_Table = {node: [] for node in nodes}
    
    def hash_function(self, key):
        """Hash function to map keys to nodes."""
        return int(hashlib.sha1(key.encode('utf-8')).hexdigest(), 16) % len(self.nodes)

    def add_node(self, node):
        """Add a node to the DHT Table."""
        self.nodes.append(node)
        self.nodes.sort()
        self.DHT_Table[node] = []

    def locate_closest_node(self, key):
        """Find the closest node for a given key."""
        hash_value = self.hash_function(key)
        for node in self.nodes:
            if self.hash_function(node) >= hash_value:
                return node
        return self.nodes[0]

    def distribute_tasks(self, tasks):
        """Distribute tasks among nodes based on hash values."""
        for task in tasks:
            node = self.locate_closest_node(task)
            self.DHT_Table[node].append(task)
        return self.DHT_Table

# Example usage
nodes = ["Node1", "Node2", "Node3"]
tasks = ["Task1", "Task2", "Task3", "Task4"]

dht_load_balancer = DHTLoadBalancer(nodes)

# Add nodes to DHT Table
for node in nodes:
    dht_load_balancer.add_node(node)

# Distribute tasks
distributed_tasks = dht_load_balancer.distribute_tasks(tasks)
print("Distributed Task List:", distributed_tasks)
