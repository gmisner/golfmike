# storers/track_information_storer.py
from db_config import SessionLocal
from typing import List
from models.pydantic.track_information import TrackInformationModel
from models.sqlalchemy.track_information import TrackInformationDBModel
from models.sqlalchemy.aircraft import AircraftDBModel
from utils.logger import main_logger as logger
from sqlalchemy.exc import SQLAlchemyError


def store_track_information(
    track_data_list: List[TrackInformationModel],
    batch_size: int = 100,
):
    session = SessionLocal()
    try:
        # Create a dictionary to cache aircraft records for updates
        aircraft_cache = {}
        new_aircrafts = []
        new_track_records = []

        for track_data in track_data_list:  # Iterate over the list
            try:
                # Fetch or cache the AircraftDBModel
                aircraft = aircraft_cache.get(track_data.aircraft_id)
                if not aircraft:
                    aircraft = (
                        session.query(AircraftDBModel)
                        .filter_by(aircraft_id=track_data.aircraft_id)
                        .first()
                    )
                    if aircraft:
                        aircraft_cache[track_data.aircraft_id] = aircraft
                    else:
                        # If aircraft doesn't exist, prepare to add a new one
                        aircraft = AircraftDBModel(
                            aircraft_id=track_data.aircraft_id,
                            airline=track_data.airline,
                            aircraft_category=track_data.aircraft_category,
                            user_category=track_data.user_category,
                        )
                        new_aircrafts.append(aircraft)
                        aircraft_cache[track_data.aircraft_id] = aircraft

                # Update existing aircraft fields
                if aircraft:
                    aircraft.airline = track_data.airline
                    aircraft.aircraft_category = track_data.aircraft_category
                    aircraft.user_category = track_data.user_category

                # Prepare to add new track information record
                track_record = TrackInformationDBModel(
                    aircraft_id=track_data.aircraft_id,
                    gufi=track_data.gufi,
                    speed=track_data.speed,
                    altitude=track_data.altitude,
                    latitude=track_data.latitude,
                    longitude=track_data.longitude,
                    time_at_position=track_data.time_at_position,
                    departure_airport=track_data.departure_airport,
                    arrival_airport=track_data.arrival_airport,
                )
                new_track_records.append(track_record)

                if (
                    len(new_aircrafts) >= batch_size
                    or len(new_track_records) >= batch_size
                ):
                    # Bulk insert new aircraft and track information records
                    session.bulk_save_objects(new_aircrafts)
                    session.bulk_save_objects(new_track_records)
                    session.commit()
                    logger.debug(
                        f"Committed batch of {len(new_aircrafts)} aircraft and {len(new_track_records)} track records"
                    )

                    # Clear the lists after commit
                    new_aircrafts.clear()
                    new_track_records.clear()

            except SQLAlchemyError as e:
                session.rollback()
                logger.error(
                    f"Error processing track data: {track_data.aircraft_id}, Error: {e}",
                    exc_info=True,
                )

        # Commit any remaining records in the batch
        if new_aircrafts or new_track_records:
            session.bulk_save_objects(new_aircrafts)
            session.bulk_save_objects(new_track_records)
            session.commit()
            logger.debug(
                f"Committed final batch of {len(new_aircrafts)} aircraft and {len(new_track_records)} track records"
            )

        logger.success("All track information stored successfully")

    except Exception as e:
        session.rollback()
        logger.error(f"Error storing track information: {e}", exc_info=True)
    finally:
        session.close()
