import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { FlightDetail } from '@/api/flights'

// Fix Leaflet's broken default marker icons when bundled with Vite
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

interface Props {
  flight: FlightDetail
  className?: string
}

export default function FlightMap({ flight, className }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const trackRef = useRef<L.Polyline | null>(null)
  const markerRef = useRef<L.Marker | null>(null)

  // Initialise map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: true,
    })

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map)

    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Update track + marker whenever flight data changes
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    // Build track coords from history
    const trackPoints: L.LatLngTuple[] = (flight.track ?? []).map((p) => [p.lat, p.lon])

    // Current position
    const hasPosition = flight.latitude != null && flight.longitude != null
    if (hasPosition) {
      trackPoints.push([flight.latitude!, flight.longitude!])
    }

    // Draw/update polyline
    if (trackRef.current) {
      trackRef.current.setLatLngs(trackPoints)
    } else if (trackPoints.length > 1) {
      trackRef.current = L.polyline(trackPoints, {
        color: '#38bdf8',
        weight: 2,
        opacity: 0.8,
      }).addTo(map)
    }

    // Position marker
    if (hasPosition) {
      const pos: L.LatLngTuple = [flight.latitude!, flight.longitude!]
      if (markerRef.current) {
        markerRef.current.setLatLng(pos)
      } else {
        const planeIcon = L.divIcon({
          className: '',
          html: `<div style="
            width:28px;height:28px;
            background:#38bdf8;
            border-radius:50%;
            border:2px solid white;
            display:flex;align-items:center;justify-content:center;
            font-size:14px;
            box-shadow:0 2px 8px rgba(0,0,0,.4);
          ">✈</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        })
        markerRef.current = L.marker(pos, { icon: planeIcon })
          .addTo(map)
          .bindTooltip(`${flight.ident}${flight.altitude ? ` · FL${(flight.altitude / 100).toFixed(0)}` : ''}`)
      }
      // Pan to current position
      if (trackPoints.length <= 2) {
        map.setView(pos, 7)
      } else if (trackRef.current) {
        map.fitBounds(trackRef.current.getBounds(), { padding: [40, 40] })
      }
    } else if (trackPoints.length > 1 && trackRef.current) {
      map.fitBounds(trackRef.current.getBounds(), { padding: [40, 40] })
    }
  }, [flight])

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ background: '#1a1a2e' }}
    />
  )
}
