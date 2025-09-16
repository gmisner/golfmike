/**
 * Flight Detail Page - FlightAware-style flight history page
 * Handles map rendering, data loading, and interactive features
 */

class FlightDetailPage {
    constructor() {
        this.map = null;
        this.flightData = null;
        this.aircraftId = null;
        this.flightDate = null;
        this.temperatureUnit = 'celsius'; // Default to Celsius
        
        this.init();
    }

    init() {
        this.parseUrlParams();
        this.initializeMap();
        this.loadFlightData();
        this.setupEventListeners();
    }

    parseUrlParams() {
        const urlParams = new URLSearchParams(window.location.search);
        this.aircraftId = urlParams.get('aircraft') || 'N560PB';
        this.flightDate = urlParams.get('date') || new Date().toISOString().split('T')[0];
        
        console.log('Flight Detail - Aircraft:', this.aircraftId, 'Date:', this.flightDate);
    }

    initializeMap() {
        try {
            // Initialize Leaflet map
            this.map = L.map('flight-map').setView([39.8283, -98.5795], 4);
            
            // Add tile layer
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(this.map);
            
            console.log('Map initialized successfully');
        } catch (error) {
            console.error('Error initializing map:', error);
            // Show placeholder if map fails
            document.getElementById('flight-map').innerHTML = 
                '<div class="map-placeholder">Map loading failed. Please refresh the page.</div>';
        }
    }

    async loadFlightData() {
        try {
            console.log('Loading flight data for:', this.aircraftId);
            
            // Load flight data and upcoming flights in parallel
            const [flightResponse, upcomingResponse] = await Promise.all([
                fetch(`/api/flights/${this.aircraftId}/detail?date=${this.flightDate}`),
                fetch(`/api/flights/${this.aircraftId}/upcoming`)
            ]);
            
            console.log('API response status:', flightResponse.status);
            console.log('API response headers:', flightResponse.headers);
            
            if (!flightResponse.ok) {
                throw new Error(`HTTP error! status: ${flightResponse.status}`);
            }
            
            const responseText = await flightResponse.text();
            console.log('API response text length:', responseText.length);
            console.log('API response text preview:', responseText.substring(0, 200));
            
            this.flightData = JSON.parse(responseText);
            console.log('Parsed flight data:', this.flightData);
            
            // Load upcoming flights if available
            if (upcomingResponse.ok) {
                this.upcomingFlights = await upcomingResponse.json();
                console.log('Upcoming flights:', this.upcomingFlights);
            } else {
                this.upcomingFlights = [];
            }
            
            this.renderFlightData();
            
        } catch (error) {
            console.error('Error loading flight data:', error);
            this.showError('Failed to load flight data. Please try again.');
        }
    }

    renderFlightData() {
        if (!this.flightData) {
            console.log('No flight data to render');
            return;
        }

        console.log('Rendering flight data...');

        try {
            // Update page title and header
            console.log('Updating flight header...');
            this.updateFlightHeader();
            
            // Update OOOI stats
            console.log('Updating OOOI stats...');
            this.updateOOOIStats();
            
            // Update timeline
            console.log('Updating timeline...');
            this.updateTimeline();
            
            // Update track log
            console.log('Updating track log...');
            this.updateTrackLog();
            
            // Update weather data
            console.log('Updating weather data...');
            this.updateWeatherData();
            
            // Update upcoming flights
            console.log('Updating upcoming flights...');
            this.updateUpcomingFlights();
            
            // Update aircraft details
            console.log('Updating aircraft details...');
            this.updateAircraftDetails();
            
            // Update recent flights
            console.log('Updating recent flights...');
            this.updateRecentFlights();
            
            // Render map
            console.log('Rendering map...');
            this.renderMap();
            
            console.log('Flight data rendering complete');
        } catch (error) {
            console.error('Error rendering flight data:', error);
            this.showError('Error rendering flight data. Please refresh the page.');
        }
    }

