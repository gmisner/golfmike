from sqlalchemy import insert, exc
from db_config import SessionLocal
from models.sqlalchemy.flight_plan import FlightPlanDBModel
from models.sqlalchemy.aircraft import AircraftDBModel
from models.pydantic.flight_plan import FlightPlanModel
from utils.logger import main_logger as logger


def store_flight_plan(flight_plan: FlightPlanModel):
    """
    store_flight_plan _summary_

    Args:
        flight_plan (FlightPlanModel): _description_
    """
    try:
        with SessionLocal() as session:
            # Store or update aircraft data
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
    except exc.IntegrityError as e:
        logger.error(f"Integrity error storing flight plan: {e}", exc_info=True)
        session.rollback()
    except Exception as e:
        logger.error(f"Error storing flight plan: {e}", exc_info=True)
        session.rollback()
