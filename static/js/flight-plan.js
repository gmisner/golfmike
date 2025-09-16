/**
 * Flight Plan Lookup - JavaScript functionality
 */

class FlightPlanLookup {
    constructor() {
        this.map = null;
        this.currentFlightPlan = null;
        this.waypointMarkers = [];
        this.routePolyline = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeMap();
    }

    setupEventListeners() {
        console.log('Setting up event listeners...');
        
        // Search functionality
        const searchBtn = document.getElementById('searchBtn');
        const searchInput = document.getElementById('searchInput');
        const backBtn = document.getElementById('backToSearch');
        
        console.log('Elements found:', { searchBtn, searchInput, backBtn });
        
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                console.log('Search button clicked');
                this.searchFlights();
            });
        } else {
            console.error('Search button not found!');
        }

        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    console.log('Enter key pressed');
                    this.searchFlights();
                }
            });
        } else {
            console.error('Search input not found!');
        }

        // Back to search
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                this.showSearchResults();
            });
        } else {
            console.error('Back button not found!');
        }
    }

    initializeMap() {
        try {
            console.log('Initializing map...');
            // Initialize the map for flight plan visualization
            this.map = L.map('flightPlanMap').setView([39.8283, -98.5795], 4);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(this.map);
            console.log('Map initialized successfully');
        } catch (error) {
            console.error('Error initializing map:', error);
        }
    }

    async searchFlights() {
        console.log('Search function called');
        const query = document.getElementById('searchInput').value.trim();
        console.log('Search query:', query);
        
        if (!query) {
            alert('Please enter a search term');
            return;
        }

        try {
            console.log('Making API request...');
            const response = await fetch(`/api/flights/search?q=${encodeURIComponent(query)}`);
            console.log('Response status:', response.status);
            
            const data = await response.json();
            console.log('Response data:', data);

            if (data.error) {
                alert('Error: ' + data.error);
                return;
            }

            this.displaySearchResults(data);
        } catch (error) {
            console.error('Search error:', error);
            alert('Error searching flights: ' + error.message);
        }
    }

    displaySearchResults(data) {
        const resultsContainer = document.getElementById('searchResultsList');
        const searchResults = document.getElementById('searchResults');
        
        if (data.flights.length === 0) {
            resultsContainer.innerHTML = '<div class="alert alert-warning">No flights found matching your search.</div>';
        } else {
            let html = `<div class="alert alert-info">Found ${data.count} flights matching "${data.query}"</div>`;
            
            data.flights.forEach(flight => {
                const positionInfo = flight.position ? 
                    `📍 ${flight.position.latitude.toFixed(4)}, ${flight.position.longitude.toFixed(4)}` : 
                    '📍 Position unknown';
                
                html += `
                    <div class="card mb-3">
                        <div class="card-body">
                            <div class="row align-items-center">
                                <div class="col-md-3">
                                    <h4 class="mb-1">${flight.aircraft_id}</h4>
                                    <div class="text-muted small">${flight.gufi}</div>
                                </div>
                                <div class="col-md-3">
                                    <div class="text-muted small">Route</div>
                                    <div>${flight.departure_airport} → ${flight.arrival_airport}</div>
                                </div>
                                <div class="col-md-3">
                                    <div class="text-muted small">Position</div>
                                    <div class="small">${positionInfo}</div>
                                </div>
                                <div class="col-md-3">
                                    <button class="btn btn-primary btn-sm" onclick="flightPlanLookup.viewFlightPlan('${flight.aircraft_id}')">
                                        View Flight Plan
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            resultsContainer.innerHTML = html;
        }
        
        searchResults.style.display = 'block';
        document.getElementById('flightPlanDetails').style.display = 'none';
    }

    async viewFlightPlan(aircraftId) {
        try {
            const response = await fetch(`/api/flights/${aircraftId}/flightplan`);
            const flightPlan = await response.json();

            if (flightPlan.error) {
                alert('Error: ' + flightPlan.error);
                return;
            }

            this.currentFlightPlan = flightPlan;
            this.displayFlightPlan(flightPlan);
        } catch (error) {
            console.error('Error fetching flight plan:', error);
            alert('Error loading flight plan');
        }
    }

    displayFlightPlan(flightPlan) {
        // Update flight information
        document.getElementById('aircraftId').textContent = flightPlan.aircraft_id;
        document.getElementById('gufi').textContent = flightPlan.gufi;
        document.getElementById('departure').textContent = flightPlan.departure_airport;
        document.getElementById('arrival').textContent = flightPlan.arrival_airport;
        document.getElementById('scheduledDeparture').textContent = 
            flightPlan.scheduled_departure ? new Date(flightPlan.scheduled_departure).toLocaleString() : 'N/A';
        document.getElementById('waypointCount').textContent = flightPlan.waypoint_count;
        document.getElementById('fixCount').textContent = flightPlan.fix_count;
        document.getElementById('routeText').textContent = flightPlan.route_text || 'N/A';

        // Update title
        document.getElementById('flightPlanTitle').textContent = 
            `Flight Plan: ${flightPlan.aircraft_id} (${flightPlan.departure_airport} → ${flightPlan.arrival_airport})`;

        // Display waypoints
        this.displayWaypoints(flightPlan.waypoints);

        // Display fixes
        this.displayFixes(flightPlan.fixes);

        // Display route of flight
        document.getElementById('routeOfFlight').textContent = flightPlan.route_of_flight || 'N/A';

        // Update map
        this.updateMap(flightPlan);

        // Show flight plan details
        document.getElementById('searchResults').style.display = 'none';
        document.getElementById('flightPlanDetails').style.display = 'block';
    }

    displayWaypoints(waypoints) {
        const waypointsList = document.getElementById('waypointsList');
        
        if (!waypoints || waypoints.length === 0) {
            waypointsList.innerHTML = '<div class="text-muted">No waypoints available</div>';
            return;
        }

        let html = '';
        waypoints.forEach((waypoint, index) => {
            const elapsedTime = waypoint.elapsed_time ? 
                `${Math.floor(waypoint.elapsed_time / 60)}:${(waypoint.elapsed_time % 60).toString().padStart(2, '0')}` : 
                'N/A';
            
            html += `
                <div class="mb-2 p-2 border rounded">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>WP ${index + 1}</strong>
                        </div>
                        <div class="text-muted small">
                            ${elapsedTime}
                        </div>
                    </div>
                    <div class="small text-muted">
                        ${waypoint.latitude}, ${waypoint.longitude}
                    </div>
                </div>
            `;
        });
        
        waypointsList.innerHTML = html;
    }

    displayFixes(fixes) {
        const fixesList = document.getElementById('fixesList');
        
        if (!fixes || fixes.length === 0) {
            fixesList.innerHTML = '<div class="text-muted">No fixes available</div>';
            return;
        }

        let html = '<div class="d-flex flex-wrap gap-1">';
        fixes.forEach(fix => {
            html += `<span class="badge bg-blue-lt">${fix}</span>`;
        });
        html += '</div>';
        
        fixesList.innerHTML = html;
    }

    updateMap(flightPlan) {
        // Clear existing markers and polylines
        this.waypointMarkers.forEach(marker => this.map.removeLayer(marker));
        this.waypointMarkers = [];
        
        if (this.routePolyline) {
            this.map.removeLayer(this.routePolyline);
        }

        if (!flightPlan.waypoints || flightPlan.waypoints.length === 0) {
            return;
        }

        // Create waypoint markers and route polyline
        const waypointCoords = [];
        
        flightPlan.waypoints.forEach((waypoint, index) => {
            const lat = parseFloat(waypoint.latitude);
            const lng = parseFloat(waypoint.longitude);
            
            if (!isNaN(lat) && !isNaN(lng)) {
                waypointCoords.push([lat, lng]);
                
                // Create marker
                const marker = L.circleMarker([lat, lng], {
                    radius: 6,
                    fillColor: index === 0 ? '#2fb344' : '#206bc4', // Green for start, blue for others
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                }).addTo(this.map);
                
                // Add popup
                const elapsedTime = waypoint.elapsed_time ? 
                    `${Math.floor(waypoint.elapsed_time / 60)}:${(waypoint.elapsed_time % 60).toString().padStart(2, '0')}` : 
                    'N/A';
                
                marker.bindPopup(`
                    <div>
                        <strong>Waypoint ${index + 1}</strong><br>
                        <strong>Position:</strong> ${lat.toFixed(4)}, ${lng.toFixed(4)}<br>
                        <strong>Elapsed Time:</strong> ${elapsedTime}
                    </div>
                `);
                
                this.waypointMarkers.push(marker);
            }
        });

        // Create route polyline
        if (waypointCoords.length > 1) {
            this.routePolyline = L.polyline(waypointCoords, {
                color: '#206bc4',
                weight: 3,
                opacity: 0.7,
                dashArray: '10, 10'
            }).addTo(this.map);
        }

        // Add departure and arrival markers
        if (waypointCoords.length > 0) {
            // Departure marker (first waypoint)
            const departureMarker = L.marker(waypointCoords[0], {
                icon: L.divIcon({
                    className: 'departure-marker',
                    html: '<div style="background: #2fb344; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
                    iconSize: [26, 26],
                    iconAnchor: [13, 13]
                })
            }).addTo(this.map);
            
            departureMarker.bindPopup(`
                <div>
                    <strong>Departure</strong><br>
                    <strong>Aircraft:</strong> ${flightPlan.aircraft_id}<br>
                    <strong>From:</strong> ${flightPlan.departure_airport}
                </div>
            `);
            
            this.waypointMarkers.push(departureMarker);

            // Arrival marker (last waypoint)
            if (waypointCoords.length > 1) {
                const arrivalMarker = L.marker(waypointCoords[waypointCoords.length - 1], {
                    icon: L.divIcon({
                        className: 'arrival-marker',
                        html: '<div style="background: #d63384; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
                        iconSize: [26, 26],
                        iconAnchor: [13, 13]
                    })
                }).addTo(this.map);
                
                arrivalMarker.bindPopup(`
                    <div>
                        <strong>Arrival</strong><br>
                        <strong>Aircraft:</strong> ${flightPlan.aircraft_id}<br>
                        <strong>To:</strong> ${flightPlan.arrival_airport}
                    </div>
                `);
                
                this.waypointMarkers.push(arrivalMarker);
            }
        }

        // Fit map to show all waypoints
        if (waypointCoords.length > 0) {
            const group = new L.featureGroup(this.waypointMarkers);
            this.map.fitBounds(group.getBounds().pad(0.1));
        }
    }

    showSearchResults() {
        document.getElementById('flightPlanDetails').style.display = 'none';
        document.getElementById('searchResults').style.display = 'block';
    }
}

// Initialize the flight plan lookup when the page loads
let flightPlanLookup;
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing FlightPlanLookup...');
    try {
        flightPlanLookup = new FlightPlanLookup();
        console.log('FlightPlanLookup initialized successfully');
    } catch (error) {
        console.error('Error initializing FlightPlanLookup:', error);
    }
});
