import streamlit as st
import folium
import requests
import os
from dotenv import load_dotenv
import polyline

# Load API Key from environment variables
load_dotenv()
api_key = st.secrets['api_key']

def get_lat_lon(address, api_key):
    """
    Geocodes an address to get latitude and longitude using Google Maps API.
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {'address': address, 'key': api_key}
    response = requests.get(url, params=params)
    response.raise_for_status()
    result = response.json()
    location = result['results'][0]['geometry']['location']
    return (location['lat'], location['lng'])



def get_directions(origin, destination, api_key, mode='walking'):
    url = "https://maps.googleapis.com/maps/api/directions/json"

    # Convert (lat, lon) tuples to "latitude,longitude" strings
    origin_str = f"{origin[0]},{origin[1]}"
    destination_str = f"{destination[0]},{destination[1]}"

    params = {
        'origin': origin_str,
        'destination': destination_str,
        'key': api_key,
        'mode': mode
    }
    response = requests.get(url, params=params)
    
    directions = response.json()
    
    # Check for successful response and routes
    if directions['status'] == 'OK' and directions['routes']:
        polyline_str = directions['routes'][0]['overview_polyline']['points']
        decoded_points = polyline.decode(polyline_str)
        return decoded_points
    else:
        # Handle cases where no route is found or API call fails
        print(f"Error fetching directions: {directions['status']}")
        return None

def plot(locations, assignments, driver_paths):
    """
    Plots driver and companion paths on a map using Folium.

    Args:
        locations: Dictionary with keys `office` and `companions`.
        assignments: Dictionary mapping drivers to companions and meeting points.
        driver_paths: Dictionary mapping drivers to their coordinates.
    """
    # Get office coordinates
    office_coords = get_lat_lon(locations["office"], api_key)

    # Get coordinates for companions
    companion_coords = {
        companion: get_lat_lon(address, api_key)
        for companion, address in locations["companions"].items()
    }

    print(f"locations: {locations} and assignments: {assignments}")

    # Create the map centered on the office
    mymap = folium.Map(location=office_coords, zoom_start=12)
    folium.Marker(office_coords, popup=f"Office", icon=folium.Icon(color='red')).add_to(mymap)
    # Colors for drivers
    colors = ['red', 'blue', 'green', 'purple']
    
    i=0


    # Add companion meeting paths
    for driver, companion_list in assignments.items():
        coords=driver_paths[driver]     
        folium.PolyLine(coords, color=colors[i % len(colors)], weight=5, opacity=0.8).add_to(mymap)
        folium.Marker(coords[0], popup=f"Driver: {driver}", icon=folium.Icon(color='blue')).add_to(mymap)
        i=i+1
        for companion, coordinates in companion_list:
            companion_coord = companion_coords[companion]
            companion_paths = get_directions(companion_coord,coordinates,api_key)
            folium.PolyLine(companion_paths, color='black', weight=4, opacity=0.6).add_to(mymap)
            folium.Marker(companion_coord, popup=f"Companion: {companion}", icon=folium.Icon(color='green')).add_to(mymap)
            folium.Marker(coordinates, popup=f"Meeting Point for {companion}", icon=folium.Icon(color='red')).add_to(mymap)

    # Save the map to an HTML file
    mymap.save('map.html')
    print("The paths have been plotted and saved to map.html.")
    return mymap
