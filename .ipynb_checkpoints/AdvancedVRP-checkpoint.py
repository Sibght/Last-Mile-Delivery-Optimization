import os
import time
import random
import requests
import folium
import itertools
import networkx as nx
import osmnx as ox
from folium.plugins import AntPath
from folium.features import DivIcon
from shapely.geometry import LineString
from networkx.algorithms import approximation as approx
from geopy.geocoders import Nominatim
from folium.plugins import MarkerCluster, Search, AntPath


########################################
# 0) Fallbacks
########################################
geo_fallbacks = {
    "Warehouse 1, Jabal Ali, Dubai, UAE": (24.9837, 55.0673),
    "Warehouse 2, Al Awir, Dubai, UAE": (25.1555, 55.5045),
    "Fulfillment Center 1, Mudon, Dubai, UAE": (25.0529, 55.2774),
    "Fulfillment Center 2, Al Manara, Dubai, UAE": (25.1412, 55.2148),
    "Fulfillment Center 3, Al Garhoud, Dubai, UAE": (25.2432, 55.3487),
    "Fulfillment Center 4, Warsan 1, Dubai, UAE": (25.1614, 55.4184),
}

########################################
# 1) Setup & Geocoding
########################################
geolocator = Nominatim(user_agent="route_optimization_app")

def geocode_locations(locations_list):
    geolocations = []
    for loc in locations_list:
        try:
            result = geolocator.geocode(loc, timeout=5)
            if result:
                geolocations.append((result.latitude, result.longitude))
                print(f"✅ {loc} => Lat: {result.latitude}, Lon: {result.longitude}")
            else:
                if loc in geo_fallbacks:
                    lat, lon = geo_fallbacks[loc]
                    geolocations.append((lat, lon))
                    print(f"⚠️ Using fallback for {loc}: Lat {lat}, Lon {lon}")
                else:
                    print(f"❌ {loc} => No geocoding results. (Consider adding a fallback)")
                    geolocations.append(None)
        except Exception as e:
            print(f"❌ Error geocoding {loc}: {e}")
            geolocations.append(None)
        time.sleep(0.1)
    return geolocations

########################################
# 2) TomTom Real-Time Traffic
########################################
def fetch_tomtom_traffic(coordinates, tomtom_api_key):
    base_url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    live_speeds = {}
    for (lat, lon) in coordinates:
        params = {"point": f"{lat},{lon}", "unit": "KMPH", "key": tomtom_api_key}
        try:
            r = requests.get(base_url, params=params)
            r.raise_for_status()
            data = r.json()
            if "flowSegmentData" in data:
                seg = data["flowSegmentData"]
                speed = seg.get("currentSpeed", 1)
                live_speeds[(lat, lon)] = speed
            else:
                live_speeds[(lat, lon)] = 1
        except:
            live_speeds[(lat, lon)] = 1
    print(f"✅ TomTom traffic for {len(live_speeds)} coords.")
    return live_speeds

########################################
# 3) Prepare Warehouses, FCs, and Delivery Points
########################################
all_locations = [
    "Warehouse 1, Jabal Ali, Dubai, UAE",
    "Warehouse 2, Al Awir, Dubai, UAE",
    "Fulfillment Center 1, Mudon, Dubai, UAE",
    "Fulfillment Center 2, Al Manara, Dubai, UAE",
    "Fulfillment Center 3, Al Garhoud, Dubai, UAE",
    "Fulfillment Center 4, Warsan 1, Dubai, UAE",
    "Arabian Ranches 2, Dubai, UAE",
    "Remraam, Dubai, UAE",
    "DAMAC Hills, Dubai, UAE",
    "Dubai Studio City, Dubai, UAE",
    "Motor City, Dubai, UAE",
    "Jumeirah Beach, Dubai, UAE",
    "Umm Suqeim, Dubai, UAE",
    "Al Safa, Dubai, UAE",
    "Al Wasl, Dubai, UAE",
    "Al Barsha, Dubai, UAE",
    "Port Saeed, Dubai, UAE",
    "Umm Ramool, Dubai, UAE",
    "Nad Al Hamar, Dubai, UAE",
    "Mirdif, Dubai, UAE",
    "Al Rashidiya, Dubai, UAE",
    "International City, Dubai, UAE",
    "Academic City, Dubai, UAE",
    "Nad Al Sheba, Dubai, UAE",
    "Al Warqa, Dubai, UAE",
    "Dubai Silicon Oasis, Dubai, UAE",
]

