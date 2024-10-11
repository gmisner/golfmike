from db_config import SessionLocal
from models.sqlalchemy import AircraftDBModel, TrackInformationDBModel
from sqlalchemy.exc import SQLAlchemyError
from utils.logger import main_logger as logger
from typing import List


def store_track_information(
    track_data_list: List[TrackInformationDBModel], batch_size: int = 100
):
    try:
        with SessionLocal() as session:
            new_aircrafts = []
            new_tracks = []

            for track_data in track_data_list:
                # Fetch or create aircraft
                aircraft = (
                    session.query(AircraftDBModel)
                    .filter_by(aircraft_id=track_data.aircraft_id)
                    .first()
                )
                if not aircraft:
                    aircraft = AircraftDBModel(
                        aircraft_id=track_data.aircraft_id,
                        airline=track_data.airline,
                        aircraft_category=track_data.aircraft_category,
                        user_category=track_data.user_category,
                    )
                    new_aircrafts.append(aircraft)

                # Create track information entry
                track = TrackInformationDBModel(
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
                new_tracks.append(track)

                if len(new_aircrafts) >= batch_size or len(new_tracks) >= batch_size:
                    session.add_all(new_aircrafts)
                    session.add_all(new_tracks)
                    session.commit()  # Commit the batch
                    logger.info(
                        f"Committed batch of {len(new_aircrafts)} aircraft and {len(new_tracks)} tracks"
                    )
                    new_aircrafts.clear()
                    new_tracks.clear()

            # Commit remaining records
            if new_aircrafts or new_tracks:
                session.add_all(new_aircrafts)
                session.add_all(new_tracks)
                session.commit()
                logger.info(
                    f"Committed final batch of {len(new_aircrafts)} aircraft and {len(new_tracks)} tracks"
                )

            logger.success("All track information stored successfully.")

    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error occurred: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}", exc_info=True)
