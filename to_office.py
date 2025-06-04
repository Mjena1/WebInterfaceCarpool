import osmnx as ox
import networkx as nx
import math
from typing import Dict, List, Tuple



#*********************************** Helper Functions ***************************************
def calculate_aerial_distance(graph: nx.Graph, node1: int, node2: int) -> float:
    """Calculate the aerial distance between two nodes."""
    lat1, lon1 = graph.nodes[node1].get('y'), graph.nodes[node1].get('x')
    lat2, lon2 = graph.nodes[node2].get('y'), graph.nodes[node2].get('x')
    
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')
    
    return get_distance_from_lat_lon_in_km(lat1, lon1, lat2, lon2)

def get_distance_from_lat_lon_in_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute the distance between two latitude-longitude points in kilometers."""
    R = 6371  # Radius of the Earth in kilometers
    dLat = deg2rad(lat2 - lat1)
    dLon = deg2rad(lon2 - lon1)
    a = math.sin(dLat / 2) ** 2 + math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) * math.sin(dLon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def deg2rad(deg: float) -> float:
    """Convert degrees to radians."""
    return deg * (math.pi / 180)

def find_best_paths(graph: nx.Graph, locations: Dict[str, Tuple[float, float]]) -> Dict[str, List[int]]:
    """Compute the shortest paths from drivers to the office based on travel time."""
    office_location = locations['office']
    office_node = ox.distance.nearest_nodes(graph, office_location[1], office_location[0])
    
    paths = {}
    
    for label, (lat, lon) in locations.items():
        if label.startswith('driver'):
            driver_node = ox.distance.nearest_nodes(graph, lon, lat)
            try:
                path = nx.shortest_path(graph, source=driver_node, target=office_node, weight='travel_time')
                paths[label] = path
            except nx.NetworkXNoPath:
                paths[label] = []  # No path found
    
    return paths

def calculate_driver_companion_distances(
    graph: nx.Graph,
    driver_paths: Dict[str, List[int]],
    companion_nodes: List[int]
) -> Dict[Tuple[str, int], List[Tuple[int, float]]]:
    """Calculate the top 5 closest nodes for each driver-companion pair based on aerial distance."""
    aerial_distances = {}
    
    for driver_label, path in driver_paths.items():
        if not path:
            continue
        for companion_node in companion_nodes:
            distances = []
            for node in path:
                if node in graph.nodes and companion_node in graph.nodes:
                    distance = calculate_aerial_distance(graph, node, companion_node)
                    distances.append((node, distance))
            
            top_5_nodes = sorted(distances, key=lambda x: x[1])[:8]
            aerial_distances[(driver_label, companion_node)] = top_5_nodes
    
    return aerial_distances

def find_best_intersection_node(
    graph: nx.Graph,
    driver_paths: Dict[str, List[int]],
    companion_nodes: List[int],
    aerial_distances: Dict[Tuple[str, int], List[Tuple[int, float]]]
) -> Dict[Tuple[str, int], Tuple[float, float, int]]:
    """Find the best intersection node among the top 5 nodes for each driver-companion pair."""
    road_distances = {}
    buffer_time=5
    for (driver_label, companion_node), top_5_nodes in aerial_distances.items():
        shortest_road_distance = float('inf')
        shortest_road_time = float('inf')
        best_intersection_node = None
        
        for node, _ in top_5_nodes:
            # Calculate road distance and travel time from driver to intersection node
            road_distance_to_intersection = nx.shortest_path_length(graph, source=driver_paths[driver_label][0], target=node, weight='length')
            travel_time_to_intersection = nx.shortest_path_length(graph, source=driver_paths[driver_label][0], target=node, weight='travel_time')
            
            # Calculate road distance and travel time from the intersection node to the companion
            path_from_intersection = nx.shortest_path(graph, source=node, target=companion_node, weight='length')
            road_distance_from_intersection = nx.shortest_path_length(graph, source=node, target=companion_node, weight='length')
            travel_time_from_intersection = sum(graph[u][v][0].get('travel_time', 0) for u, v in zip(path_from_intersection[:-1], path_from_intersection[1:]))
            
            
            if road_distance_from_intersection < shortest_road_distance and travel_time_from_intersection <= (travel_time_to_intersection + buffer_time):
                shortest_road_distance = road_distance_from_intersection
                shortest_road_time = travel_time_from_intersection
                best_intersection_node = node
        
        road_distances[(driver_label, companion_node)] = (shortest_road_distance, shortest_road_time, best_intersection_node)
    
    return road_distances

#*********************************** Helper Functions ***************************************

##************************* Constants ******************************************************
locations = {
    "office": (12.934, 77.62),
    "drivers": {
        "Driver A": (13.064165569984327, 77.69139096635745),
        "Driver B": (12.9417027837777, 77.6047024498736),
        "Driver C": (12.954032807906207, 77.65954983678637),
        "Driver D": (13.058517489154386, 77.60478468841292),
        "Driver E": (12.880261914881979, 77.53660170901598),
        "Driver F": (12.940454648155722, 77.53464148361742)
    },
    "companions": {
        "Companion 1": (12.937,77.628)
    },
}
#************************* Constants ******************************************************

def helper(graph: nx.Graph) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, Tuple[int, int]]]:
    office_node = ox.distance.nearest_nodes(graph, locations["office"][1], locations["office"][0])
    
    driver_nodes = {name: ox.distance.nearest_nodes(graph, loc[1], loc[0]) for name, loc in locations["drivers"].items()}
    companion_nodes = {name: ox.distance.nearest_nodes(graph, loc[1], loc[0]) for name, loc in locations["companions"].items()}
    
    driver_paths = {}
    for driver_label, node in driver_nodes.items():
        try:
            driver_paths[driver_label] = nx.shortest_path(graph, source=node, target=office_node, weight="travel_time")
        except nx.NetworkXNoPath:
            driver_paths[driver_label] = []  
    
    aerial_distances = calculate_driver_companion_distances(graph, driver_paths, list(companion_nodes.values()))
    # print(aerial_distances)
    driver_companion_distances = find_best_intersection_node(graph, driver_paths, list(companion_nodes.values()), aerial_distances)
    
    # Find the best driver-companion pairing
    best_driver = None
    best_distance = float('inf')
    best_intersection_node = None

    for (driver_label, companion_node), (distance, time, intersection) in driver_companion_distances.items():
        if distance < best_distance:
            best_distance = distance
            best_driver = driver_label
            best_intersection_node = intersection
            
    return (locations, {best_driver: [(list(companion_nodes.keys())[0], best_intersection_node)]},driver_paths)

