from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.sqlalchemy import TrackInformationDBModel, AircraftDBModel
from models.sqlalchemy.flight_events import TrackUpdatesDBModel
from models.sqlalchemy.flight_plan import FlightPlanDBModel
from utils.logger import main_logger as logger
from db_config import SessionLocal
from services.notification_service import send_flight_event
from services.route_overlay_service import process_track_point


def _parse_altitude_ft(alt_str) -> int:
    """Convert a filed altitude value to feet (handles FL### and raw integers)."""
    if alt_str is None:
        return None
    try:
        s = str(alt_str).upper().strip()
        if s.startswith("FL"):
            return int(s[2:]) * 100
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _infer_event_type(diversion_indicator, prev_status: str, has_position: bool) -> str:
    if diversion_indicator and str(diversion_indicator).upper() not in ("", "NONE", "N"):
        return "DIVERTED"
    if has_position:
        return "IN_FLIGHT"
    return None


def store_track_information(
    track_data_list: List[TrackInformationDBModel],
    session=None,
    batch_size: int = 100,
):
    logger.debug("Starting store_track_information function")

    created_locally = False
    if session is None:
        session = SessionLocal()
        created_locally = True
    elif not isinstance(session, Session):
        logger.error(f"Invalid session type: {type(session)}")
        raise TypeError("Invalid session type. Expected SQLAlchemy Session.")

    new_aircrafts = []
    new_tracks = []
    new_track_updates = []

    try:
        for track_data in track_data_list:
            aircraft_id = track_data.aircraft_id
            gufi = track_data.gufi

            # ── Ensure aircraft record exists ─────────────────────────────────
            aircraft = (
                session.query(AircraftDBModel)
                .filter_by(aircraft_id=aircraft_id)
                .first()
            )
            if not aircraft:
                aircraft = AircraftDBModel(
                    aircraft_id=aircraft_id,
                    airline=getattr(track_data, "airline", None),
                    aircraft_category=getattr(track_data, "aircraft_category", None),
                    user_category=getattr(track_data, "user_category", None),
                )
                new_aircrafts.append(aircraft)

            # ── Write to legacy track_information table (keeps existing API) ──
            track = TrackInformationDBModel(
                aircraft_id=aircraft_id,
                gufi=gufi,
                speed=track_data.speed,
                altitude=track_data.altitude,
                latitude=track_data.latitude,
                longitude=track_data.longitude,
                time_at_position=track_data.time_at_position,
                departure_airport=track_data.departure_airport,
                arrival_airport=track_data.arrival_airport,
                etd=track_data.etd,
                eta=track_data.eta,
                diversion_indicator=track_data.diversion_indicator,
                rvsm_data=track_data.rvsm_data,
                next_position=track_data.next_position,
                fixes=track_data.fixes,
                waypoints=track_data.waypoints,
                sectors=track_data.sectors,
                route_of_flight=track_data.route_of_flight,
            )
            new_tracks.append(track)

            # ── Write to normalised track_updates table ───────────────────────
            lat = track_data.latitude
            lon = track_data.longitude
            has_position = lat is not None and lon is not None

            if has_position:
                try:
                    lat_f = float(lat)
                    lon_f = float(lon)
                except (TypeError, ValueError):
                    lat_f = lon_f = None
                    has_position = False

            if has_position:
                ts_raw = track_data.time_at_position
                if isinstance(ts_raw, str):
                    try:
                        ts = datetime.fromisoformat(ts_raw)
                    except ValueError:
                        ts = datetime.now(timezone.utc)
                elif isinstance(ts_raw, datetime):
                    ts = ts_raw
                else:
                    ts = datetime.now(timezone.utc)

                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)

                new_track_updates.append(
                    TrackUpdatesDBModel(
                        aircraft_id=aircraft_id,
                        gufi=gufi,
                        latitude=str(lat_f),
                        longitude=str(lon_f),
                        altitude=track_data.altitude,
                        speed=track_data.speed,
                        time_at_position=ts,
                    )
                )

            # ── Commit batch if full ──────────────────────────────────────────
            if len(new_tracks) >= batch_size:
                _flush(session, new_aircrafts, new_tracks, new_track_updates)
                new_aircrafts.clear()
                new_tracks.clear()
                new_track_updates.clear()

        # Final flush
        if new_aircrafts or new_tracks:
            _flush(session, new_aircrafts, new_tracks, new_track_updates)

        # ── Post-commit: route overlay + event detection per position ─────────
        for track_data in track_data_list:
            if not (track_data.latitude and track_data.longitude):
                continue
            try:
                lat_f = float(track_data.latitude)
                lon_f = float(track_data.longitude)
            except (TypeError, ValueError):
                continue

            gufi = track_data.gufi
            aircraft_id = track_data.aircraft_id

            ts_raw = track_data.time_at_position
            if isinstance(ts_raw, str):
                try:
                    ts = datetime.fromisoformat(ts_raw)
                except ValueError:
                    ts = datetime.now(timezone.utc)
            elif isinstance(ts_raw, datetime):
                ts = ts_raw
            else:
                ts = datetime.now(timezone.utc)

            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            # Look up filed altitude from flight plan for deviation calc
            filed_altitude = None
            if gufi:
                fp = session.query(FlightPlanDBModel).filter_by(gufi=gufi).first()
                if fp:
                    filed_altitude = _parse_altitude_ft(
                        fp.requestedAlt_09a or fp.assignedAlt_08a
                    )

            event_data = {
                "aircraft_id": aircraft_id,
                "gufi": gufi,
                "departure_airport": track_data.departure_airport or "",
                "arrival_airport": track_data.arrival_airport or "",
            }

            process_track_point(
                gufi=gufi,
                aircraft_id=aircraft_id,
                latitude=lat_f,
                longitude=lon_f,
                altitude=track_data.altitude,
                speed=track_data.speed,
                timestamp=ts,
                filed_altitude=filed_altitude,
                event_data=event_data,
                session=session,
            )

            # ── Detect DEPARTED / DIVERTED / ARRIVED events ───────────────────
            diversion = track_data.diversion_indicator
            event_type = _infer_event_type(diversion, "", True)
            if event_type:
                send_flight_event(event_type, event_data, session)

    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError in track storer: {e}")
        session.rollback()
    except Exception as e:
        logger.error(f"Unexpected error in track storer: {e}")
        session.rollback()
    finally:
        if created_locally:
            session.close()

    logger.success("All track information stored successfully.")


def _flush(session, aircrafts, tracks, track_updates):
    session.add_all(aircrafts)
    session.add_all(tracks)
    session.add_all(track_updates)
    try:
        session.commit()
        logger.info(
            f"Batch committed: {len(aircrafts)} aircraft, {len(tracks)} tracks, "
            f"{len(track_updates)} track_updates"
        )
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Error committing track batch: {e}", exc_info=True)
