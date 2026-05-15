/**
 * Flight Detail Page - FlightAware-style flight history page
 * Handles map rendering, data loading, and interactive features
 */

/** Initial bearing from point a → b (degrees clockwise from north; 0=N, 90=E). */
function flightDetailInitialBearingDeg(lat1, lng1, lat2, lng2) {
    const φ1 = (lat1 * Math.PI) / 180;
    const φ2 = (lat2 * Math.PI) / 180;
    const Δλ = ((lng2 - lng1) * Math.PI) / 180;
    const y = Math.sin(Δλ) * Math.cos(φ2);
    const x =
        Math.cos(φ1) * Math.sin(φ2) -
        Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
    const θ = Math.atan2(y, x);
    return ((θ * 180) / Math.PI + 360) % 360;
}

/** Top-down aircraft SVG (nose up); rotate with CSS for heading. */
function flightDetailAircraftMapIconHtml(rotationDeg) {
    const r = Number.isFinite(rotationDeg) ? rotationDeg : 0;
    const svg = `
<svg class="flight-detail-aircraft-svg" viewBox="0 0 48 48" width="40" height="40" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <g transform="translate(24,24)">
    <path fill="#39ff14" stroke="#0d0d0d" stroke-width="1.35" stroke-linejoin="round"
      d="M0,-18 L-3.5,5 L-15,8 L-15,11 L-4,10 L-2,17 L0,15 L2,17 L4,10 L15,11 L15,8 L3.5,5 L0,-18 Z"/>
  </g>
</svg>`;
    return `<div class="flight-map-aircraft-marker-inner" style="transform:rotate(${r}deg)">${svg}</div>`;
}

function flightDetailAircraftDivIcon(rotationDeg) {
    return L.divIcon({
        className: 'flight-map-aircraft-marker',
        html: flightDetailAircraftMapIconHtml(rotationDeg),
        iconSize: [40, 40],
        iconAnchor: [20, 20],
    });
}

class FlightDetailPage {
    constructor() {
        this.map = null;
        this.flightData = null;
        this.aircraftId = null;
        this.flightDate = null;
        this.temperatureUnit = 'celsius'; // Default to Celsius
        this.trackProfileChart = null;
        this.mapOverlayGroup = null;
        this._liveTrackTimer = null;
        this._mapFitBoundsOnce = false;
        
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
        // Search UI and most links use ?aircraft_id=; flight-tracker uses ?aircraft=
        this.aircraftId =
            urlParams.get('aircraft_id') || urlParams.get('aircraft') || null;
        this.flightDate = urlParams.get('date') || new Date().toISOString().split('T')[0];

        console.log('Flight Detail - Aircraft:', this.aircraftId, 'Date:', this.flightDate);
    }

    initializeMap() {
        try {
            // Initialize Leaflet map
            this.map = L.map('flight-map').setView([39.8283, -98.5795], 4);
            
            // Add tile layer
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
                subdomains: 'abcd', maxZoom: 19
            }).addTo(this.map);

            this.mapOverlayGroup = L.layerGroup().addTo(this.map);
            
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
            if (!this.aircraftId) {
                this.showError(
                    'Missing aircraft. Open this page from search (View Details) or use ?aircraft_id=TAIL_OR_CALLSIGN in the URL.'
                );
                return;
            }

            console.log('Loading flight data for:', this.aircraftId);
            this._mapFitBoundsOnce = false;

            // Load flight data and upcoming flights in parallel
            const [flightResponse, upcomingResponse] = await Promise.all([
                fetch(`/api/flights/${this.aircraftId}/detail?date=${this.flightDate}`),
                fetch(`/api/flights/${this.aircraftId}/upcoming?include_past=1`)
            ]);

            if (!flightResponse.ok) {
                throw new Error(`HTTP error! status: ${flightResponse.status}`);
            }

            this.flightData = await flightResponse.json();

