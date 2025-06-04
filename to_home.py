import osmnx as ox
import networkx as nx
import math

#************************* help functions **********************************************
def calculate_aerial_distance(graph, node1, node2):
    lat1, lon1 = graph.nodes[node1].get('x'), graph.nodes[node1].get('y')
    lat2, lon2 = graph.nodes[node2].get('x'), graph.nodes[node2].get('y')
    
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')
    
    return get_distance_from_lat_lon_in_km(lat1, lon1, lat2, lon2)

def get_distance_from_lat_lon_in_km(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of the Earth in kilometers
    dLat = deg2rad(lat2 - lat1)
    dLon = deg2rad(lon2 - lon1)
    a = math.sin(dLat / 2) ** 2 + math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) * math.sin(dLon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = R * c
    return d

def deg2rad(deg):
    return deg * (math.pi / 180)

def calculate_driver_companion_distances(graph, driver_paths, companion_nodes):
    aerial_distances = {}
    
    for driver_name, path in driver_paths.items():
        if not path:
            continue
        for companion_name, companion_node in companion_nodes.items():
            distances = []
            for node in path:
                if node in graph.nodes and companion_node in graph.nodes:
                    distance = calculate_aerial_distance(graph, node, companion_node)
                    distances.append((node, distance))
            
            top_5_nodes = sorted(distances, key=lambda x: x[1])[:5]
            aerial_distances[(driver_name, companion_name)] = top_5_nodes
                
    road_distances = {}
    
    for (driver_name, companion_name), top_5_nodes in aerial_distances.items():
        shortest_road_distance = float('inf')
        shortest_road_time = float('inf')
        intersection_node = None       
        for node, _ in top_5_nodes:
            try:
                path = nx.shortest_path(graph, source=node, target=companion_nodes[companion_name], weight='length')
                road_distance = nx.shortest_path_length(graph, source=node, target=companion_nodes[companion_name], weight='length')               
                total_travel_time = sum(graph[u][v][0].get('travel_time', 0) 
                                        for u, v in zip(path[:-1], path[1:]))
                
                if road_distance < shortest_road_distance:
                    shortest_road_distance = road_distance
                    shortest_road_time = total_travel_time
                    intersection_node = node
            except nx.NetworkXNoPath:
                continue        
        road_distances[(driver_name, companion_name)] = (shortest_road_distance, shortest_road_time, intersection_node) 
    return road_distances

def assign_companion_to_driver(road_distances, driver_capacity):
    sorted_distances = sorted(road_distances.items(), key=lambda x: x[1][0])
    
    assignments = {driver: [] for driver in driver_capacity.keys()}
    companion_assigned = set()  # Track assigned companions

    for (driver, companion), (_, _, nd) in sorted_distances:
        if len(assignments[driver]) < driver_capacity[driver] and companion not in companion_assigned:
            assignments[driver].append((companion, nd))
            companion_assigned.add(companion)  # Mark this companion as assigned

    return assignments
#************************* help functions **********************************************

##************************* Constants **********************************************
locations = {
    "office": (12.9715987, 77.5945627),
    "drivers": {
        "Driver A": (12.935192, 77.624480),
        "Driver B": (12.971891, 77.641151),
    },
    "companions": {
        "Companion 1": (12.960632, 77.638496),
        "Companion 2": (12.932568, 77.619218),
        "Companion 3": (12.987631, 77.625515),
        "Companion 4": (12.935230, 77.610116),
    },
}
#************************* Constants **********************************************

def helper(graph):
    office_node = ox.distance.nearest_nodes(graph, locations["office"][1], locations["office"][0])
    
    driver_nodes = {name: ox.distance.nearest_nodes(graph, loc[1], loc[0]) for name, loc in locations["drivers"].items()}
    companion_nodes = {name: ox.distance.nearest_nodes(graph, loc[1], loc[0]) for name, loc in locations["companions"].items()}
      
    capacity = {
        list(driver_nodes.keys())[0]: 3,  # Driver A
        list(driver_nodes.keys())[1]: 2,  # Driver B
    }
     
    driver_paths = {}
    for driver_name, node in driver_nodes.items():
        try:
            driver_paths[driver_name] = nx.shortest_path(graph, source=node, target=office_node, weight="travel_time")
        except nx.NetworkXNoPath:
            driver_paths[driver_name] = []   
    print(driver_paths)       
    road_distances = calculate_driver_companion_distances(graph, driver_paths, companion_nodes)
    print(road_distances)
    assignments = assign_companion_to_driver(road_distances, capacity)
    return (locations, assignments,driver_paths)
