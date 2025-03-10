# Last-Mile-Delivery-Optimization
		A case study: Last-Mile Delivery Optimization in Dubai

1. The Problem
•	Rapid E-Commerce Growth & Delivery Challenges
•	Dubai’s booming e-commerce market has created a need for swift, reliable delivery 	services. Fulfilment centres (FCs) and warehouses often have to dispatch orders to 	numerous drop-off points, all while contending with heavy traffic at different times 	of the day.

•	Key Pain Points
•	Unpredictable Traffic Delays: Rush hours or accident-prone roads can significantly delay shipments.
•	Rising Operational Costs: Longer routes mean higher fuel usage and increased CO₂ emissions.
•	Multiple Fulfilment Centres & Drivers: Coordinating which driver handles which deliveries, and balancing workload, can be difficult.

•	Why Address It?
•	Customer Expectations are skyrocketing, with many wanting same-day or next-day delivery.
•	Cost Efficiency is vital for competitive pricing.
•	Environmental Responsibility is increasingly important, prompting businesses to 	reduce their carbon footprint.

2. Rationale & Goals
•	What Needed to Be Solved
•	Inefficient Routes leading to wasted time and higher costs.
•	Driver Overload when one FC or driver is assigned too many deliveries.
•	Static Routing ignoring real-time changes in road conditions.

•	Core Objectives
•	Minimize Delivery Times & Distances: Shorter routes benefit both cost and customer 	satisfaction.
•	Balance Workload: Ensure no single driver or FC is overloaded.
•	Incorporate Real-Time Traffic: Adjust speeds to reflect TomTom live data, reducing 	traffic-related delays.
•	Provide an Easy Visualization: A Streamlit dashboard to show routes, metrics, and key insights in a user-friendly manner.

3. Approach & Methodology
•	The Strategy

1.	Data Acquisition:
•	Geocode addresses for warehouses, FCs, and delivery points.
•	Retrieve live traffic speeds from TomTom’s API for each coordinate.  

2.	Algorithmic Core:
•	A Vehicle Routing Problem (VRP) approach to allocate deliveries to multiple drivers.
•	Within each driver’s set, a TSP (Traveling Salesman Problem) solver finds a near-optimal route sequence.
•	We use clustering so that deliveries are grouped logically, avoiding a single huge TSP problem.

3.	Real-Time Graph Update:
•	With OSMnx and NetworkX, each road segment is assigned a dynamic “travel_time” based on TomTom speeds, making the routing realistic for current conditions.

4.	Performance Tracking:
•	Calculate fuel cost, CO₂ emissions, and overall delivery time.
•	Compare optimized routes vs. a naive baseline to measure improvements.

5.	Why VRP + TSP?
•	VRP handles multiple drivers and capacity constraints.
•	TSP sequences delivery stops effectively once we know which driver is handling 			which deliveries.
•	Real-time traffic updates improve on typical static VRP solutions.
4. Implementation Details
1.	Key Components
•	AdvancedVRP.py:
	Geocoding and traffic fetching from TomTom.
	solve_vrp_clustering(): Divides deliveries among drivers via clustering.
	run_cluster_tsp(): Approximates TSP for each cluster.
	run_vrp(): Orchestrates everything, builds a Folium map showing routes, and returns key metrics.
	
2.	ProjectDashboard.py:
•	Streamlit app that calls run_vrp().
•	Displays the map (ExpandedDubai_VRP.html), an interactive legend, and top-level KPI metrics.
•	Sidebar charts (Altair) for driver distance, delivery times, and a pie chart for FC utilization.
•	Collapsible “Key Insights” sections explaining real-time traffic benefits, environmental impact, workload balancing, and delivery efficiency.

The Dashboard Layout
	Top: Title and short overview.
	Center: Map with color-coded routes, each driver in a distinct color. Hover tooltips for “Leg Distance” & “Leg Time.”
	Right: A “Map Overview” box showing average time & disclaimers, plus a “Legend” box describing icons and route colors.
	Below Map: KPI metrics (distance, average time, CO₂ saved, fuel cost).
	Left Sidebar:
•	Driver charts (distance/time).
•	Fulfillment center pie chart.
•	Collapsible expansions for Key Insights.

5. Conclusion: How the Problem Was Solved
By combining real-time traffic data with an efficient VRP + TSP approach, the system:
	Minimizes Road Time: Shortens routes and finds better paths even in heavy traffic.
	Reduces Fuel & Emissions: Fewer kilometres travelled means direct savings and eco-friendly operations.
	Balances Driver Workload: Clustering ensures no single driver is overloaded while others remain underutilized.
	Provides Actionable Insights: A Streamlit dashboard highlights performance metrics, driver times, and FC workloads in an intuitive format.
Final Takeaways:
	Real-time data significantly improves last-mile logistics, saving both time and cost.
	The dashboard approach ensures clarity for managers or dispatchers to track routes and performance.
	The solution is scalable and can adapt to more locations, more drivers, or different traffic APIs if needed.
	This project showcases a holistic approach to last-mile delivery optimization, from problem definition to a visually appealing, data-driven result.