            // Fetch planned route waypoints using GUFI (parallel, non-blocking)
            const gufi = this.flightData?.flight?.gufi ||
                         new URLSearchParams(window.location.search).get('gufi');
            if (gufi) {
                fetch(`/v1/flights/${encodeURIComponent(gufi)}/route-overlay`)
                    .then(r => r.ok ? r.json() : null)
                    .then(overlay => {
                        if (!overlay) return;
                        const pts = (overlay.planned_route || [])
                            .filter(w => w.latitude != null && w.longitude != null)
                            .map(w => [w.latitude, w.longitude]);
                        if (pts.length >= 2) {
                            this.flightData.planned_route = pts;
                            this.renderMap();
                        }
                    })
                    .catch(() => {});
            }

            if (upcomingResponse.ok) {
                this.upcomingFlights = await upcomingResponse.json();
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
            this.updateOperationalBanner();
            this.updateNcsmRoutePanel(this.flightData.route_assignment);

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

            // Update latest oceanic report panel
            console.log('Updating oceanic report panel...');
            this.updateOceanicReport();
            
            // Update recent flights
            console.log('Updating recent flights...');
            this.updateRecentFlights();
            
            // Render map
            console.log('Rendering map...');
            this.renderMap();
            
            console.log('Flight data rendering complete');

            this.startLiveTrackPolling();
        } catch (error) {
            console.error('Error rendering flight data:', error);
            this.showError('Error rendering flight data. Please refresh the page.');
        }
    }

    updateOperationalBanner() {
        const wrap = document.getElementById('operational-banner-wrap');
        const el = document.getElementById('operational-banner');
        const alertsNav = document.getElementById('alerts-page-btn');
        if (alertsNav && this.aircraftId) {
            alertsNav.href = `/flight-alerts.html?aircraft_id=${encodeURIComponent(this.aircraftId)}`;
        }
        if (!wrap || !el) return;
        const op = this.flightData.operational;
        if (!op) {
            wrap.classList.add('d-none');
            return;
        }
        const links = op.links || {};
        const alertsHref = links.alerts_page || `/flight-alerts.html?aircraft_id=${encodeURIComponent(this.aircraftId)}`;
        const n = Number(op.alerts_unacknowledged_30d || 0);
        const recent = Array.isArray(op.recent_swim_alerts) ? op.recent_swim_alerts.length : 0;
        if (n > 0) {
            el.className = 'alert alert-warning mb-0';
            el.innerHTML =
                `You have <strong>${n}</strong> unacknowledged operational alert(s) in the last 30 days (by tail <strong>${this.aircraftId}</strong>). ` +
                `<a href="${alertsHref}">View alerts</a> — GUFI is shown only for reference.`;
            wrap.classList.remove('d-none');
        } else if (recent > 0) {
            el.className = 'alert alert-info mb-0';
            el.innerHTML =
                `Recent SWIM / operational messages for this tail. ` +
                `<a href="${alertsHref}">Browse alerts</a>.`;
            wrap.classList.remove('d-none');
        } else {
            wrap.classList.add('d-none');
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
        
        // Show airway/fix string when present, plus OD (expected_route) when it adds info
        const detail = (flight.filed_route || flight.route_text || '').trim();
        const od = (flight.expected_route || '').trim();
        let routeLine;
        if (detail && od && detail.replace(/\s/g, '') !== od.replace(/\s/g, '')) {
            routeLine = `${detail} · ${od}`;
        } else {
            routeLine = detail || od || 'Route not available';
        }
        document.getElementById('filed-route').textContent = routeLine;
    }

    /**
     * FlightScheduleActivate (NCSM) payload from route_assignments — fixes, alt, routeOfFlight.
     */
    updateNcsmRoutePanel(ra) {
        const panel = document.getElementById('ncsm-route-panel');
        if (!panel) return;
        const hasContent =
            ra &&
            (ra.route_of_flight ||
                (ra.fixes && ra.fixes.length) ||
                (ra.waypoints && ra.waypoints.length) ||
                ra.assigned_altitude != null ||
                ra.assigned_speed != null);
        if (!hasContent) {
            panel.classList.add('d-none');
            return;
        }
        panel.classList.remove('d-none');
        const parts = [];
        if (ra.assigned_altitude != null && ra.assigned_altitude !== '') {
            parts.push(`Assigned alt ${ra.assigned_altitude} ft`);
        }
        if (ra.assigned_speed != null && ra.assigned_speed !== '') {
            parts.push(`Filed TAS ${ra.assigned_speed} kt`);
        }
        if (ra.etd) parts.push(`ETD ${ra.etd}`);
        if (ra.eta) parts.push(`ETA ${ra.eta}`);
        if (ra.source_facility) parts.push(`Facility ${ra.source_facility}`);
        document.getElementById('ncsm-meta').textContent = parts.join(' · ');
        document.getElementById('ncsm-route-of-flight').textContent =
            ra.route_of_flight || '';
        let fixLine = '';
        if (ra.fixes && ra.fixes.length) {
            const names = ra.fixes.map((f) =>
                typeof f === 'string'
                    ? f
                    : f.name || f.fix || ''
            ).filter(Boolean);
            fixLine = `Fixes (${names.length}): ${names.join(' → ')}`;
        }
        document.getElementById('ncsm-fixes').textContent = fixLine;
        const hint = document.getElementById('ncsm-doc-hint');
        if (hint) {
            hint.textContent = ra.documentation || '';
        }
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
            
            // Get icon based on event type and title
            const icon = this.getTimelineIcon(event.type || 'operational', event.title || '');
            
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

    getTimelineIcon(eventType, eventTitle = '') {
        // Check for specific event types based on title
        if (eventTitle.includes('Takeoff') || eventTitle.includes('OFF')) {
            return `<svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M12 2l-2 4l-4 1l2 2l-1 4l4 -2l4 2l-1 -4l2 -2l-4 -1z"/>
                <path d="M12 2l2 4l4 1l-2 2l1 4l-4 -2l-4 2l1 -4l-2 -2l4 -1z"/>
            </svg>`;
        }
        
        if (eventTitle.includes('Landing') || eventTitle.includes('ON')) {
            return `<svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M12 2l-2 4l-4 1l2 2l-1 4l4 -2l4 2l-1 -4l2 -2l-4 -1z"/>
                <path d="M12 2l2 4l4 1l-2 2l1 4l-4 -2l-4 2l1 -4l-2 -2l4 -1z"/>
            </svg>`;
        }
        
        if (eventTitle.includes('Pushback') || eventTitle.includes('OUT')) {
            return `<svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M12 2l-2 4l-4 1l2 2l-1 4l4 -2l4 2l-1 -4l2 -2l-4 -1z"/>
            </svg>`;
        }
        
        if (eventTitle.includes('At Block') || eventTitle.includes('IN')) {
            return `<svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M12 2l-2 4l-4 1l2 2l-1 4l4 -2l4 2l-1 -4l2 -2l-4 -1z"/>
            </svg>`;
        }

        const icons = {
            'operational': `<svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M12 2l3.09 6.26l6.91 1.01l-5 4.87l1.18 6.88l-6.18 -3.25l-6.18 3.25l1.18 -6.88l-5 -4.87l6.91 -1.01z"/>
            </svg>`,
            'flight': `<svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M12 2l-2 4l-4 1l2 2l-1 4l4 -2l4 2l-1 -4l2 -2l-4 -1z"/>
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
            const gs = point.ground_speed ?? point.speed;
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${this.formatTime(point.time)}</td>
                <td>${point.latitude?.toFixed(4) || 'N/A'}</td>
                <td>${point.longitude?.toFixed(4) || 'N/A'}</td>
                <td>${this.formatAltitudeDisplay(point.altitude)}</td>
                <td>${gs ?? 'N/A'}</td>
                <td>${point.remark || ''}</td>
            `;
            tbody.appendChild(row);
        });

        this.updateTrackProfileChart(trackPoints);
    }

    /**
     * Parse a track numeric field (altitude, ground_speed) from API / DB.
     * @returns {number|null}
     */
    parseTrackNumber(value) {
        if (value === null || value === undefined || value === '') {
            return null;
        }
        if (typeof value === 'string') {
            const cleaned = value.replace(/,/g, '').trim();
            if (cleaned === '') {
                return null;
            }
            const n = Number(cleaned);
            return Number.isFinite(n) ? n : null;
        }
        const n = Number(value);
        return Number.isFinite(n) ? n : null;
    }

    /**
     * NAS simpleAltitude is often flight level in hundreds of feet (360 = FL360 = 36,000 ft).
     * Matches utils.nas_altitude.normalize_altitude_to_feet_maybe_legacy for legacy rows.
     */
    normalizeAltitudeFeet(value) {
        const n = this.parseTrackNumber(value);
        if (n === null) {
            return null;
        }
        if (n >= 10000) {
            return n;
        }
        if (n >= 10 && n <= 99) {
            return n * 100;
        }
        if (n >= 100 && n <= 600 && n !== 500) {
            return n * 100;
        }
        return n;
    }

    formatAltitudeDisplay(value) {
        const n = this.normalizeAltitudeFeet(value);
        if (n === null) {
            return 'N/A';
        }
        return String(n);
    }

    startLiveTrackPolling() {
        if (this._liveTrackTimer) {
            clearInterval(this._liveTrackTimer);
            this._liveTrackTimer = null;
        }
        if (!this.aircraftId) {
            return;
        }
        const poll = () => this.pollLiveTrack();
        setTimeout(poll, 1500);
        this._liveTrackTimer = setInterval(poll, 25000);
    }

    async pollLiveTrack() {
        if (!this.aircraftId || !this.flightData || document.hidden) {
            return;
        }
        try {
            const res = await fetch(
                `/api/flights/${encodeURIComponent(this.aircraftId)}/track?date=${encodeURIComponent(this.flightDate)}`
            );
            if (!res.ok) {
                return;
            }
            const data = await res.json();
            const raw = data.tracks || [];
            if (!raw.length) {
                return;
            }
            const normalized = raw
                .map((t) => ({
                    time: t.timestamp,
                    latitude: t.latitude,
                    longitude: t.longitude,
                    altitude: t.altitude,
                    ground_speed: t.speed ?? t.ground_speed,
                    remark: '',
                }))
                .sort((a, b) => new Date(a.time) - new Date(b.time));
            this.flightData.track = normalized;
            this.updateTrackLog();
            this.renderMap();
        } catch (e) {
            console.error('Live track poll failed', e);
        }
    }

    /**
     * Line chart: altitude (ft), ground speed (kts), or latitude (°N) vs time.
     * Uses Chart.js when available; falls back to native canvas if the library did not load.
     */
    updateTrackProfileChart(trackPoints) {
        const card = document.getElementById('track-profile-card');
        const section = document.getElementById('track-profile-section');
        const noData = document.getElementById('track-profile-no-data');
        const note = document.getElementById('track-profile-note');
        const canvas = document.getElementById('track-profile-chart');
        if (!card || !section || !canvas) {
            return;
        }

        if (this.trackProfileChart) {
            this.trackProfileChart.destroy();
            this.trackProfileChart = null;
        }

        const hideCard = () => {
            card.classList.add('d-none');
            section.classList.add('d-none');
            if (noData) {
                noData.classList.add('d-none');
            }
            if (note) {
                note.classList.add('d-none');
                note.textContent = '';
            }
        };

        if (!trackPoints.length) {
            hideCard();
            return;
        }

        const labels = trackPoints.map((p) => this.formatChartAxisTime(p.time));
        const altData = trackPoints.map((p) => this.normalizeAltitudeFeet(p.altitude));
        const gsData = trackPoints.map((p) =>
            this.parseTrackNumber(p.ground_speed ?? p.speed)
        );
        const latData = trackPoints.map((p) => this.parseTrackNumber(p.latitude));

        const hasAlt = altData.some((v) => v !== null);
        const hasGs = gsData.some((v) => v !== null);
        const hasLat = latData.some((v) => v !== null);
        const hasAltOrGs = hasAlt || hasGs;

        card.classList.remove('d-none');

        if (!hasAltOrGs && !hasLat) {
            section.classList.add('d-none');
            if (noData) {
                noData.classList.remove('d-none');
            }
            if (note) {
                note.classList.add('d-none');
            }
            return;
        }

        if (noData) {
            noData.classList.add('d-none');
        }
        if (note) {
            if (!hasAltOrGs && hasLat) {
                note.textContent =
                    'Altitude and speed are not in this feed; showing latitude vs time.';
                note.classList.remove('d-none');
            } else {
                note.classList.add('d-none');
                note.textContent = '';
            }
        }
        section.classList.remove('d-none');

        const ChartCtor = typeof window !== 'undefined' ? window.Chart : undefined;

        const buildChartConfig = () => {
            if (hasAltOrGs) {
                return {
                    type: 'line',
                    data: {
                        labels,
                        datasets: [
                            {
                                label: 'Altitude (ft)',
                                data: altData,
                                yAxisID: 'y',
                                borderColor: 'rgb(32, 107, 196)',
                                backgroundColor: 'rgba(32, 107, 196, 0.08)',
                                fill: false,
                                tension: 0.15,
                                spanGaps: true,
                                hidden: !hasAlt,
                            },
                            {
                                label: 'Ground speed (kts)',
                                data: gsData,
                                yAxisID: 'y1',
                                borderColor: 'rgb(247, 103, 7)',
                                backgroundColor: 'rgba(247, 103, 7, 0.08)',
                                fill: false,
                                tension: 0.15,
                                spanGaps: true,
                                hidden: !hasGs,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: { mode: 'index', intersect: false },
                        plugins: {
                            legend: { position: 'top' },
                            tooltip: {
                                callbacks: {
                                    label(ctx) {
                                        const v = ctx.parsed.y;
                                        if (v === null || v === undefined) {
                                            return `${ctx.dataset.label}: —`;
                                        }
                                        const unit =
                                            ctx.dataset.yAxisID === 'y' ? ' ft' : ' kts';
                                        return `${ctx.dataset.label}: ${v}${unit}`;
                                    },
                                },
                            },
                        },
                        scales: {
                            x: {
                                ticks: {
                                    maxRotation: 45,
                                    minRotation: 0,
                                    autoSkip: true,
                                    maxTicksLimit: 12,
                                },
                            },
                            y: {
                                type: 'linear',
                                display: hasAlt,
                                position: 'left',
                                title: {
                                    display: true,
                                    text: 'Altitude (ft)',
                                },
                                grid: { drawOnChartArea: true },
                            },
                            y1: {
                                type: 'linear',
                                display: hasGs,
                                position: 'right',
                                title: {
                                    display: true,
                                    text: 'Ground speed (kts)',
                                },
                                grid: { drawOnChartArea: false },
                            },
                        },
                    },
                };
            }
            return {
                type: 'line',
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'Latitude (°N)',
                            data: latData,
                            borderColor: 'rgb(32, 107, 196)',
                            backgroundColor: 'rgba(32, 107, 196, 0.08)',
                            fill: false,
                            tension: 0.15,
                            spanGaps: true,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { position: 'top' },
                        tooltip: {
                            callbacks: {
                                label(ctx) {
                                    const v = ctx.parsed.y;
                                    if (v === null || v === undefined) {
                                        return `${ctx.dataset.label}: —`;
                                    }
                                    return `${ctx.dataset.label}: ${v}°`;
                                },
                            },
                        },
                    },
                    scales: {
                        x: {
                            ticks: {
                                maxRotation: 45,
                                minRotation: 0,
                                autoSkip: true,
                                maxTicksLimit: 12,
                            },
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Latitude (°N)',
                            },
                        },
                    },
                },
            };
        };

        const ctx = canvas.getContext('2d');
        if (!ctx) {
            return;
        }

        if (typeof ChartCtor === 'function') {
            try {
                this.trackProfileChart = new ChartCtor(ctx, buildChartConfig());
                requestAnimationFrame(() => {
                    if (this.trackProfileChart) {
                        this.trackProfileChart.resize();
                    }
                });
                return;
            } catch (e) {
                console.error('Chart.js render failed, using canvas fallback', e);
            }
        }

        this.drawNativeTrackProfileChart(
            canvas,
            labels,
            altData,
            gsData,
            latData,
            hasAltOrGs
        );
    }

    /**
     * Minimal canvas fallback when Chart.js is blocked or throws.
     */
    drawNativeTrackProfileChart(
        canvas,
        labels,
        altData,
        gsData,
        latData,
        hasAltOrGs
    ) {
        const ctx = canvas.getContext('2d');
        if (!ctx) {
            return;
        }
        const wrap = canvas.parentElement;
        const cssW = Math.max(wrap ? wrap.clientWidth : 400, 320);
        const cssH = 280;
        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.floor(cssW * dpr);
        canvas.height = Math.floor(cssH * dpr);
        canvas.style.width = `${cssW}px`;
        canvas.style.height = `${cssH}px`;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, cssW, cssH);

        const pad = { l: 44, r: 44, t: 20, b: 32 };
        const plotW = cssW - pad.l - pad.r;
        const plotH = cssH - pad.t - pad.b;
        const n = labels.length;

        const xAt = (i) => {
            if (n <= 1) {
                return pad.l + plotW / 2;
            }
            return pad.l + (i / (n - 1)) * plotW;
        };

        const line = (data, color, ymin, ymax) => {
            const vals = data.filter((v) => v !== null);
            if (!vals.length) {
                return;
            }
            let lo = ymin;
            let hi = ymax;
            if (lo === undefined || hi === undefined) {
                lo = Math.min(...vals);
                hi = Math.max(...vals);
            }
            if (hi === lo) {
                lo -= 1;
                hi += 1;
            }
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.beginPath();
            let started = false;
            for (let i = 0; i < n; i++) {
                const v = data[i];
                if (v === null) {
                    continue;
                }
                const x = xAt(i);
                const y = pad.t + ((hi - v) / (hi - lo)) * plotH;
                if (!started) {
                    ctx.moveTo(x, y);
                    started = true;
                } else {
                    ctx.lineTo(x, y);
                }
            }
            ctx.stroke();
        };

        ctx.strokeStyle = '#e9ecef';
        ctx.lineWidth = 1;
        for (let g = 0; g <= 4; g++) {
            const gy = pad.t + (g / 4) * plotH;
            ctx.beginPath();
            ctx.moveTo(pad.l, gy);
            ctx.lineTo(pad.l + plotW, gy);
            ctx.stroke();
        }

        if (hasAltOrGs) {
            line(altData, 'rgb(32, 107, 196)');
            line(gsData, 'rgb(247, 103, 7)');
            ctx.fillStyle = '#6c757d';
            ctx.font = '11px system-ui, sans-serif';
            ctx.fillText('Altitude (blue) · Speed (orange)', pad.l, cssH - 8);
        } else {
            line(latData, 'rgb(32, 107, 196)');
            ctx.fillStyle = '#6c757d';
            ctx.font = '11px system-ui, sans-serif';
            ctx.fillText('Latitude (°N)', pad.l, cssH - 8);
        }
    }

    formatChartAxisTime(timeString) {
        if (!timeString) {
            return '—';
        }
        const date = new Date(timeString);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZone: 'UTC',
            hour12: false,
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

    _flightListItemHtml(flight) {
        return `
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
        `;
    }

    updateUpcomingFlights() {
        const upcomingContainer = document.getElementById('upcoming-flights');
        if (!upcomingContainer) return;

        const all = this.upcomingFlights || [];
        const upcoming = all.filter((f) => !f.is_past);
        const past = all.filter((f) => f.is_past);

        if (all.length === 0) {
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

        const pastBlock =
            past.length > 0
                ? `
            <div class="card card-sm mb-3">
                <div class="card-header">
                    <strong>Recent flights</strong>
                    <span class="badge bg-secondary ms-2">${past.length}</span>
                </div>
                <div class="card-body">
                    <div class="list-group list-group-flush">
                        ${past.map((f) => this._flightListItemHtml(f)).join('')}
                    </div>
                </div>
            </div>
        `
                : '';

        const upcomingBlock =
            upcoming.length > 0
                ? `
            <div class="card card-sm">
                <div class="card-header">
                    <strong>Upcoming flights</strong>
                    <span class="badge bg-info ms-2">${upcoming.length}</span>
                </div>
                <div class="card-body">
                    <div class="list-group list-group-flush">
                        ${upcoming.map((f) => this._flightListItemHtml(f)).join('')}
                    </div>
                </div>
            </div>
        `
                : '';

        upcomingContainer.innerHTML =
            pastBlock +
            upcomingBlock +
            (past.length > 0 && upcoming.length === 0
                ? `<p class="text-muted small mb-0">No future scheduled flights in the feed.</p>`
                : '');
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

    updateOceanicReport() {
        const card = document.getElementById('oceanic-report-card');
        const body = document.getElementById('oceanic-report-body');
        if (!card || !body) {
            return;
        }
        const oceanic = this.flightData?.oceanic_report;
        if (!oceanic) {
            card.classList.add('d-none');
            body.innerHTML = '';
            return;
        }

        const rvsm = oceanic.rvsm_data || {};
        const boolTag = (raw) => {
            if (raw === true || String(raw).toLowerCase() === 'true') return 'Yes';
            if (raw === false || String(raw).toLowerCase() === 'false') return 'No';
            return 'Unknown';
        };
        const fmt = (v) => (v !== null && v !== undefined && v !== '' ? v : '—');
        const lat =
            oceanic.latitude !== null && oceanic.latitude !== undefined
                ? Number(oceanic.latitude).toFixed(4)
                : '—';
        const lon =
            oceanic.longitude !== null && oceanic.longitude !== undefined
                ? Number(oceanic.longitude).toFixed(4)
                : '—';

        body.innerHTML = `
            <div class="small text-secondary mb-2">
                Reported ${fmt(oceanic.reported_at)} · Received ${fmt(oceanic.created_at)}
            </div>
            <div class="row g-2 small">
                <div class="col-6"><span class="text-secondary">Position</span><div class="fw-semibold">${lat}, ${lon}</div></div>
                <div class="col-6"><span class="text-secondary">Speed</span><div class="fw-semibold">${fmt(oceanic.speed)}</div></div>
                <div class="col-6"><span class="text-secondary">Altitude</span><div class="fw-semibold">${fmt(oceanic.altitude)}</div></div>
                <div class="col-6"><span class="text-secondary">ETA (est)</span><div class="fw-semibold">${fmt(oceanic.eta_estimated)}</div></div>
                <div class="col-6"><span class="text-secondary">Facility</span><div class="fw-semibold">${fmt(oceanic.source_facility)}</div></div>
                <div class="col-6"><span class="text-secondary">Flight Ref</span><div class="fw-semibold">${fmt(oceanic.flight_reference)}</div></div>
            </div>
            <hr class="my-2"/>
            <div class="small fw-semibold mb-1">RVSM</div>
            <div class="small">
                Equipped: <strong>${boolTag(rvsm.equipped)}</strong> ·
                Current: <strong>${boolTag(rvsm.current_compliance)}</strong> ·
                Future: <strong>${boolTag(rvsm.future_compliance)}</strong>
            </div>
        `;
        card.classList.remove('d-none');
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
                item.href = `?aircraft_id=${encodeURIComponent(this.aircraftId)}&date=${encodeURIComponent(flight.date)}`;
                item.textContent = `${flight.route} · ${flight.date}`;
                container.appendChild(item);
            });
            
        } catch (error) {
            console.error('Error loading recent flights:', error);
        }
    }

    renderMap() {
        if (!this.map || !this.flightData) return;

        const plannedRoute = this.flightData.planned_route || [];
        const trackPoints = this.flightData.track || [];
        const hasPlannedLine = plannedRoute.length >= 2;
        const hasTrackPts = trackPoints.length > 0;
        if (!hasPlannedLine && !hasTrackPts) return;

        try {
            if (this.mapOverlayGroup) {
                this.mapOverlayGroup.clearLayers();
            }

            const legend = document.getElementById('map-legend');
            const legPlanned = document.getElementById('legend-planned');
            const legTrack = document.getElementById('legend-track');
            if (legend) {
                legend.classList.add('d-none');
                if (legPlanned) legPlanned.classList.add('d-none');
                if (legTrack) legTrack.classList.add('d-none');
            }

            const plannedLatLngs = plannedRoute.filter(
                ll =>
                    Array.isArray(ll) &&
                    ll.length === 2 &&
                    Number.isFinite(Number(ll[0])) &&
                    Number.isFinite(Number(ll[1]))
            ).map(ll => [Number(ll[0]), Number(ll[1])]);

            const trackSorted = [...trackPoints].sort(
                (a, b) =>
                    new Date(a.time || 0).getTime() - new Date(b.time || 0).getTime()
            );
            const trackLatLngs = trackSorted
                .filter(
                    point =>
                        point.latitude != null &&
                        point.longitude != null &&
                        !Number.isNaN(Number(point.latitude)) &&
                        !Number.isNaN(Number(point.longitude))
                )
                .map(point => [Number(point.latitude), Number(point.longitude)]);

            const boundsLayers = [];
            const overlayTarget = this.mapOverlayGroup || this.map;

            if (plannedLatLngs.length >= 2) {
                const plannedLine = L.polyline(plannedLatLngs, {
                    color: '#94a3b8',
                    weight: 3,
                    opacity: 0.5,
                    dashArray: '4, 6',
                    lineCap: 'round',
                    lineJoin: 'round',
                }).addTo(overlayTarget);
                boundsLayers.push(plannedLine);
                if (legend) {
                    legend.classList.remove('d-none');
                    if (legPlanned) legPlanned.classList.remove('d-none');
                }
            }

            if (trackLatLngs.length >= 2) {
                const trackLine = L.polyline(trackLatLngs, {
                    color: '#0d6efd',
                    weight: 4,
                    opacity: 0.92,
                    lineCap: 'round',
                    lineJoin: 'round',
                }).addTo(overlayTarget);
                trackLine.bringToFront();
                boundsLayers.push(trackLine);
                if (legend) {
                    legend.classList.remove('d-none');
                    if (legTrack) legTrack.classList.remove('d-none');
                }

                const n = trackLatLngs.length;
                const endBearing = flightDetailInitialBearingDeg(
                    trackLatLngs[n - 2][0],
                    trackLatLngs[n - 2][1],
                    trackLatLngs[n - 1][0],
                    trackLatLngs[n - 1][1]
                );

                const mEnd = L.marker(trackLatLngs[n - 1], {
                    icon: flightDetailAircraftDivIcon(endBearing),
                }).addTo(overlayTarget);
                boundsLayers.push(mEnd);
            } else if (trackLatLngs.length === 1) {
                const m = L.marker(trackLatLngs[0], {
                    icon: flightDetailAircraftDivIcon(0),
                }).addTo(overlayTarget);
                boundsLayers.push(m);
                if (legend) {
                    legend.classList.remove('d-none');
                    if (legTrack) legTrack.classList.remove('d-none');
                }
            }

            if (boundsLayers.length > 0) {
                const group = L.featureGroup(boundsLayers);
                if (!this._mapFitBoundsOnce) {
                    this.map.fitBounds(group.getBounds(), {
                        padding: [24, 24],
                        maxZoom: 12,
                    });
                    this._mapFitBoundsOnce = true;
                }
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

        window.addEventListener('resize', () => {
            if (this.trackProfileChart) {
                this.trackProfileChart.resize();
            }
        });

        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.aircraftId && this.flightData) {
                this.pollLiveTrack();
            }
        });

        window.addEventListener('beforeunload', () => {
            if (this._liveTrackTimer) {
                clearInterval(this._liveTrackTimer);
                this._liveTrackTimer = null;
            }
        });
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
            this.normalizeAltitudeFeet(point.altitude) ?? '',
            point.ground_speed ?? point.speed ?? '',
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
