/**
 * GolfMike Flight Tracker - Real-time flight tracking interface
 */

class FlightTracker {
    constructor() {
        this.map = null;
        this.flightMarkers = new Map();
        this.flightTrails = new Map(); // Store flight trails for animation
        this.refreshInterval = null;
        this.animationInterval = null;
        this.lastUpdate = null;
        this.apiBase = '/api/flights';
        this.isAnimating = false;
        this.animationSpeed = 1000; // Animation speed in ms
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeMap();
        this.startAutoRefresh();
        this.loadInitialData();
    }

    setupEventListeners() {
        // Refresh button
        document.querySelector('[onclick="refreshData()"]')?.addEventListener('click', () => {
            this.refreshData();
        });

        // Search input - handle Enter key
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.searchFlights();
                }
            });
        }

        // Tab changes
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                if (e.target.getAttribute('href') === '#tab-map') {
                    setTimeout(() => this.map?.invalidateSize(), 100);
                }
            });
        });
    }

    initializeMap() {
        // Initialize Leaflet map
        this.map = L.map('flight-map').setView([39.8283, -98.5795], 4); // Center on US
        
        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);

        // Add aircraft icon
        this.aircraftIcon = L.divIcon({
            className: 'aircraft-marker',
            html: '<div style="background: #206bc4; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });
    }

    async loadInitialData() {
        try {
            await Promise.all([
                this.loadActiveFlights(),
                this.loadNotifications(),
                this.updateStats()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load flight data');
        }
    }

    async loadActiveFlights() {
        try {
            const response = await fetch(`${this.apiBase}/current`);
            const data = await response.json();
            
            if (data.flights) {
                this.currentFlights = data.flights; // Store for search functionality
                this.renderFlights(data.flights);
                this.updateMap(data.flights);
                this.updateLastUpdate();
            }
        } catch (error) {
            console.error('Error loading active flights:', error);
        }
    }

    async loadNotifications() {
        try {
            const response = await fetch(`${this.apiBase}/notifications?hours=1`);
            const data = await response.json();
            
            if (data.notifications) {
                this.renderNotifications(data.notifications);
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    async updateStats() {
        try {
            const [flightsResponse, notificationsResponse] = await Promise.all([
                fetch(`${this.apiBase}/current`),
                fetch(`${this.apiBase}/notifications?hours=1`)
            ]);

            const flightsData = await flightsResponse.json();
            const notificationsData = await notificationsResponse.json();

            // Update stats
            document.getElementById('active-flights-count').textContent = flightsData.count || 0;
            
            const takeoffs = notificationsData.notifications?.filter(n => n.event_type === 'DEPARTED').length || 0;
            const landings = notificationsData.notifications?.filter(n => n.event_type === 'ARRIVED').length || 0;
            
            document.getElementById('takeoffs-count').textContent = takeoffs;
            document.getElementById('landings-count').textContent = landings;
            
        } catch (error) {
            console.error('Error updating stats:', error);
        }
    }

    renderFlights(flights) {
        const container = document.getElementById('flights-container');
        
        if (!flights || flights.length === 0) {
            container.innerHTML = `
                <div class="col-12">
                    <div class="empty">
                        <div class="empty-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                                <path d="M12 2l3.09 6.26l6.91 1.01l-5 4.87l1.18 6.88l-6.18 -3.25l-6.18 3.25l1.18 -6.88l-5 -4.87l6.91 -1.01z"/>
                            </svg>
                        </div>
                        <p class="empty-title">No active flights</p>
                        <p class="empty-subtitle text-muted">No flights are currently being tracked.</p>
                    </div>
                </div>
            `;
            return;
        }

        container.innerHTML = flights.map(flight => this.createFlightCard(flight)).join('');
    }

    createFlightCard(flight) {
        const statusClass = this.getStatusClass(flight.current_status);
        const statusText = this.getStatusText(flight.current_status);
        const aircraftCode = flight.aircraft_id?.substring(0, 3) || 'N/A';
        const hasPosition = flight.position && flight.position.latitude && flight.position.longitude;
        const cardClass = hasPosition ? 'flight-card has-position' : 'flight-card';
        const statusBadgeClass = flight.current_status === 'IN_FLIGHT' ? 'status-badge in-flight' : `status-badge ${statusClass}`;
        
        return `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card ${cardClass}" onclick="tracker.showFlightDetails('${flight.aircraft_id}')">
                    <div class="card-body">
                        <div class="row align-items-center">
                            <div class="col-auto">
                                <div class="aircraft-avatar">
                                    ${aircraftCode}
                                </div>
                            </div>
                            <div class="col">
                                <div class="font-weight-medium">${flight.aircraft_id || 'Unknown'}</div>
                                <div class="text-muted">${flight.departure_airport || 'N/A'} → ${flight.arrival_airport || 'N/A'}</div>
                            </div>
                            <div class="col-auto">
                                <span class="badge ${statusBadgeClass}">${statusText}</span>
                            </div>
                        </div>
                        ${hasPosition ? `
                            <div class="position-data">
                                <div class="position-item">
                                    <small class="text-muted">Position</small>
                                    <small class="font-weight-medium">
                                        ${flight.position.latitude.toFixed(4)}, ${flight.position.longitude.toFixed(4)}
                                    </small>
                                </div>
                                <div class="position-item">
                                    <small class="text-muted">Altitude</small>
                                    <small class="font-weight-medium">
                                        ${flight.position.altitude ? flight.position.altitude + ' ft' : 'N/A'}
                                    </small>
                                </div>
                                <div class="position-item">
                                    <small class="text-muted">Speed</small>
                                    <small class="font-weight-medium">
                                        ${flight.position.speed ? flight.position.speed + ' kts' : 'N/A'}
                                    </small>
                                </div>
                                <div class="position-item">
                                    <small class="text-muted">Last Update</small>
                                    <small class="font-weight-medium">
                                        ${flight.position.timestamp ? new Date(flight.position.timestamp).toLocaleTimeString() : 'N/A'}
                                    </small>
                                </div>
                            </div>
                        ` : ''}
                        <div class="mt-2">
                            <small class="text-muted">
                                <i class="icon icon-clock"></i>
                                Scheduled: ${flight.scheduled_departure ? new Date(flight.scheduled_departure).toLocaleString() : 'N/A'}
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderNotifications(notifications) {
        const container = document.getElementById('notifications-container');
        
        if (!notifications || notifications.length === 0) {
            container.innerHTML = `
                <div class="empty">
                    <div class="empty-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                            <path d="M10 5a2 2 0 0 1 4 0a7 7 0 0 1 4 6v3a4 4 0 0 0 2 3h-16a4 4 0 0 0 2 -3v-3a7 7 0 0 1 4 -6"/>
                            <path d="M9 17v1a3 3 0 0 0 6 0v-1"/>
                        </svg>
                    </div>
                    <p class="empty-title">No recent notifications</p>
                    <p class="empty-subtitle text-muted">No flight events in the last hour.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = notifications.map(notification => this.createNotificationItem(notification)).join('');
    }

    createNotificationItem(notification) {
        const eventClass = notification.event_type.toLowerCase();
        const eventIcon = this.getEventIcon(notification.event_type);
        const timeAgo = this.getTimeAgo(notification.timestamp);
        
        return `
            <div class="notification-item ${eventClass} mb-3 p-3 bg-dark-lt">
                <div class="row align-items-center">
                    <div class="col-auto">
                        <span class="avatar avatar-sm bg-primary-lt">
                            ${eventIcon}
                        </span>
                    </div>
                    <div class="col">
                        <div class="font-weight-medium">${notification.aircraft_id}</div>
                        <div class="text-muted">${this.getEventText(notification.event_type)}</div>
                    </div>
                    <div class="col-auto">
                        <div class="text-muted small">${timeAgo}</div>
                    </div>
                </div>
            </div>
        `;
    }

    updateMap(flights) {
        if (!this.map) return;

        // Store previous positions for animation
        const previousPositions = new Map();
        this.flightMarkers.forEach((marker, aircraftId) => {
            const latLng = marker.getLatLng();
            previousPositions.set(aircraftId, { lat: latLng.lat, lng: latLng.lng });
        });

        // Clear existing markers
        this.flightMarkers.forEach(marker => this.map.removeLayer(marker));
        this.flightMarkers.clear();

        // Add new markers with smooth animation
        flights.forEach(flight => {
            if (flight.position && flight.position.latitude && flight.position.longitude) {
                const newPosition = [flight.position.latitude, flight.position.longitude];
                const previousPosition = previousPositions.get(flight.aircraft_id);
                
                // Create custom icon based on flight status
                const statusColor = this.getStatusColor(flight.current_status);
                const customIcon = L.divIcon({
                    className: 'aircraft-marker',
                    html: `<div style="background: ${statusColor}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
                    iconSize: [16, 16],
                    iconAnchor: [8, 8]
                });

                const marker = L.marker(newPosition, {
                    icon: customIcon
                }).addTo(this.map);

                // Add smooth animation if previous position exists
                if (previousPosition) {
                    this.animateMarker(marker, previousPosition, newPosition, flight);
                }

                // Add popup with enhanced information
                const popupContent = `
                    <div class="p-2">
                        <div class="font-weight-bold">${flight.aircraft_id}</div>
                        <div class="text-muted">${flight.departure_airport} → ${flight.arrival_airport}</div>
                        <div class="small mt-2">
                            <div><strong>Status:</strong> ${this.getStatusText(flight.current_status)}</div>
                            <div><strong>Altitude:</strong> ${flight.position.altitude ? flight.position.altitude + ' ft' : 'N/A'}</div>
                            <div><strong>Speed:</strong> ${flight.position.speed ? flight.position.speed + ' kts' : 'N/A'}</div>
                            <div><strong>Position:</strong> ${flight.position.latitude.toFixed(4)}, ${flight.position.longitude.toFixed(4)}</div>
                            <div><strong>Last Update:</strong> ${flight.position.timestamp ? new Date(flight.position.timestamp).toLocaleTimeString() : 'N/A'}</div>
                        </div>
                        <div class="mt-2">
                            <button class="btn btn-sm btn-primary" onclick="tracker.showFlightDetails('${flight.aircraft_id}')">
                                View Details
                            </button>
                        </div>
                    </div>
                `;
                marker.bindPopup(popupContent);

                this.flightMarkers.set(flight.aircraft_id, marker);
            }
        });

        // Update flight trails
        this.updateFlightTrails(flights);

        // Fit map to show all markers (only if not animating)
        if (this.flightMarkers.size > 0 && !this.isAnimating) {
            const group = new L.featureGroup(Array.from(this.flightMarkers.values()));
            this.map.fitBounds(group.getBounds().pad(0.1));
        }
    }

    getStatusClass(status) {
        const statusMap = {
            'PLANNED': 'bg-blue-lt',
            'DEPARTED': 'bg-green-lt',
            'IN_FLIGHT': 'bg-yellow-lt',
            'ARRIVED': 'bg-red-lt',
            'DIVERTED': 'bg-orange-lt',
            'CANCELLED': 'bg-gray-lt'
        };
        return statusMap[status] || 'bg-gray-lt';
    }

    getStatusText(status) {
        const statusMap = {
            'PLANNED': 'Planned',
            'DEPARTED': 'Departed',
            'IN_FLIGHT': 'In Flight',
            'ARRIVED': 'Arrived',
            'DIVERTED': 'Diverted',
            'CANCELLED': 'Cancelled'
        };
        return statusMap[status] || 'Unknown';
    }

    getStatusColor(status) {
        const colorMap = {
            'PLANNED': '#206bc4',
            'DEPARTED': '#2fb344',
            'IN_FLIGHT': '#f76707',
            'ARRIVED': '#e03131',
            'DIVERTED': '#fd7e14',
            'CANCELLED': '#6c757d'
        };
        return colorMap[status] || '#6c757d';
    }

    getEventIcon(eventType) {
        const iconMap = {
            'DEPARTED': '✈️',
            'ARRIVED': '🛬',
            'DIVERTED': '🔄',
            'CANCELLED': '❌'
        };
        return iconMap[eventType] || '📢';
    }

    getEventText(eventType) {
        const textMap = {
            'DEPARTED': 'Flight departed',
            'ARRIVED': 'Flight arrived',
            'DIVERTED': 'Flight diverted',
            'CANCELLED': 'Flight cancelled'
        };
        return textMap[eventType] || 'Flight event';
    }

    getTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d ago`;
    }

    updateLastUpdate() {
        this.lastUpdate = new Date();
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = this.lastUpdate.toLocaleTimeString();
        }
        
        // Update status indicator
        const statusElement = document.getElementById('update-status');
        if (statusElement) {
            statusElement.textContent = `Live tracking active (${this.flightMarkers.size} aircraft)`;
        }
    }

    startAutoRefresh() {
        // Refresh every 10 seconds for more dynamic updates (like FlightAware)
        this.refreshInterval = setInterval(() => {
            this.loadInitialData();
        }, 10000);
        
        // Add continuous position updates for smoother animation
        this.startPositionUpdates();
    }

    startPositionUpdates() {
        // Update positions every 2 seconds for smoother animation
        this.positionUpdateInterval = setInterval(() => {
            this.updateAircraftPositions();
        }, 2000);
    }

    async updateAircraftPositions() {
        try {
            // Get current flights and update positions smoothly
            const response = await fetch(`${this.apiBase}/current`);
            const data = await response.json();
            
            if (data.flights) {
                this.updateMapPositions(data.flights);
                this.updateLastUpdate();
            }
        } catch (error) {
            console.error('Error updating positions:', error);
            // Update status to show error
            const statusElement = document.getElementById('update-status');
            if (statusElement) {
                statusElement.textContent = 'Connection error - retrying...';
                statusElement.className = 'text-warning';
            }
        }
    }

    updateMapPositions(flights) {
        if (!this.map) return;

        flights.forEach(flight => {
            if (flight.position && flight.position.latitude && flight.position.longitude) {
                const marker = this.flightMarkers.get(flight.aircraft_id);
                if (marker) {
                    const currentPos = marker.getLatLng();
                    const newPos = [flight.position.latitude, flight.position.longitude];
                    
                    // Only animate if position has changed significantly
                    const distance = this.calculateDistance(
                        currentPos.lat, currentPos.lng,
                        newPos[0], newPos[1]
                    );
                    
                    if (distance > 0.001) { // ~100 meters
                        this.animateMarker(marker, currentPos, newPos, flight);
                    }
                }
            }
        });
    }

    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Earth's radius in km
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    refreshData() {
        this.loadInitialData();
    }

    // Cleanup method to stop all intervals
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.positionUpdateInterval) {
            clearInterval(this.positionUpdateInterval);
        }
        if (this.animationInterval) {
            clearInterval(this.animationInterval);
        }
    }

    searchFlights() {
        const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
        
        if (!searchTerm) {
            this.loadInitialData();
            return;
        }

        // Check if search term matches a specific aircraft ID exactly
        const allFlights = this.currentFlights || [];
        const exactMatch = allFlights.find(flight => 
            flight.aircraft_id.toLowerCase() === searchTerm
        );

        if (exactMatch) {
            // If exact match found, redirect to flight detail page
            this.showFlightDetails(exactMatch.aircraft_id);
            return;
        }

        // Otherwise, filter flights based on search term
        const filteredFlights = allFlights.filter(flight => 
            flight.aircraft_id.toLowerCase().includes(searchTerm) ||
            flight.departure_airport.toLowerCase().includes(searchTerm) ||
            flight.arrival_airport.toLowerCase().includes(searchTerm) ||
            (flight.gufi && flight.gufi.toLowerCase().includes(searchTerm))
        );

        this.renderFlights(filteredFlights);
        this.updateMap(filteredFlights);
    }

    clearSearch() {
        document.getElementById('searchInput').value = '';
        this.loadInitialData();
    }

    showFlightDetails(aircraftId) {
        // Redirect to the flight detail page
        window.location.href = `/flight-detail.html?aircraft=${aircraftId}`;
    }

    createFlightDetailsModal(aircraftId, positionData, trackData) {
        // Remove existing modal if any
        const existingModal = document.getElementById('flightDetailsModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Create modal HTML
        const modalHTML = `
            <div class="modal fade" id="flightDetailsModal" tabindex="-1" aria-labelledby="flightDetailsModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="flightDetailsModalLabel">Flight Details - ${aircraftId}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>Current Position</h6>
                                    <div class="card">
                                        <div class="card-body">
                                            ${positionData.error ? 
                                                '<p class="text-muted">No position data available</p>' :
                                                `
                                                <div class="row">
                                                    <div class="col-6"><strong>Latitude:</strong></div>
                                                    <div class="col-6">${positionData.latitude?.toFixed(6) || 'N/A'}</div>
                                                </div>
                                                <div class="row">
                                                    <div class="col-6"><strong>Longitude:</strong></div>
                                                    <div class="col-6">${positionData.longitude?.toFixed(6) || 'N/A'}</div>
                                                </div>
                                                <div class="row">
                                                    <div class="col-6"><strong>Altitude:</strong></div>
                                                    <div class="col-6">${positionData.altitude ? positionData.altitude + ' ft' : 'N/A'}</div>
                                                </div>
                                                <div class="row">
                                                    <div class="col-6"><strong>Speed:</strong></div>
                                                    <div class="col-6">${positionData.speed ? positionData.speed + ' kts' : 'N/A'}</div>
                                                </div>
                                                <div class="row">
                                                    <div class="col-6"><strong>Last Update:</strong></div>
                                                    <div class="col-6">${positionData.timestamp ? new Date(positionData.timestamp).toLocaleString() : 'N/A'}</div>
                                                </div>
                                                `
                                            }
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <h6>Track History</h6>
                                    <div class="card">
                                        <div class="card-body" style="max-height: 300px; overflow-y: auto;">
                                            ${trackData.tracks && trackData.tracks.length > 0 ?
                                                trackData.tracks.slice(0, 10).map(track => `
                                                    <div class="border-bottom pb-2 mb-2">
                                                        <div class="small">
                                                            <strong>${new Date(track.timestamp).toLocaleTimeString()}</strong>
                                                        </div>
                                                        <div class="small text-muted">
                                                            ${track.latitude?.toFixed(4)}, ${track.longitude?.toFixed(4)} | 
                                                            ${track.altitude ? track.altitude + ' ft' : 'N/A'} | 
                                                            ${track.speed ? track.speed + ' kts' : 'N/A'}
                                                        </div>
                                                    </div>
                                                `).join('') :
                                                '<p class="text-muted">No track history available</p>'
                                            }
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="row mt-3">
                                <div class="col-12">
                                    <h6>Track Map</h6>
                                    <div id="trackMap" style="height: 300px; border-radius: 8px;"></div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" onclick="tracker.centerOnAircraft('${aircraftId}')">
                                Center on Map
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('flightDetailsModal'));
        modal.show();

        // Initialize track map
        this.initializeTrackMap(trackData.tracks || []);
    }

    initializeTrackMap(tracks) {
        if (!tracks || tracks.length === 0) return;

        // Create map for track history
        const trackMap = L.map('trackMap').setView([tracks[0].latitude, tracks[0].longitude], 8);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(trackMap);

        // Add track line
        const trackLine = tracks.map(track => [track.latitude, track.longitude]);
        L.polyline(trackLine, {color: '#206bc4', weight: 3}).addTo(trackMap);

        // Add start and end markers
        if (tracks.length > 0) {
            L.marker([tracks[0].latitude, tracks[0].longitude], {
                icon: L.divIcon({
                    className: 'track-marker',
                    html: '<div style="background: #2fb344; width: 10px; height: 10px; border-radius: 50%; border: 2px solid white;"></div>',
                    iconSize: [14, 14],
                    iconAnchor: [7, 7]
                })
            }).addTo(trackMap).bindPopup('Start');

            L.marker([tracks[tracks.length - 1].latitude, tracks[tracks.length - 1].longitude], {
                icon: L.divIcon({
                    className: 'track-marker',
                    html: '<div style="background: #e03131; width: 10px; height: 10px; border-radius: 50%; border: 2px solid white;"></div>',
                    iconSize: [14, 14],
                    iconAnchor: [7, 7]
                })
            }).addTo(trackMap).bindPopup('Latest');
        }

        // Fit map to track
        if (trackLine.length > 0) {
            trackMap.fitBounds(L.polyline(trackLine).getBounds().pad(0.1));
        }
    }

    centerOnAircraft(aircraftId) {
        const marker = this.flightMarkers.get(aircraftId);
        if (marker && this.map) {
            this.map.setView(marker.getLatLng(), 10);
            marker.openPopup();
        }
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('flightDetailsModal'));
        if (modal) {
            modal.hide();
        }
    }

    // Animate marker movement smoothly
    animateMarker(marker, fromPos, toPos, flight) {
        this.isAnimating = true;
        const startTime = Date.now();
        const duration = this.animationSpeed;
        
        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function for smooth animation
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            
            const lat = fromPos.lat + (toPos[0] - fromPos.lat) * easeProgress;
            const lng = fromPos.lng + (toPos[1] - fromPos.lng) * easeProgress;
            
            marker.setLatLng([lat, lng]);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                this.isAnimating = false;
            }
        };
        
        requestAnimationFrame(animate);
    }

    // Update flight trails (like FlightAware's flight paths)
    updateFlightTrails(flights) {
        // Clear old trails
        this.flightTrails.forEach(trail => this.map.removeLayer(trail));
        this.flightTrails.clear();

        // Add trails for flights with position history
        flights.forEach(flight => {
            if (flight.position && flight.position.latitude && flight.position.longitude) {
                // Get recent track data for this aircraft
                this.getFlightTrail(flight.aircraft_id).then(trailData => {
                    if (trailData && trailData.tracks && trailData.tracks.length > 1) {
                        const trailPoints = trailData.tracks.map(track => [track.latitude, track.longitude]);
                        
                        // Create trail polyline
                        const trail = L.polyline(trailPoints, {
                            color: this.getStatusColor(flight.current_status),
                            weight: 2,
                            opacity: 0.6,
                            dashArray: '5, 5'
                        }).addTo(this.map);
                        
                        this.flightTrails.set(flight.aircraft_id, trail);
                    }
                });
            }
        });
    }

    // Get flight trail data
    async getFlightTrail(aircraftId) {
        try {
            const response = await fetch(`${this.apiBase}/${aircraftId}/track?hours=1`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching flight trail:', error);
            return null;
        }
    }

    showError(message) {
        // Simple error display
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible';
        alert.innerHTML = `
            ${message}
            <a class="btn-close" data-bs-dismiss="alert"></a>
        `;
        document.querySelector('.page-body').insertBefore(alert, document.querySelector('.page-body').firstChild);
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.map) {
            this.map.remove();
        }
    }
}

// Initialize the flight tracker when the page loads
let tracker;
document.addEventListener('DOMContentLoaded', () => {
    tracker = new FlightTracker();
});

// Global function for refresh button
function refreshData() {
    if (tracker) {
        tracker.refreshData();
    }
}
