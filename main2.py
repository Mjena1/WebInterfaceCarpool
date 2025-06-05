
import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import os
from dotenv import load_dotenv
import time
import pandas as pd
import to_office_google_api
import to_home_google_api
from plotTo import plot as pltTo
from plotFrom import plot as pltFrom

# Load API key from .env file
load_dotenv()
# api_key = os.getenv('api_key')
api_key = st.secrets['api_key']

# Hardcoded credentials for admin
ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "admin"

# Function to get latitude and longitude from address
def get_lat_lon(address, api_key):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {'address': address, 'key': api_key}
    response = requests.get(url, params=params)
    response.raise_for_status()
    result = response.json()
    location = result['results'][0]['geometry']['location']
    return (location['lat'], location['lng'])


# Session state to track login and demo state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "demo_started" not in st.session_state:
    st.session_state.demo_started = False
if "demo_choice" not in st.session_state:
    st.session_state.demo_choice = None
if "show_results" not in st.session_state: # New state for showing results page
    st.session_state.show_results = False
if "algorithm_output" not in st.session_state: # To store algorithm results
    st.session_state.algorithm_output = None

def login():
    st.markdown("<h1 style='text-align: center;'>🔐 Admin Login</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Please enter your credentials to continue</h3>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        email = st.text_input("📧 Email", placeholder="admin@admin.com")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter password")

        if st.button("➡️ Login"):
            if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid email or password")

def welcome():
    st.markdown("<h1 style='text-align: center;'>🎉 Welcome Page</h1>", unsafe_allow_html=True)
    st.write(f"Welcome, **{ADMIN_EMAIL}**! You have successfully logged in.")
    
    if st.button("🚗 Get started with the demo for carpooling"):
        st.session_state.demo_started = True
        st.rerun()

def demo_choice():
    st.markdown("<h1 style='text-align: center;'>🚗 Carpooling Demo</h1>", unsafe_allow_html=True)
    st.write("Are you ready to start the carpooling demo?")
    
    if st.button("✅ Yes"):
        st.session_state.demo_choice = "choose_direction"
        st.rerun()
    elif st.button("❌ No"):
        st.write("You can start the demo anytime by refreshing the page.")

def choose_direction():
    st.markdown("<h1 style='text-align: center;'>🚗 Choose Your Demo</h1>", unsafe_allow_html=True)
    st.write("Select the direction for the carpooling demo:")

    if st.button("➡️ To Office"):
        st.session_state.demo_choice = "to_office"
        st.rerun()
    elif st.button("⬅️ From Office"):
        st.session_state.demo_choice = "from_office"
        st.rerun()

