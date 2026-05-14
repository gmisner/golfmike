"""
Converter to transform TrackInformationModel data to track_updates format
"""

from typing import List, Dict, Any, Optional
from models.pydantic.track_information import TrackInformationModel
from storers.flight_hub import upsert_flight_operational_fields
from storers.track_updates_storer import store_track_updates
from storers.swim_flight_alerts_storer import store_swim_rows_as_flight_alerts
from utils.logger import main_logger as logger


def _route_and_metadata_snapshot(m: TrackInformationModel) -> Dict[str, Any]:
    """Fields stored in track_updates.track_data (JSONB) for TFMS / TFM track messages."""
    return {
        "airline": m.airline,
        "aircraft_category": m.aircraft_category,
        "user_category": m.user_category,
        "departure_airport": m.departure_airport,
        "arrival_airport": m.arrival_airport,
        "igtd": m.igtd,
        "flight_ref": m.flight_ref,
        "source_time_stamp": m.source_time_stamp,
        "computer_facility": m.computer_facility,
        "computer_id_number": m.computer_id_number,
        "etd": m.etd,
        "eta": m.eta,
        "diversion_indicator": m.diversion_indicator,
        "rvsm_data": m.rvsm_data,
        "next_position": m.next_position,
        "fixes": m.fixes,
        "waypoints": m.waypoints,
        "sectors": m.sectors,
        "sector_details": m.sector_details,
        "airways": m.airways,
        "centers": m.centers,
        "route_of_flight": m.route_of_flight,
        "star_route_name": m.star_route_name,
        "star_route_type": m.star_route_type,
        "star_transition_fix": m.star_transition_fix,
        "route_arrival_fix_name": m.route_arrival_fix_name,
        "route_arrival_fix_time": m.route_arrival_fix_time,
        "ncsm_track_data": m.track_data,
    }


def _drop_none_values(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def convert_and_store_track_updates(
    track_data_list: List[TrackInformationModel], session=None
) -> None:
    """
    Convert TrackInformationModel objects to track_updates format and store them

    Args:
        track_data_list: List of TrackInformationModel objects
        session: Database session (optional)
    """
    converted_data = []
    non_pos_alert_rows = []

    for track_data in track_data_list:
        # Extract heading if available (might be in next_position or calculated)
        heading: Optional[int] = None
        next_pos = track_data.next_position
        if next_pos:
            # Try to calculate heading from current and next position
            try:
                current_lat = (
                    float(track_data.latitude) if track_data.latitude else None
                )
                current_lon = (
                    float(track_data.longitude) if track_data.longitude else None
                )
                next_lat = float(next_pos.get("latitude", 0)) if next_pos else None
                next_lon = float(next_pos.get("longitude", 0)) if next_pos else None

                if current_lat and current_lon and next_lat and next_lon:
                    # Calculate bearing
                    import math

                    lat1_rad = math.radians(current_lat)
                    lat2_rad = math.radians(next_lat)
                    delta_lon = math.radians(next_lon - current_lon)

                    y = math.sin(delta_lon) * math.cos(lat2_rad)
                    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(
                        lat1_rad
                    ) * math.cos(lat2_rad) * math.cos(delta_lon)

                    heading = int((math.degrees(math.atan2(y, x)) + 360) % 360)
            except (ValueError, TypeError, AttributeError):
                pass

        snapshot = _drop_none_values(_route_and_metadata_snapshot(track_data))
        nas_meta = (snapshot.get("ncsm_track_data") or {}).get("nas_message_collection")
        if isinstance(nas_meta, dict) and track_data.gufi and track_data.aircraft_id:
            upsert_flight_operational_fields(
                session=session,
                gufi=track_data.gufi,
                aircraft_id=track_data.aircraft_id,
                fields={
                    "source_timestamp": nas_meta.get("source_timestamp"),
                    "route_text": nas_meta.get("route_text"),
                    "current_beacon_code": nas_meta.get("current_beacon_code"),
                    "fdps_flight_status": nas_meta.get("flight_status"),
                    "coordination_time": nas_meta.get("coordination_time"),
                    "coordination_fix": nas_meta.get("coordination_fix"),
                    "coordination_distance_nm": nas_meta.get(
                        "coordination_distance_nm"
                    ),
                    "coordination_radial_deg": nas_meta.get("coordination_radial_deg"),
                },
            )

        converted = {
            "aircraft_id": track_data.aircraft_id,
            "gufi": track_data.gufi,
            "latitude": track_data.latitude,
            "longitude": track_data.longitude,
            "altitude": track_data.altitude if track_data.altitude else None,
            "speed": track_data.speed if track_data.speed else None,
            "heading": heading,
            "time_at_position": track_data.time_at_position,
            "source_facility": track_data.source_facility,
            "track_data": snapshot if snapshot else None,
        }

        if track_data.latitude and track_data.longitude:
            converted_data.append(converted)
        else:
            nas_meta = (snapshot.get("ncsm_track_data") or {}).get(
                "nas_message_collection", {}
            )
            non_pos_alert_rows.append(
                {
                    "aircraft_id": track_data.aircraft_id,
                    "gufi": track_data.gufi,
                    "flight_reference": track_data.flight_ref,
                    "source_time_stamp": track_data.source_time_stamp,
                    "source_facility": track_data.source_facility,
                    "departure_airport": track_data.departure_airport,
                    "arrival_airport": track_data.arrival_airport,
                    "airline": track_data.airline,
                    "speed": track_data.speed,
                    "altitude": track_data.altitude,
                    "fdps_flight_status": nas_meta.get("flight_status"),
                    "current_beacon_code": nas_meta.get("current_beacon_code"),
                    "coordination_time": nas_meta.get("coordination_time"),
                    "coordination_fix": nas_meta.get("coordination_fix"),
                    "coordination_distance_nm": nas_meta.get(
                        "coordination_distance_nm"
                    ),
                    "coordination_radial_deg": nas_meta.get("coordination_radial_deg"),
                    "route_text": nas_meta.get("route_text"),
                    "track_data": snapshot if snapshot else None,
                }
            )

    # Store using track_updates_storer (new table only)
    if converted_data:
        store_track_updates(converted_data, session=session)
        logger.info(
            f"Stored {len(converted_data)} track updates to track_updates table"
        )
    if non_pos_alert_rows:
        store_swim_rows_as_flight_alerts(
            non_pos_alert_rows,
            "NAS_MessageCollection",
            session=session,
        )
        logger.info(
            f"Stored {len(non_pos_alert_rows)} NAS non-position updates to flight_alerts table"
        )