    updateFlightHeader() {
        const flight = this.flightData.flight;
        
        // Update title
        document.getElementById('aircraft-id').textContent = flight.aircraft_id || this.aircraftId;
        document.getElementById('route').textContent = 
            `${flight.departure_airport || 'UNKN'} → ${flight.arrival_airport || 'UNKN'}`;
        
        // Update flight details
        const date = new Date(flight.departure_time || this.flightDate);
        document.getElementById('flight-date').textContent = date.toLocaleDateString('en-US', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
        
        document.getElementById('departure-time').textContent = 
            date.toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit',
                timeZone: 'UTC',
                hour12: false 
            }) + 'Z';
        
        document.getElementById('flight-type').textContent = flight.flight_type || 'General Aviation';
        
        // Update status badge
        const statusBadge = document.getElementById('status-badge');
        const status = this.determineFlightStatus(flight);
        statusBadge.textContent = status.text;
        statusBadge.className = `badge ${status.class}`;
        
        // Update filed route
        document.getElementById('filed-route').textContent = 
            flight.filed_route || 'Route not available';
    }

    determineFlightStatus(flight) {
        const now = new Date();
        const departure = new Date(flight.departure_time);
        const arrival = new Date(flight.arrival_time);
        
        if (arrival && now > arrival) {
            return { text: 'Arrived', class: 'flight-status-arrived' };
        } else if (departure && now > departure) {
            return { text: 'En-route', class: 'flight-status-enroute' };
        } else if (departure && now < departure) {
            return { text: 'Scheduled', class: 'flight-status-scheduled' };
        } else {
            return { text: 'Unknown', class: 'flight-status-scheduled' };
        }
    }

    updateOOOIStats() {
        const oooi = this.flightData.oooi || {};
        
        // Update OUT time
        if (oooi.out_time) {
            document.getElementById('out-time').textContent = 
                new Date(oooi.out_time).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZone: 'UTC',
                    hour12: false
                }) + 'Z';
        }
        
        // Update OFF time
        if (oooi.off_time) {
            document.getElementById('off-time').textContent = 
                new Date(oooi.off_time).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZone: 'UTC',
                    hour12: false
                }) + 'Z';
        }
        
        // Update ON time
        if (oooi.on_time) {
            document.getElementById('on-time').textContent = 
                new Date(oooi.on_time).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZone: 'UTC',
                    hour12: false
                }) + 'Z';
        }
        
        // Update IN time
        if (oooi.in_time) {
            document.getElementById('in-time').textContent = 
                new Date(oooi.in_time).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZone: 'UTC',
                    hour12: false
                }) + 'Z';
        }
        
        // Update block time
        if (oooi.block_time) {
            document.getElementById('block-time').textContent = `Block ${oooi.block_time}`;
        }
    }

    updateTimeline() {
        const timeline = document.getElementById('flight-timeline');
        const events = this.flightData.timeline || [];
        
        timeline.innerHTML = '';
        
        if (events.length === 0) {
            timeline.innerHTML = `
                <div class="empty">
                    <div class="empty-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                            <path d="M12 8v4l3 3m6 -3a9 9 0 1 1 -18 0a9 9 0 0 1 18 0"/>
                        </svg>
                    </div>
                    <p class="empty-title">No timeline events</p>
                    <p class="empty-subtitle text-secondary">
                        Timeline events will appear here as they occur during the flight.
                    </p>
                </div>
            `;
            return;
        }
        
        events.forEach((event, index) => {
            const timelineItem = document.createElement('div');
            timelineItem.className = 'timeline-item';
            
            // Get icon based on event type
            const icon = this.getTimelineIcon(event.type || 'operational');
            
            timelineItem.innerHTML = `
                <div class="timeline-time">${this.formatTime(event.time)}</div>
                <div class="timeline-badge ${event.badge_class || 'bg-primary'}">
                    ${icon}
                </div>
                <div class="timeline-content">
                    <div class="timeline-title">${event.title}</div>
                    <div class="text-secondary">${event.description || ''}</div>
                    <div class="timeline-meta">
                        <span class="badge bg-${this.getEventTypeColor(event.type || 'operational')}">
                            ${this.getEventTypeLabel(event.type || 'operational')}
                        </span>
                    </div>
                </div>
            `;
            
            timeline.appendChild(timelineItem);
        });
    }

    getTimelineIcon(eventType) {
        const icons = {
            'operational': `<svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M12 2l3.09 6.26l6.91 1.01l-5 4.87l1.18 6.88l-6.18 -3.25l-6.18 3.25l1.18 -6.88l-5 -4.87l6.91 -1.01z"/>
            </svg>`,
            'flight': `<svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M12 2l3.09 6.26l6.91 1.01l-5 4.87l1.18 6.88l-6.18 -3.25l-6.18 3.25l1.18 -6.88l-5 -4.87l6.91 -1.01z"/>
            </svg>`,
            'weather': `<svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M12 2l3.09 6.26l6.91 1.01l-5 4.87l1.18 6.88l-6.18 -3.25l-6.18 3.25l1.18 -6.88l-5 -4.87l6.91 -1.01z"/>
            </svg>`,
            'planning': `<svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M12 2l3.09 6.26l6.91 1.01l-5 4.87l1.18 6.88l-6.18 -3.25l-6.18 3.25l1.18 -6.88l-5 -4.87l6.91 -1.01z"/>
            </svg>`
        };
        return icons[eventType] || icons['operational'];
    }

    getEventTypeColor(eventType) {
        const colors = {
            'operational': 'primary',
            'flight': 'info',
            'weather': 'warning',
            'planning': 'secondary'
        };
        return colors[eventType] || 'secondary';
    }

    getEventTypeLabel(eventType) {
        const labels = {
            'operational': 'Operational',
            'flight': 'Flight',
            'weather': 'Weather',
            'planning': 'Planning'
        };
        return labels[eventType] || 'Event';
    }

    updateTrackLog() {
        const tbody = document.getElementById('track-log-rows');
        const trackPoints = this.flightData.track || [];
        
        tbody.innerHTML = '';
        
        trackPoints.forEach(point => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${this.formatTime(point.time)}</td>
                <td>${point.latitude?.toFixed(4) || 'N/A'}</td>
                <td>${point.longitude?.toFixed(4) || 'N/A'}</td>
                <td>${point.altitude || 'N/A'}</td>
                <td>${point.ground_speed || 'N/A'}</td>
                <td>${point.remark || ''}</td>
            `;
            tbody.appendChild(row);
        });
    }

    updateWeatherData() {
        const weatherContainer = document.getElementById('weather-data');
        const weather = this.flightData.weather || {};
        
        weatherContainer.innerHTML = '';
        
        // Add departure airport weather
        if (weather.departure_metar) {
            const depCard = document.createElement('div');
            depCard.className = 'col-md-6';
            depCard.innerHTML = `
                <div class="card card-sm">
                    <div class="card-header">
                        <div class="d-flex align-items-center justify-content-between">
                            <div>
                                <strong>${weather.departure_metar.station_id} METAR</strong>
                                <span class="badge bg-${this.getFlightCategoryColor(weather.departure_metar.flight_category)} ms-2">
                                    ${weather.departure_metar.flight_category || 'UNKN'}
                                </span>
                            </div>
                            <button class="btn btn-sm btn-outline-secondary" onclick="flightDetailPage.toggleTemperatureUnit()" title="Toggle temperature unit">
                                ${this.temperatureUnit === 'celsius' ? '°F' : '°C'}
                            </button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="row g-2">
                            <div class="col-6">
                                <div class="text-secondary small">Temperature</div>
                                <div class="fw-bold">
                                    ${this.formatTemperature(weather.departure_metar.temperature)}
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="text-secondary small">Wind</div>
                                <div class="fw-bold">${weather.departure_metar.wind_direction || 'N/A'}°/${weather.departure_metar.wind_speed || 'N/A'}kt</div>
                            </div>
                            <div class="col-6">
                                <div class="text-secondary small">Visibility</div>
                                <div class="fw-bold">${weather.departure_metar.visibility || 'N/A'} mi</div>
                            </div>
                            <div class="col-6">
                                <div class="text-secondary small">Dewpoint</div>
                                <div class="fw-bold">
                                    ${this.formatTemperature(weather.departure_metar.dewpoint)}
                                </div>
                            </div>
                        </div>
                        <div class="mt-2">
                            <div class="text-secondary small">Raw METAR</div>
                            <div class="small route-code">${weather.departure_metar.raw_text || 'No data available'}</div>
                        </div>
                    </div>
                </div>
            `;
            weatherContainer.appendChild(depCard);
        }
        
        // Add arrival airport weather
        if (weather.arrival_metar) {
            const arrCard = document.createElement('div');
            arrCard.className = 'col-md-6';
            arrCard.innerHTML = `
                <div class="card card-sm">
                    <div class="card-header">
                        <div class="d-flex align-items-center justify-content-between">
                            <div>
                                <strong>${weather.arrival_metar.station_id} METAR</strong>
                                <span class="badge bg-${this.getFlightCategoryColor(weather.arrival_metar.flight_category)} ms-2">
                                    ${weather.arrival_metar.flight_category || 'UNKN'}
                                </span>
                            </div>
                            <button class="btn btn-sm btn-outline-secondary" onclick="flightDetailPage.toggleTemperatureUnit()" title="Toggle temperature unit">
                                ${this.temperatureUnit === 'celsius' ? '°F' : '°C'}
                            </button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="row g-2">
                            <div class="col-6">
                                <div class="text-secondary small">Temperature</div>
                                <div class="fw-bold">
                                    ${this.formatTemperature(weather.arrival_metar.temperature)}
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="text-secondary small">Wind</div>
                                <div class="fw-bold">${weather.arrival_metar.wind_direction || 'N/A'}°/${weather.arrival_metar.wind_speed || 'N/A'}kt</div>
                            </div>
                            <div class="col-6">
                                <div class="text-secondary small">Visibility</div>
                                <div class="fw-bold">${weather.arrival_metar.visibility || 'N/A'} mi</div>
                            </div>
                            <div class="col-6">
                                <div class="text-secondary small">Dewpoint</div>
                                <div class="fw-bold">
                                    ${this.formatTemperature(weather.arrival_metar.dewpoint)}
                                </div>
                            </div>
                        </div>
                        <div class="mt-2">
                            <div class="text-secondary small">Raw METAR</div>
                            <div class="small route-code">${weather.arrival_metar.raw_text || 'No data available'}</div>
                        </div>
                    </div>
                </div>
            `;
            weatherContainer.appendChild(arrCard);
        }
        
        // Add TAF forecasts
        if (weather.departure_taf || weather.arrival_taf) {
            const tafCard = document.createElement('div');
            tafCard.className = 'col-12';
            tafCard.innerHTML = `
                <div class="card card-sm">
                    <div class="card-header"><strong>TAF Forecasts</strong></div>
                    <div class="card-body">
                        <div class="row g-3">
                            ${weather.departure_taf ? `
                                <div class="col-md-6">
                                    <div class="text-secondary small">${weather.departure_taf.station_id} TAF</div>
                                    <div class="small route-code">${weather.departure_taf.raw_text || 'No TAF available'}</div>
                                </div>
                            ` : ''}
                            ${weather.arrival_taf ? `
                                <div class="col-md-6">
                                    <div class="text-secondary small">${weather.arrival_taf.station_id} TAF</div>
                                    <div class="small route-code">${weather.arrival_taf.raw_text || 'No TAF available'}</div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
            weatherContainer.appendChild(tafCard);
        }
        
        // Add weather alerts
        if (weather.weather_alerts && weather.weather_alerts.length > 0) {
            const alertsCard = document.createElement('div');
            alertsCard.className = 'col-12';
            alertsCard.innerHTML = `
                <div class="card card-sm">
                    <div class="card-header">
                        <strong>Weather Alerts</strong>
                        <span class="badge bg-warning ms-2">${weather.weather_alerts.length}</span>
                    </div>
                    <div class="card-body">
                        ${weather.weather_alerts.map(alert => `
                            <div class="alert alert-${this.getAlertSeverityColor(alert.severity)} alert-dismissible" role="alert">
                                <div class="d-flex">
                                    <div class="flex-fill">
                                        <div class="d-flex align-items-center mb-1">
                                            <h4 class="alert-title mb-0">${alert.alert_type}</h4>
                                            <span class="badge bg-${this.getAlertSourceColor(alert.source)} ms-2">${alert.source}</span>
                                            <span class="badge bg-${this.getAlertUrgencyColor(alert.urgency)} ms-1">${alert.urgency}</span>
                                        </div>
                                        <div class="text-secondary">${alert.summary || alert.description}</div>
                                        <div class="small text-muted mt-1">
                                            <div>Valid: ${this.formatTime(alert.valid_from)} - ${this.formatTime(alert.valid_until)}</div>
                                            ${alert.affected_area ? `<div>Area: ${this.formatAffectedArea(alert.affected_area)}</div>` : ''}
                                        </div>
                                    </div>
                                    <div class="ms-3">
                                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            weatherContainer.appendChild(alertsCard);
        }
        
        // Show message if no weather data
        if (!weather.departure_metar && !weather.arrival_metar && (!weather.weather_alerts || weather.weather_alerts.length === 0)) {
            const noDataCard = document.createElement('div');
            noDataCard.className = 'col-12';
            noDataCard.innerHTML = `
                <div class="card card-sm">
                    <div class="card-body text-center text-secondary">
                        <div class="empty">
                            <div class="empty-icon">
                                <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                                    <path d="M10 10v4a2 2 0 1 0 4 0v-4a2 2 0 1 0 -4 0z"/>
                                    <path d="M10 6h4"/>
                                    <path d="M10 18h4"/>
                                    <path d="M5 12h14"/>
                                </svg>
                            </div>
                            <p class="empty-title">No weather data available</p>
                            <p class="empty-subtitle text-secondary">
                                Weather data will appear here when available for this flight's airports.
                            </p>
                        </div>
                    </div>
                </div>
            `;
            weatherContainer.appendChild(noDataCard);
        }
    }

    updateUpcomingFlights() {
        const upcomingContainer = document.getElementById('upcoming-flights');
        if (!upcomingContainer) return;

        if (!this.upcomingFlights || this.upcomingFlights.length === 0) {
            upcomingContainer.innerHTML = `
                <div class="card card-sm">
                    <div class="card-body text-center text-secondary">
                        <div class="empty">
                            <div class="empty-icon">
                                <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                                    <path d="M12 2l3.09 6.26l6.91 1.01l-5 4.87l1.18 6.88l-6.18 -3.25l-6.18 3.25l1.18 -6.88l-5 -4.87l6.91 -1.01z"/>
                                </svg>
                            </div>
                            <p class="empty-title">No upcoming flights</p>
                            <p class="empty-subtitle text-secondary">
                                No scheduled flights found for this aircraft.
                            </p>
                        </div>
                    </div>
                </div>
            `;
            return;
        }

        upcomingContainer.innerHTML = `
            <div class="card card-sm">
                <div class="card-header">
                    <strong>Upcoming Flights</strong>
                    <span class="badge bg-info ms-2">${this.upcomingFlights.length}</span>
                </div>
                <div class="card-body">
                    <div class="list-group list-group-flush">
                        ${this.upcomingFlights.map(flight => `
                            <div class="list-group-item px-0">
                                <div class="row align-items-center">
                                    <div class="col">
                                        <div class="d-flex align-items-center">
                                            <div class="flex-fill">
                                                <div class="fw-bold">${flight.flight_reference || flight.aircraft_id}</div>
                                                <div class="text-muted small">
                                                    ${flight.departure_airport || 'TBD'} → ${flight.arrival_airport || 'TBD'}
                                                </div>
                                                <div class="text-muted small">
                                                    <i class="ti ti-clock me-1"></i>
                                                    Dep: ${flight.departure_time ? new Date(flight.departure_time).toLocaleString() : 'TBD'}
                                                </div>
                                                ${flight.aircraft_type ? `
                                                    <div class="text-muted small">
                                                        <i class="ti ti-plane me-1"></i>
                                                        ${flight.aircraft_type}
                                                    </div>
                                                ` : ''}
                                                ${flight.aircraft_operator ? `
                                                    <div class="text-muted small">
                                                        <i class="ti ti-building me-1"></i>
                                                        ${flight.aircraft_operator}
                                                    </div>
                                                ` : ''}
                                            </div>
                                            <div class="ms-3">
                                                <span class="badge bg-${this.getStatusColor(flight.status)}">${flight.status}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    getStatusColor(status) {
        switch(status) {
            case 'PLANNED': return 'info';
            case 'ACTIVE': return 'success';
            case 'COMPLETED': return 'secondary';
            case 'CANCELLED': return 'danger';
            default: return 'secondary';
        }
    }
    
    getFlightCategoryColor(category) {
        switch(category) {
            case 'VFR': return 'success';
            case 'MVFR': return 'warning';
            case 'IFR': return 'danger';
            case 'LIFR': return 'dark';
            default: return 'secondary';
        }
    }
    
    getAlertSeverityColor(severity) {
        switch(severity) {
            case 'LOW': return 'info';
            case 'MODERATE': return 'warning';
            case 'HIGH': return 'danger';
            case 'EXTREME': return 'dark';
            default: return 'secondary';
        }
    }
    
    getAlertSourceColor(source) {
        switch(source) {
            case 'ITWS': return 'primary';
            case 'API': return 'success';
            default: return 'secondary';
        }
    }
    
    getAlertUrgencyColor(urgency) {
        switch(urgency) {
            case 'IMMEDIATE': return 'danger';
            case 'EXPECTED': return 'warning';
            case 'FUTURE': return 'info';
            case 'PAST': return 'secondary';
            default: return 'secondary';
        }
    }
    
    formatAffectedArea(affectedArea) {
        if (!affectedArea) return 'Unknown';
        
        if (typeof affectedArea === 'string') {
            return affectedArea;
        }
        
        if (typeof affectedArea === 'object') {
            const parts = [];
            if (affectedArea.fir_name) parts.push(affectedArea.fir_name);
            if (affectedArea.airports) parts.push(affectedArea.airports);
            if (affectedArea.hazard) parts.push(affectedArea.hazard);
            return parts.join(', ') || 'Unknown area';
        }
        
        return 'Unknown';
    }

    updateAircraftDetails() {
        const aircraft = this.flightData.aircraft || {};
        
        // Update aircraft registration
        document.getElementById('aircraft-reg').textContent = aircraft.registration || this.aircraftId;
        
        // Update aircraft type
        document.getElementById('aircraft-type').textContent = aircraft.type || 'Unknown';
        
        // Update aircraft avatar
        const avatar = document.getElementById('aircraft-avatar');
        avatar.textContent = (aircraft.registration || this.aircraftId).substring(1, 3);
        
        // Update owner
        document.getElementById('aircraft-owner').textContent = aircraft.owner || 'Private';
        
        // Update equipment
        document.getElementById('aircraft-equipment').textContent = aircraft.equipment || 'ADS-B Out';
    }

    async updateRecentFlights() {
        try {
            const response = await fetch(`/api/flights/${this.aircraftId}/recent`);
            const recentFlights = await response.json();
            
            const container = document.getElementById('recent-flights');
            container.innerHTML = '';
            
            recentFlights.forEach(flight => {
                const item = document.createElement('a');
                item.className = 'list-group-item';
                item.href = `?aircraft=${this.aircraftId}&date=${flight.date}`;
                item.textContent = `${flight.route} · ${flight.date}`;
                container.appendChild(item);
            });
            
        } catch (error) {
            console.error('Error loading recent flights:', error);
        }
    }

    renderMap() {
        if (!this.map || !this.flightData.track) return;
        
        try {
            // Clear existing markers and polylines
            this.map.eachLayer(layer => {
                if (layer instanceof L.Marker || layer instanceof L.Polyline) {
                    this.map.removeLayer(layer);
                }
            });
            
            const trackPoints = this.flightData.track || [];
            if (trackPoints.length === 0) return;
            
            // Create polyline from track points
            const latLngs = trackPoints
                .filter(point => point.latitude && point.longitude)
                .map(point => [point.latitude, point.longitude]);
            
            if (latLngs.length > 0) {
                const polyline = L.polyline(latLngs, {
                    color: '#007bff',
                    weight: 3,
                    opacity: 0.8
                }).addTo(this.map);
                
                // Add departure marker
                if (latLngs[0]) {
                    L.marker(latLngs[0], {
                        icon: L.divIcon({
                            className: 'departure-marker',
                            html: '<div style="background: #28a745; color: white; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold;">D</div>',
                            iconSize: [20, 20]
                        })
                    }).addTo(this.map);
                }
                
                // Add arrival marker
                if (latLngs[latLngs.length - 1]) {
                    L.marker(latLngs[latLngs.length - 1], {
                        icon: L.divIcon({
                            className: 'arrival-marker',
                            html: '<div style="background: #dc3545; color: white; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold;">A</div>',
                            iconSize: [20, 20]
                        })
                    }).addTo(this.map);
                }
                
                // Fit map to show entire route
                this.map.fitBounds(polyline.getBounds(), { padding: [20, 20] });
            }
            
        } catch (error) {
            console.error('Error rendering map:', error);
        }
    }

    setupEventListeners() {
        // Global search functionality
        const searchInput = document.getElementById('global-search');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const query = e.target.value.trim();
                    if (query) {
                        window.location.href = `/flight-plan.html?q=${encodeURIComponent(query)}`;
                    }
                }
            });
        }
        
        // Download CSV functionality
        const downloadBtn = document.getElementById('download-btn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.downloadCSV();
            });
        }
        
        // Share functionality
        const shareBtn = document.getElementById('share-btn');
        if (shareBtn) {
            shareBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.shareFlight();
            });
        }
    }

    downloadCSV() {
        if (!this.flightData.track) {
            alert('No track data available for download');
            return;
        }
        
        const csvContent = this.generateCSV();
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `flight-${this.aircraftId}-${this.flightDate}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    generateCSV() {
        const headers = ['Time (Z)', 'Latitude', 'Longitude', 'Altitude', 'Ground Speed', 'Remark'];
        const rows = this.flightData.track.map(point => [
            this.formatTime(point.time),
            point.latitude || '',
            point.longitude || '',
            point.altitude || '',
            point.ground_speed || '',
            point.remark || ''
        ]);
        
        return [headers, ...rows].map(row => row.join(',')).join('\n');
    }

    shareFlight() {
        const url = window.location.href;
        if (navigator.share) {
            navigator.share({
                title: `Flight ${this.aircraftId}`,
                text: `View flight details for ${this.aircraftId}`,
                url: url
            });
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(url).then(() => {
                alert('Flight URL copied to clipboard!');
            });
        }
    }

    formatTime(timeString) {
        if (!timeString) return 'N/A';
        const date = new Date(timeString);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            timeZone: 'UTC',
            hour12: false
        });
    }

    formatTemperature(temperature) {
        if (!temperature) return 'N/A';
        
        // Handle both old format (number) and new format (object)
        if (typeof temperature === 'number') {
            return `${temperature}°C`;
        }
        
        if (typeof temperature === 'object' && temperature !== null) {
            const value = this.temperatureUnit === 'fahrenheit' ? temperature.fahrenheit : temperature.celsius;
            const unit = this.temperatureUnit === 'fahrenheit' ? 'F' : 'C';
            return `${value}°${unit}`;
        }
        
        return 'N/A';
    }

    toggleTemperatureUnit() {
        this.temperatureUnit = this.temperatureUnit === 'celsius' ? 'fahrenheit' : 'celsius';
        this.updateWeatherData(); // Re-render weather data with new unit
    }

    showError(message) {
        // Show error message to user
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger';
        errorDiv.textContent = message;
        
        const container = document.querySelector('.container-xl');
        container.insertBefore(errorDiv, container.firstChild);
        
        // Remove error after 5 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }
}

// Initialize the flight detail page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.flightDetailPage = new FlightDetailPage();
});