def demo_to_office():
    # --- Check for results display FIRST ---
    if st.session_state.show_results and st.session_state.algorithm_output:
        locations, assignments, driver_paths, total_time = st.session_state.algorithm_output
        display_results_interface(locations, assignments, driver_paths, total_time)
        return # IMPORTANT: Stop execution here if results are displayed
    
    
    st.markdown("<h1 style='text-align: center;'>🚗 Carpooling Demo - To Office</h1>", unsafe_allow_html=True)
    st.write("This is the interface for carpooling **to the office**.")

    # Initialize session state
    if "companion_name" not in st.session_state:
        st.session_state.companion_name = "Manab"
        st.session_state.companion_location = "Zolo Arena"
        st.session_state.office_location = "Brigade Tech Gardens, Bangalore"
        st.session_state.num_drivers = 2
        st.session_state.show_map = False
        default_drivers = [
            ("Sundar Sri", "Nallur Halli Metro Station,Bangalore", 3),
            ("Abhijit Balan", "Marathahalli Bridge", 2),
            ("Tarun Chintapalli", "Sarjapura ,Bangalore", 2),
            ("Jay Gupta", "Indiranagar Metro station, Bangalore", 3),
            ("Kishore K", "HopeFarm,Bangalore", 2)
        ]
        for i in range(1, 6):
            st.session_state[f'driver_{i}_name'] = default_drivers[i-1][0]
            st.session_state[f'driver_{i}_location'] = default_drivers[i-1][1]
            st.session_state[f'driver_{i}_capacity'] = default_drivers[i-1][2]

    # Function to clear all input fields
    def clear_fields():
        st.session_state.companion_name = "Manab"
        st.session_state.companion_location = "Zolo Arena"
        st.session_state.office_location = "Brigade Tech Gardens, Bangalore"
        st.session_state.num_drivers = 2
        st.session_state.show_map = False
        default_drivers = [
            ("Sundar Sri", "Nallur Halli Metro Station,Bangalore", 3),
            ("Abhijit Balan", "Marathahalli Bridge", 2),
            ("Tarun Chintapalli", "Sarjapura ,Bangalore", 2),
            ("Jay Gupta", "Indiranagar Metro station, Bangalore", 3),
            ("Kishore K", "HopeFarm,Bangalore", 2)
        ]
        for i in range(1, 6):
            st.session_state[f'driver_{i}_name'] = default_drivers[i-1][0]
            st.session_state[f'driver_{i}_location'] = default_drivers[i-1][1]
            st.session_state[f'driver_{i}_capacity'] = default_drivers[i-1][2]

    # Sidebar inputs
    with st.sidebar:
        st.header("Companion Info")
        st.session_state.companion_name = st.text_input("Name", value=st.session_state.companion_name)
        st.session_state.companion_location = st.text_input("Location", value=st.session_state.companion_location)

        st.header("Office Info")
        st.session_state.office_location = st.text_input("Office Address", value=st.session_state.office_location)

        st.header("Drivers")
        st.session_state.num_drivers = st.slider("Number of Drivers", 1, 5, value=st.session_state.num_drivers)

        for i in range(1, st.session_state.num_drivers + 1):
            st.subheader(f"Driver {i}")
            st.session_state[f'driver_{i}_name'] = st.text_input(f"Name", key=f'driver_{i}_name_input', value=st.session_state[f'driver_{i}_name'])
            st.session_state[f'driver_{i}_location'] = st.text_input(f"Location", key=f'driver_{i}_location_input', value=st.session_state[f'driver_{i}_location'])
            st.session_state[f'driver_{i}_capacity'] = st.number_input(f"Capacity", min_value=1, max_value=10, value=st.session_state[f'driver_{i}_capacity'], key=f'driver_{i}_capacity_input')

        if st.button("Clear All"):
            clear_fields()
            st.rerun()

        if st.button("Update Map"):
            st.session_state.show_map = True


    # Main area: map display
    if st.session_state.show_map:
        try:
            office_lat, office_lon = get_lat_lon(st.session_state.office_location, api_key)

            # Collect all points for bounds
            all_points = [(office_lat, office_lon)]

            companion_lat, companion_lon = get_lat_lon(st.session_state.companion_location, api_key)
            all_points.append((companion_lat, companion_lon))

            for i in range(1, st.session_state.num_drivers + 1):
                driver_lat, driver_lon = get_lat_lon(st.session_state[f'driver_{i}_location'], api_key)
                all_points.append((driver_lat, driver_lon))

            # Calculate bounds
            min_lat = min(p[0] for p in all_points)
            max_lat = max(p[0] for p in all_points)
            min_lon = min(p[1] for p in all_points)
            max_lon = max(p[1] for p in all_points)
            center_lat = (min_lat + max_lat) / 2
            center_lon = (min_lon + max_lon) / 2

            m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
            m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

            # Add markers
            folium.Marker([office_lat, office_lon], tooltip="Office", icon=folium.Icon(color='blue')).add_to(m)
            folium.Marker([companion_lat, companion_lon], tooltip=st.session_state.companion_name or "Companion", icon=folium.Icon(color='green')).add_to(m)

            for i in range(1, st.session_state.num_drivers + 1):
                driver_lat, driver_lon = get_lat_lon(st.session_state[f'driver_{i}_location'], api_key)
                driver_name = st.session_state[f'driver_{i}_name'] or f"Driver {i}"
                folium.Marker([driver_lat, driver_lon], tooltip=driver_name, icon=folium.Icon(color='red')).add_to(m)

            st_folium(m,width=900, height=600)
        except Exception as e:
            st.error(f"Error generating map: {e}")

    # Red "Start the Algorithm" button
    st.markdown("""
        <style>
        div.stButton > button:first-child {
            background-color: red;
            color: white;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    if st.button("Start the Algorithm"):
        with st.spinner("Running the carpooling algorithm..."):
            locations = {
                "office": st.session_state.office_location,
                "drivers": {
                    st.session_state[f'driver_{i}_name']: st.session_state[f'driver_{i}_location']
                    for i in range(1, st.session_state.num_drivers + 1)
                    if st.session_state[f'driver_{i}_name'] and st.session_state[f'driver_{i}_location']
                },
                "companions": {
                    st.session_state.companion_name: st.session_state.companion_location    
                }
            }
            time_st=time.time()
            # print(locations)
            try:
                (geocoded_locations, assignments, driver_paths) = to_office_google_api.helper(locations)
                time_end=time.time()
                total_time=time_end-time_st
                st.success("Algorithm completed! We have our ride details !")
                print(geocoded_locations,assignments,driver_paths)
                
                st.session_state.algorithm_output = (geocoded_locations, assignments, driver_paths, total_time)
                
                st.session_state.show_results = True
                st.rerun()

            except Exception as e:
                st.error(f"Error running algorithm: {e}")
                st.session_state.show_results = False
                st.stop()
            


def demo_from_office():
    # --- Check for results display FIRST ---
    if st.session_state.show_results and st.session_state.algorithm_output:
        locations, assignments, driver_paths, total_time = st.session_state.algorithm_output
        display_results_interface1(locations, assignments, driver_paths, total_time)
        return # IMPORTANT: Stop execution here if results are displayed
    
    
    st.markdown("<h1 style='text-align: center;'>🚗 Carpooling Demo - From Office</h1>", unsafe_allow_html=True)
    st.write("This is the interface for carpooling **from the office**.")

    # Initialize session state
    if "num_companions" not in st.session_state:
        st.session_state.office_location = "Brigade Tech Gardens, Bangalore"
        st.session_state.num_companions = 3
        st.session_state.num_drivers = 2
        st.session_state.show_map = False

        default_companions = [
            ("Manab", "Zolo Arena, Bangalore"),
            ("Rohith", "Munnekolal,Bangalore"),
            ("Sayan", "Kundalhali Railway Station,Bangalore"),
            ("Aman", "DMart, Siddapura,Bangalore"),
            ("Hitesh", "EcoSpace , Bellandur,Bangalore")
        ]

        default_drivers = [
            ("Sundar Sri", "Nallur Halli Metro Station,Bangalore", 3),
            ("Abhijit Balan", "Marathahalli Bridge", 2),
            ("Tarun Chintapalli", "Sarjapura ,Bangalore", 2),
            ("Jay Gupta", "Indiranagar Metro station, Bangalore", 3),
            ("Kishore K", "HopeFarm,Bangalore", 2)
        ]

        for i in range(1, 6):
            st.session_state[f'companion_{i}_name'] = default_companions[i-1][0]
            st.session_state[f'companion_{i}_location'] = default_companions[i-1][1]
            st.session_state[f'driver_{i}_name'] = default_drivers[i-1][0]
            st.session_state[f'driver_{i}_location'] = default_drivers[i-1][1]
            st.session_state[f'driver_{i}_capacity'] = default_drivers[i-1][2]


        # Function to clear all input fields
        def clear_fields():
            st.session_state.office_location = "Brigade Tech Gardens, Bangalore"
            st.session_state.num_companions = 3
            st.session_state.num_drivers = 2
            st.session_state.show_map = False
            for i in range(1, 6):
                st.session_state[f'companion_{i}_name'] = default_companions[i-1][0]
                st.session_state[f'companion_{i}_location'] = default_companions[i-1][1]
                st.session_state[f'driver_{i}_name'] = default_drivers[i-1][0]
                st.session_state[f'driver_{i}_location'] = default_drivers[i-1][1]
                st.session_state[f'driver_{i}_capacity'] = default_drivers[i-1][2]

    # Sidebar inputs
    with st.sidebar:
        st.header("Office Info")
        st.session_state.office_location = st.text_input("Office Address", value=st.session_state.office_location)

        st.header("Companions")
        st.session_state.num_companions = st.slider("Number of Companions", 1, 5, value=st.session_state.num_companions)
        for i in range(1, st.session_state.num_companions + 1):
            st.subheader(f"Companion {i}")
            st.session_state[f'companion_{i}_name'] = st.text_input(f"Name", key=f'companion_{i}_name_input', value=st.session_state[f'companion_{i}_name'])
            st.session_state[f'companion_{i}_location'] = st.text_input(f"Location", key=f'companion_{i}_location_input', value=st.session_state[f'companion_{i}_location'])

        st.header("Drivers")
        st.session_state.num_drivers = st.slider("Number of Drivers", 1, 5, value=st.session_state.num_drivers)
        for i in range(1, st.session_state.num_drivers + 1):
            st.subheader(f"Driver {i}")
            st.session_state[f'driver_{i}_name'] = st.text_input(f"Name", key=f'driver_{i}_name_input', value=st.session_state[f'driver_{i}_name'])
            st.session_state[f'driver_{i}_location'] = st.text_input(f"Location", key=f'driver_{i}_location_input', value=st.session_state[f'driver_{i}_location'])
            st.session_state[f'driver_{i}_capacity'] = st.number_input(f"Capacity", min_value=1, max_value=10, value=st.session_state[f'driver_{i}_capacity'], key=f'driver_{i}_capacity_input')

        if st.button("Clear All"):
            clear_fields()
            st.rerun()

        if st.button("Update Map"):
            st.session_state.show_map = True

    # Main area: map display
    if st.session_state.show_map:
        try:
            office_lat, office_lon = get_lat_lon(st.session_state.office_location, api_key)

            # Collect all points for bounds
            all_points = [(office_lat, office_lon)]

            for i in range(1, st.session_state.num_companions + 1):
                lat, lon = get_lat_lon(st.session_state[f'companion_{i}_location'], api_key)
                all_points.append((lat, lon))

            for i in range(1, st.session_state.num_drivers + 1):
                lat, lon = get_lat_lon(st.session_state[f'driver_{i}_location'], api_key)
                all_points.append((lat, lon))

            # Calculate bounds
            min_lat = min(p[0] for p in all_points)
            max_lat = max(p[0] for p in all_points)
            min_lon = min(p[1] for p in all_points)
            max_lon = max(p[1] for p in all_points)
            center_lat = (min_lat + max_lat) / 2
            center_lon = (min_lon + max_lon) / 2

            m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
            m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

            # Add markers
            folium.Marker([office_lat, office_lon], tooltip="Office", icon=folium.Icon(color='blue')).add_to(m)

            for i in range(1, st.session_state.num_companions + 1):
                name = st.session_state[f'companion_{i}_name'] or f"Companion {i}"
                lat, lon = get_lat_lon(st.session_state[f'companion_{i}_location'], api_key)
                folium.Marker([lat, lon], tooltip=name, icon=folium.Icon(color='green')).add_to(m)

            for i in range(1, st.session_state.num_drivers + 1):
                name = st.session_state[f'driver_{i}_name'] or f"Driver {i}"
                lat, lon = get_lat_lon(st.session_state[f'driver_{i}_location'], api_key)
                folium.Marker([lat, lon], tooltip=name, icon=folium.Icon(color='red')).add_to(m)

            st_folium(m,width=900, height=600)
        except Exception as e:
            st.error(f"Error generating map: {e}")

    # Red "Start the Algorithm" button
    st.markdown("""
        <style>
        div.stButton > button:first-child {
            background-color: red;
            color: white;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    if st.button("Start the Algorithm"):
        with st.spinner("Running the carpooling algorithm..."):
            locations = {
                "office": st.session_state.office_location,
                "drivers": {
                    st.session_state[f'driver_{i}_name']: st.session_state[f'driver_{i}_location']
                    for i in range(1, st.session_state.num_drivers + 1)
                    if st.session_state[f'driver_{i}_name'] and st.session_state[f'driver_{i}_location']
                },
                "companions": {
                    st.session_state[f'companion_{i}_name']: st.session_state[f'companion_{i}_location']
                    for i in range(1, st.session_state.num_companions + 1)
                    if st.session_state[f'companion_{i}_name'] and st.session_state[f'companion_{i}_location']     
                }
            }
            capacity={
                st.session_state[f'driver_{i}_name']: st.session_state[f'driver_{i}_capacity']
                for i in range(1, st.session_state.num_drivers + 1)
                if st.session_state[f'driver_{i}_name'] and st.session_state[f'driver_{i}_capacity']
            }
            time_st=time.time()
            # print(locations)
            try:
                print(1)
                (geocoded_locations, assignments, driver_paths) = to_home_google_api.helper(locations,capacity)
                print(2)
                time_end=time.time()
                total_time=time_end-time_st
                st.success("Algorithm completed! We have our ride details !")
                print(geocoded_locations,assignments,driver_paths)
                
                st.session_state.algorithm_output = (geocoded_locations, assignments, driver_paths, total_time)
                
                st.session_state.show_results = True
                st.rerun()

            except Exception as e:
                st.error(f"Error running algorithm: {e}")
                st.session_state.show_results = False
                st.stop()
                
        


def display_results_interface(locations, assignments, driver_paths, algorithm_time):
    st.markdown("<h1 style='text-align: center;'>🗺️ Carpooling Results Map</h1>", unsafe_allow_html=True)

    st.markdown("### Optimized Routes Map")
    
    m = pltTo(locations ,assignments , driver_paths)
    if m is not None:
        st_folium(m, width=1000, height=600)
    else:
        st.error("Map could not be generated. Ensure 'pltTo' function works correctly and returns a Folium map object.")

    st.markdown("---")

    st.markdown("### Carpooling Assignments")
    if assignments:
        assignment_data = []
        for driver, companions_data in assignments.items():
            for companion_name, _ in companions_data:
                assignment_data.append({"Driver": driver, "Companion": companion_name})
        
        df_assignments = pd.DataFrame(assignment_data)
        st.table(df_assignments)
    else:
        st.info("No assignments were generated. Check your algorithm and inputs.")

    st.markdown("---")

    st.markdown("### Algorithm Performance")
    st.write(f"**Time taken to run the algorithm:** {algorithm_time:.4f} seconds")

def display_results_interface1(locations, assignments, driver_paths, algorithm_time):
    st.markdown("<h1 style='text-align: center;'>🗺️ Carpooling Results Map</h1>", unsafe_allow_html=True)

    st.markdown("### Optimized Routes Map")
    
    m = pltFrom(locations ,assignments , driver_paths)
    if m is not None:
        st_folium(m, width=1000, height=600)
    else:
        st.error("Map could not be generated. Ensure 'pltFrom' function works correctly and returns a Folium map object.")

    st.markdown("---")

    st.markdown("### Carpooling Assignments")
    if assignments:
        assignment_data = []
        for driver, companions_data in assignments.items():
            for companion_name, _ in companions_data:
                assignment_data.append({"Driver": driver, "Companion": companion_name})
        
        df_assignments = pd.DataFrame(assignment_data)
        st.table(df_assignments)
    else:
        st.info("No assignments were generated. Check your algorithm and inputs.")

    st.markdown("---")

    st.markdown("### Algorithm Performance")
    st.write(f"**Time taken to run the algorithm:** {algorithm_time:.4f} seconds")

def navigation_buttons(back_target=None):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔙 Go Back") and back_target:
            st.session_state.demo_choice = back_target
            st.rerun()
    with col2:
        if st.button("🚪 Log Out"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()
            


# Main logic
if not st.session_state.logged_in:
    login()
elif not st.session_state.demo_started:
    welcome()
elif st.session_state.demo_choice == "choose_direction":
    choose_direction()
    navigation_buttons(back_target=None)
elif st.session_state.demo_choice == "to_office":
    demo_to_office()
    navigation_buttons(back_target="choose_direction")
elif st.session_state.demo_choice == "from_office":
    demo_from_office()
    navigation_buttons(back_target="choose_direction")
else:
    demo_choice()
    navigation_buttons(back_target=None)
