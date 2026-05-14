from sqlalchemy import insert, exc
from db_config import SessionLocal
from models.sqlalchemy.flight_plan import FlightPlanDBModel
from models.sqlalchemy.aircraft import AircraftDBModel
from models.pydantic.flight_plan import FlightPlanModel
from storers.flight_hub import ensure_flight_hub_row
from utils.logger import main_logger as logger
from services.route_decoder import decode_route
from services.route_overlay_service import store_planned_waypoints
from services.notification_service import send_flight_event


def store_flight_plan(flight_plan: FlightPlanModel):
    """
    Store a filed flight plan, decode its route into planned waypoints,
    and fire a FILED notification to all matching subscribers.
    """
    try:
        with SessionLocal() as session:
            # Store or update aircraft record
            aircraft_data = {
                "aircraft_id": flight_plan.flightId_02a,
                "gufi": flight_plan.eramGufi_316a,
                "flight_reference": flight_plan.flightReference,
                "status": flight_plan.status,
            }
            stmt = insert(AircraftDBModel).values(**aircraft_data)
            update_dict = {c.name: c for c in stmt.excluded}
            update_stmt = stmt.on_conflict_do_update(
                index_elements=["aircraft_id"], set_=update_dict
            )
            session.execute(update_stmt)

            if flight_plan.eramGufi_316a and flight_plan.flightId_02a:
                ensure_flight_hub_row(
                    session,
                    flight_plan.eramGufi_316a,
                    flight_plan.flightId_02a,
                    current_status="PLANNED",
                )

            # Store flight plan
            flight_plan_data = flight_plan.dict()
            stmt = insert(FlightPlanDBModel).values(**flight_plan_data)
            update_dict = {c.name: c for c in stmt.excluded}
            update_stmt = stmt.on_conflict_do_update(
                index_elements=["id"], set_=update_dict
            )
            session.execute(update_stmt)

            session.commit()
            logger.info("Successfully stored flight plan data.")

        # ── Decode route and persist planned waypoints ────────────────────────
        aircraft_id = flight_plan.flightId_02a or ""
        gufi = flight_plan.eramGufi_316a or ""
        departure = flight_plan.departure_airport or ""
        destination = flight_plan.arrival_airport or ""
        route_str = flight_plan.flightPlanRoute_10a or ""

        if gufi and departure and destination and route_str:
            waypoints = decode_route(route_str, departure, destination)
            with SessionLocal() as session:
                n = store_planned_waypoints(
                    gufi=gufi,
                    aircraft_id=aircraft_id,
                    waypoints=waypoints,
                    session=session,
                    route_source="FILED",
                )
            logger.info(
                f"Decoded {n} planned waypoints for {aircraft_id} ({gufi})"
            )

        # ── Fire FILED notification ────────────────────────────────────────────
        event_data = {
            "aircraft_id": aircraft_id,
            "gufi": gufi,
            "departure_airport": departure,
            "arrival_airport": destination,
            "departure_time": str(flight_plan.igtd or ""),
            "route_text": route_str,
            "aircraft_type": flight_plan.typeOfAircraft_03c or "",
        }
        with SessionLocal() as session:
            send_flight_event("FILED", event_data, session)

    except exc.IntegrityError as e:
        logger.error(f"Integrity error storing flight plan: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error storing flight plan: {e}", exc_info=True)