time_priority_info = {}
for idx, loc in enumerate(all_locations):
    if idx < 2:
        time_priority_info[loc] = {"priority": None, "time_window": None}
    elif idx < 6:
        time_priority_info[loc] = {"priority": None, "time_window": None}
    else:
        pr = random.randint(1, 3)
        start_t = random.randint(8, 12)
        end_t = start_t + random.randint(2, 4)
        time_priority_info[loc] = {"priority": pr, "time_window": (start_t, end_t)}

########################################
# 4) Build OSMnx Graph for Dubai
########################################
print("Downloading OSM data for 'Dubai, United Arab Emirates' (this may take time)...")
graph = ox.graph_from_place("Dubai, United Arab Emirates", network_type="drive")
print("OSMnx graph download completed.")

########################################
# 5) Fuel & Emission Calculation
########################################
def calculate_fuel_and_emissions(distance_km, fuel_efficiency=12.0, fuel_price=3.0, emission_factor=0.2):
    fuel_cost = (distance_km / fuel_efficiency) * fuel_price
    co2_emission = distance_km * emission_factor
    return fuel_cost, co2_emission

########################################
# 6) Update Graph with TomTom
########################################
def update_graph_with_tomtom(graph, speeds):
    from shapely.geometry import LineString
    for u, v, key, data in graph.edges(keys=True, data=True):
        if 'geometry' in data and isinstance(data['geometry'], LineString):
            lat, lon = data['geometry'].coords[0]
        else:
            lat, lon = None, None
        if (lat, lon) in speeds:
            try:
                speed_kmh = speeds[(lat, lon)]
                if speed_kmh > 0:
                    travel_time_hr = data["length"] / (speed_kmh * 1000/3600)
                    data["travel_time"] = travel_time_hr * 1.2
                else:
                    data["travel_time"] = float("inf")
            except:
                pass
    print("✅ Graph updated with TomTom speeds for edges.")
    return graph

########################################
# 7) Basic VRP Approach (Clustering + TSP)
########################################
drivers = [
    {"id": 1, "capacity": 2, "color": "red"},
    {"id": 2, "capacity": 2, "color": "blue"},
    {"id": 3, "capacity": 2, "color": "green"},
    {"id": 4, "capacity": 2, "color": "purple"},
    {"id": 5, "capacity": 2, "color": "orange"},
    {"id": 6, "capacity": 2, "color": "darkred"},
    {"id": 7, "capacity": 2, "color": "darkblue"},
    {"id": 8, "capacity": 2, "color": "darkgreen"},
    {"id": 9, "capacity": 2, "color": "cadetblue"},
    {"id": 10, "capacity": 2, "color": "black"},
]

