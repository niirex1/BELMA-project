import hashlib

class DHTLoadBalancer:
    def __init__(self, nodes):
        self.DHT_Table = {}
        self.Node_Tasks = {node: [] for node in nodes}
        
    def add_node(self, node):
        """Add a node to the DHT Table."""
        self.DHT_Table[node] = []
        self.Node_Tasks[node] = []
        
    def compute_hash(self, task):
        """Compute the hash value of a task."""
        return hashlib.sha256(str(task).encode()).hexdigest()
        
    def locate_closest_node(self, hash_value):
        """Locate the closest node in the DHT Table using the hash value."""
        # Dummy implementation for demonstration
        # In a real-world scenario, you would use the hash value to find the closest node
        return list(self.DHT_Table.keys())[0]
        
    def distribute_tasks(self, tasks):
        """Distribute tasks among nodes."""
        for task in tasks:
            hash_value = self.compute_hash(task)
            closest_node = self.locate_closest_node(hash_value)
            self.Node_Tasks[closest_node].append(task)
            
        for node in self.Node_Tasks:
            self.DHT_Table[node] = self.Node_Tasks[node]
            
        return self.Node_Tasks

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