def cluster_deliveries(indices, k=10):
    chunk_size = max(1, len(indices)//k)
    clusters = []
    current = []
    for idx in indices:
        current.append(idx)
        if len(current) >= chunk_size:
            clusters.append(current)
            current = []
    if current:
        clusters.append(current)
    while len(clusters) > k:
        clusters[-2].extend(clusters[-1])
        clusters.pop()
    return clusters

def run_cluster_tsp(graph, sub_idxs, node_map):
    """
    Build a cost matrix among sub_idxs and run TSP approximation.
    The cost includes time + partial fuel + partial CO2 + priority penalty.
    """
    cost = {}
    import math
    for i, j in itertools.permutations(sub_idxs, 2):
        try:
            base_time = nx.shortest_path_length(graph, node_map[i], node_map[j], weight="travel_time")
            dist_m = nx.shortest_path_length(graph, node_map[i], node_map[j], weight="length")
            dist_km = dist_m / 1000.0
            fuel_cost, co2_emission = calculate_fuel_and_emissions(dist_km)
            loc_j = all_locations[j]
            prj = time_priority_info[loc_j]["priority"]
            final_cost = base_time + fuel_cost + (co2_emission * 0.5)
            if prj is not None:
                final_cost += (prj - 1) * 5
            cost[(i, j)] = final_cost
        except:
            cost[(i, j)] = 999999

    subgraph = nx.complete_graph(len(sub_idxs))
    for (u, v) in subgraph.edges():
        real_u = sub_idxs[u]
        real_v = sub_idxs[v]
        subgraph[u][v]["weight"] = cost.get((real_u, real_v), math.inf)
        subgraph[v][u]["weight"] = cost.get((real_v, real_u), math.inf)

    route = approx.greedy_tsp(subgraph, weight="weight")
    if len(route) > 1:
        # close the route by returning to start
        route.append(route[0])
    global_route = [sub_idxs[n] for n in route]
    return global_route

def solve_vrp_clustering(graph, node_list):
    drop_indices = list(range(6, 26))
    clusters = cluster_deliveries(drop_indices, k=len(drivers))
    route_assignments = []
    fc_list = [2, 3, 4, 5]  # Indices for the 4 Fulfillment Centers
    for i, cluster in enumerate(clusters):
        fc_idx = fc_list[i % len(fc_list)]
        sub_idxs = [fc_idx] + cluster
        route = run_cluster_tsp(graph, sub_idxs, node_map=node_list)
        route_assignments.append({"driver": drivers[i], "route": route})
    return route_assignments

def count_signals(path_nodes, G):
    s = 0
    for n in path_nodes:
        if G.nodes[n].get("highway") == "traffic_signals":
            s += 1
    return s

########################################
# 8) Baseline Calculation Using FC's
########################################
def calculate_naive_baseline(geocoded, node_list, G):
    """
    For each delivery (indices 6..25), compute a round-trip from the nearest Fulfillment Center 
    (indices 2,3,4,5) instead of from Warehouse 1.
    """
    fc_indices = [2, 3, 4, 5]
    total_distance_km = 0.0
    total_fuel_cost = 0.0
    total_co2 = 0.0
    import networkx as nx

    for drop_idx in range(6, 26):
        best_roundtrip = None
        for fc_idx in fc_indices:
            try:
                out_path = nx.shortest_path(G, node_list[fc_idx], node_list[drop_idx], weight="length")
                ret_path = nx.shortest_path(G, node_list[drop_idx], node_list[fc_idx], weight="length")
                dist_m_out = sum(G.get_edge_data(out_path[i], out_path[i+1], 0).get("length", 0) for i in range(len(out_path)-1))
                dist_m_ret = sum(G.get_edge_data(ret_path[i], ret_path[i+1], 0).get("length", 0) for i in range(len(ret_path)-1))
                roundtrip_km = (dist_m_out + dist_m_ret) / 1000.0
                if best_roundtrip is None or roundtrip_km < best_roundtrip:
                    best_roundtrip = roundtrip_km
            except nx.NetworkXNoPath:
                continue
        if best_roundtrip is not None:
            total_distance_km += best_roundtrip
            f_cost, co2_e = calculate_fuel_and_emissions(best_roundtrip)
            total_fuel_cost += f_cost
            total_co2 += co2_e
    return total_distance_km, total_fuel_cost, total_co2

########################################
# 9) Additional function: get_deliveries_per_fc()
########################################
def get_deliveries_per_fc(route_assignments):
    """
    Returns a dict of how many deliveries each Fulfillment Center (FC) caters.
    FC indices: 2..5
    The route is something like [2, 10, 12, 2].
    The first index is the FC (2), the last might be the same (2).
    The deliveries are the middle indices (10,12).
    """
    fc_list = [2, 3, 4, 5]
    fc_deliveries_count = {fc_idx: 0 for fc_idx in fc_list}

    for rinfo in route_assignments:
        route = rinfo["route"]
        if not route:
            continue
        fc_idx = route[0]  # The first location in route is the FC
        if fc_idx in fc_deliveries_count:
            if len(route) > 1 and route[-1] == fc_idx:
                # skip final FC if it loops back
                deliveries = route[1:-1]
            else:
                deliveries = route[1:]
            fc_deliveries_count[fc_idx] += len(deliveries)
    
    return fc_deliveries_count

########################################
# 10) run_vrp() for direct usage
########################################
def run_vrp():
    # 1) Geocode
    geocoded = geocode_locations(all_locations)
    coords = [r for r in geocoded if r is not None]
    if not coords:
        print("No valid coordinates found!")
        return (0, 0, 0, 0, {})

    # 2) Fetch TomTom Speeds
    TOMTOM_API_KEY = "M4gbWbXRcVHKsmy42AesQzR2rlrUarfm"
    traffic_speeds = fetch_tomtom_traffic(coords, TOMTOM_API_KEY)

    # 3) Update Graph
    g_updated = update_graph_with_tomtom(graph, traffic_speeds)

    # 4) Map each location to nearest node
    valid_geocoded = [c for c in geocoded if c is not None]
    if not valid_geocoded:
        print("No valid geocoded locations found!")
        return (0, 0, 0, 0, {})

    import osmnx as ox
    node_list = ox.distance.nearest_nodes(
        g_updated,
        [c[1] for c in valid_geocoded],
        [c[0] for c in valid_geocoded]
    )

    # 5) Calculate baseline
    baseline_dist, baseline_fuel, baseline_co2 = calculate_naive_baseline(geocoded, node_list, g_updated)

    # 6) Solve VRP
    route_assignments = solve_vrp_clustering(g_updated, node_list)

    # 7) Build Folium Map
    m = folium.Map(tiles="CartoDB Positron", zoom_start=10)
    m.fit_bounds([(c[0], c[1]) for c in coords])

    markers_fg = folium.FeatureGroup("Markers").add_to(m)
    vrp_fg = folium.FeatureGroup("Multi-Driver VRP").add_to(m)

    def create_warehouse_divicon(wh_name):
        return DivIcon(
            icon_size=(50,50),
            icon_anchor=(25,50),
            html=f"""
            <div style="text-align:center;">
                <div style="font-size:24px;">🏭</div>
                <div style="font-size:12px; color:darkblue; margin-top:-3px;">
                    {wh_name}
                </div>
            </div>
            """
        )

    def create_fc_divicon(fc_label):
        return DivIcon(
            icon_size=(50,50),
            icon_anchor=(25,50),
            html=f"""
            <div style="text-align:center;">
                <div style="font-size:24px;">📦</div>
                <div style="font-size:12px; color:darkgreen; margin-top:-3px;">
                    {fc_label}
                </div>
            </div>
            """
        )

    def create_delivery_pin_icon():
        return DivIcon(
            icon_size=(24,24),
            icon_anchor=(12,24),
            html="""
            <div style="font-size:24px; text-align:center;">
                📍
            </div>
            """
        )

    fc_conn_text = {
        2: "Connected with: Fulfillment Center (FC2) & Fulfillment Center (FC4)",
        3: "Connected with: Fulfillment Center (FC1) & Fulfillment Center (FC3)",
        4: "Connected with: Fulfillment Center (FC2) & Fulfillment Center (FC4)",
        5: "Connected with: Fulfillment Center (FC3) & Fulfillment Center (FC1)"
    }

    # Marker loop
    delivery_counter = 1
    for idx, (loc, gc) in enumerate(zip(all_locations, geocoded)):
        if not gc:
            continue
        lat, lon = gc
        if idx < 2:
            wh_label = f"Warehouse {idx+1}"
            if idx == 0:
                catering = "Catering to: Fulfillment Center (FC1) & Fulfillment Center (FC2)"
            else:
                catering = "Catering to: Fulfillment Center (FC3) & Fulfillment Center (FC4)"
            popup_text = f"<b>{loc}</b><br/>Lat: {lat:.5f}, Lon: {lon:.5f}<br/>{catering}"
            folium.Marker(
                location=(lat, lon),
                tooltip=wh_label,
                popup=popup_text,
                icon=create_warehouse_divicon(wh_label)
            ).add_to(markers_fg)
        elif idx < 6:
            fc_num = idx - 1
            fc_label = f"Fulfillment Center (FC{fc_num})"
            conn_text = fc_conn_text.get(idx, "")
            popup_text = f"<b>{loc}</b><br/>Lat: {lat:.5f}, Lon: {lon:.5f}<br/>{conn_text}"
            folium.Marker(
                location=(lat, lon),
                tooltip=fc_label,
                popup=popup_text,
                icon=create_fc_divicon(fc_label)
            ).add_to(markers_fg)
        else:
            pr = time_priority_info[loc]["priority"]
            tooltip_text = f"Delivery Point {delivery_counter}"
            popup_text = (
                f"<b>{loc}</b><br/>Delivery Point {delivery_counter}"
                f"<br/>Lat: {lat:.5f}, Lon: {lon:.5f}"
                f"<br/>Priority: {pr if pr else 'N/A'}"
            )
            folium.Marker(
                location=(lat, lon),
                tooltip=tooltip_text,
                popup=popup_text,
                icon=create_delivery_pin_icon()
            ).add_to(markers_fg)
            delivery_counter += 1

    # FC-FC lines
    fc_pairs = [(2,3), (3,4), (4,5), (5,2)]
    for (f1, f2) in fc_pairs:
        latlon1 = geocoded[f1]
        latlon2 = geocoded[f2]
        if latlon1 and latlon2:
            folium.PolyLine(
                locations=[latlon1, latlon2],
                color="darkcyan",
                weight=3,
                dash_array="5,5",
                tooltip=f"FC-FC Link: {all_locations[f1]} ↔ {all_locations[f2]}"
            ).add_to(vrp_fg)

    # Warehouse-FC lines
    warehouse_fc_connections = [(0,2), (0,3), (1,4), (1,5)]
    for (wh_idx, fc_idx) in warehouse_fc_connections:
        latlon_wh = geocoded[wh_idx]
        latlon_fc = geocoded[fc_idx]
        if latlon_wh and latlon_fc:
            folium.PolyLine(
                locations=[latlon_wh, latlon_fc],
                color="teal",
                weight=3,
                dash_array="3,6",
                tooltip=f"{all_locations[wh_idx]} ↔ {all_locations[fc_idx]}"
            ).add_to(vrp_fg)

    # Global totals (full route including final leg)
    total_map_distance = 0.0
    total_map_fuel_cost = 0.0
    total_map_co2_emission = 0.0

    base_speed = 40.0
    total_delivery_time = 0.0
    total_delivery_count = 0

    # Process each driver's route
    for rinfo in route_assignments:
        driver = rinfo["driver"]
        route_indices = rinfo["route"]
        if len(route_indices) < 2:
            print(f"Driver {driver['id']}: route too short => {route_indices}")
            continue

        # Full-route distance/time for env metrics
        driver_dist_m_full = 0.0
        path_nodes_full = []
        for i in range(len(route_indices) - 1):
            s_i = route_indices[i]
            e_i = route_indices[i+1]
            if nx.has_path(g_updated, node_list[s_i], node_list[e_i]):
                sub_path = nx.shortest_path(g_updated, node_list[s_i], node_list[e_i], weight="length")
                for sp_i in range(len(sub_path) - 1):
                    edge_data = g_updated.get_edge_data(sub_path[sp_i], sub_path[sp_i+1], 0)
                    if edge_data:
                        driver_dist_m_full += edge_data.get("length", 0)
                path_nodes_full.extend(sub_path)

        driver_dist_km_full = driver_dist_m_full / 1000.0
        fuel_full, co2_full = calculate_fuel_and_emissions(driver_dist_km_full)
        sigs_full = count_signals(path_nodes_full, g_updated)
        base_time_min_full = (driver_dist_km_full / base_speed) * 60
        total_time_min_full = round(base_time_min_full + (sigs_full * 0.5), 2)

        total_map_distance += driver_dist_km_full
        total_map_fuel_cost += fuel_full
        total_map_co2_emission += co2_full

        # Average delivery time per delivery leg (excluding final leg)
        for i in range(len(route_indices) - 2):
            s_i = route_indices[i]
            e_i = route_indices[i+1]
            if nx.has_path(g_updated, node_list[s_i], node_list[e_i]):
                sub_path = nx.shortest_path(g_updated, node_list[s_i], node_list[e_i], weight="length")
                leg_dist_m = 0.0
                for sp_i in range(len(sub_path) - 1):
                    edge_data = g_updated.get_edge_data(sub_path[sp_i], sub_path[sp_i+1], 0)
                    if edge_data:
                        leg_dist_m += edge_data.get("length", 0)
                leg_dist_km = leg_dist_m / 1000.0
                leg_signals = count_signals(sub_path, g_updated)
                leg_time_min = (leg_dist_km / base_speed) * 60 + (leg_signals * 0.5)
                total_delivery_time += leg_time_min
                total_delivery_count += 1

        # Plot each leg
        print(f"Driver {driver['id']} => route_indices = {route_indices}")
        for i in range(len(route_indices) - 1):
            s_i = route_indices[i]
            e_i = route_indices[i+1]
            if i == (len(route_indices) - 2):
                leg_str = "Back to FC"
            else:
                leg_str = f"Leg {i+1}"

            leg_path_nodes = []
            leg_dist_m = 0.0
            if nx.has_path(g_updated, node_list[s_i], node_list[e_i]):
                sub_path = nx.shortest_path(g_updated, node_list[s_i], node_list[e_i], weight="length")
                for sp_i in range(len(sub_path) - 1):
                    edge_data = g_updated.get_edge_data(sub_path[sp_i], sub_path[sp_i+1], 0)
                    if edge_data:
                        leg_dist_m += edge_data.get("length", 0)
                leg_path_nodes = sub_path

            if not leg_path_nodes:
                continue

            coords_path = [(g_updated.nodes[n]["y"], g_updated.nodes[n]["x"]) for n in leg_path_nodes]
            if not coords_path:
                continue

            leg_dist_km = round(leg_dist_m / 1000.0, 2)
            leg_signals = count_signals(leg_path_nodes, g_updated)
            leg_time_min = round((leg_dist_km / base_speed) * 60 + (leg_signals * 0.5), 2)

            # Removed "Total Trip" from the tooltip
            leg_tooltip = (
                f"<b>Driver {driver['id']}, {leg_str}</b><br/>"
                f"Leg Distance: {leg_dist_km} km<br/>"
                f"Leg Time: {leg_time_min} min"
            )

            AntPath(
                locations=coords_path,
                dash_array=[10, 20],
                delay=600,
                color=driver["color"],
                weight=4,
                tooltip=leg_tooltip
            ).add_to(vrp_fg)

    folium.LayerControl().add_to(m)
    search = Search(
        layer=markers_fg,
        search_label='tooltip',
        placeholder='Search...',
        collapsed=False
    )
    search.add_to(m)

    # Save final map
    m.save("ExpandedDubai_VRP.html")
    print("✅ Final expanded VRP map => ExpandedDubai_VRP.html")

    # Compute overall average delivery time (excl final leg)
    if total_delivery_count > 0:
        avg_delivery_time_excl = round(total_delivery_time / total_delivery_count, 2)
    else:
        avg_delivery_time_excl = 0.0

    # New: get deliveries per FC
    fc_counts = get_deliveries_per_fc(route_assignments)

    return (
        round(total_map_distance, 2),
        round(total_map_co2_emission, 2),
        round(total_map_fuel_cost, 2),
        avg_delivery_time_excl,
        fc_counts
    )

if __name__ == "__main__":
    run_vrp()
