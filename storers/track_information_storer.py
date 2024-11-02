from sqlalchemy.orm import Session
from models.sqlalchemy import TrackInformationDBModel, AircraftDBModel
from typing import List
from utils.logger import main_logger as logger
from sqlalchemy.exc import SQLAlchemyError
from db_config import SessionLocal


def store_track_information(
    track_data_list: List[TrackInformationDBModel],
    session=None,
    batch_size: int = 100,
):
    # Start the function and log its initiation
    logger.debug("Starting store_track_information function")

    # Verify session type and create a new session if none is provided
    created_locally = False
    if session is None:
        logger.debug("No session provided, creating a new session")
        session = SessionLocal()
        created_locally = True
    elif not isinstance(session, Session):
        # Log an error if the provided session is not of the correct type
        logger.error(
            f"Invalid session type: {type(session)}. Expected <class 'sqlalchemy.orm.session.Session'>."
        )
        raise TypeError("Invalid session type. Expected SQLAlchemy Session.")

    logger.debug(f"Session type after check: {type(session)}")

    # Lists to hold new aircraft and track information to be added to the database
    new_aircrafts = []
    new_tracks = []

    try:
        # Iterate over each track data object in the provided list
        for track_data in track_data_list:
            logger.debug(f"Processing track data: {track_data}")

            # Retrieve or create aircraft entry
            logger.debug(f"Querying aircraft with ID: {track_data.aircraft_id}")
            aircraft = (
                session.query(AircraftDBModel)
                .filter_by(aircraft_id=track_data.aircraft_id)
                .first()
            )
            logger.debug(f"Query result for aircraft: {aircraft}")

            # If the aircraft does not exist, create a new entry and add it to the batch list
            if not aircraft:
                logger.info(
                    f"Aircraft with ID {track_data.aircraft_id} not found. Creating new aircraft entry."
                )
                aircraft = AircraftDBModel(
                    aircraft_id=track_data.aircraft_id,
                    airline=track_data.airline,
                    aircraft_category=track_data.aircraft_category,
                    user_category=track_data.user_category,
                )
                new_aircrafts.append(aircraft)
                logger.debug(f"New aircraft added to batch: {aircraft}")

            # Create a new track information entry using the current track data
            logger.debug(
                f"Creating track information entry for aircraft ID: {track_data.aircraft_id}"
            )
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
                etd=track_data.etd,  # Estimated time of departure
                eta=track_data.eta,  # Estimated time of arrival
                diversion_indicator=track_data.diversion_indicator,  # Diversion status
                rvsm_data=track_data.rvsm_data,  # RVSM data attributes
                next_position=track_data.next_position,  # Next position
                fixes=track_data.fixes,  # List of fixes
                waypoints=track_data.waypoints,  # List of waypoints
                sectors=track_data.sectors,  # List of sectors
                route_of_flight=track_data.route_of_flight,  # Route of flight
            )
            new_tracks.append(track)
            logger.debug(f"New track added to batch: {track}")

            # Commit the batch if the batch size limit is reached
            if len(new_aircrafts) >= batch_size or len(new_tracks) >= batch_size:
                logger.info(
                    f"Batch size reached. Committing {len(new_aircrafts)} aircraft and {len(new_tracks)} tracks."
                )
                session.add_all(new_aircrafts)  # Add all new aircrafts to the session
                session.add_all(new_tracks)  # Add all new tracks to the session
                try:
                    session.commit()  # Commit the batch to the database
                    logger.info(
                        f"Batch committed successfully: {len(new_aircrafts)} aircraft and {len(new_tracks)} tracks."
                    )
                except SQLAlchemyError as e:
                    # Rollback the session if there is an error during the commit
                    session.rollback()
                    logger.error(f"Error committing batch: {e}", exc_info=True)
                # Clear the lists after attempting to commit
                new_aircrafts.clear()
                new_tracks.clear()
                logger.debug("Batch cleared after commit attempt.")

        # Commit any remaining records that didn't make up a full batch
        if new_aircrafts or new_tracks:
            logger.info(
                f"Committing final batch of {len(new_aircrafts)} aircraft and {len(new_tracks)} tracks."
            )
            session.add_all(new_aircrafts)  # Add remaining new aircrafts to the session
            session.add_all(new_tracks)  # Add remaining new tracks to the session
            try:
                session.commit()  # Commit the final batch to the database
                logger.info(
                    f"Final batch committed successfully: {len(new_aircrafts)} aircraft and {len(new_tracks)} tracks."
                )
            except SQLAlchemyError as e:
                # Rollback the session if there is an error during the commit
                session.rollback()
                logger.error(f"Error committing final batch: {e}", exc_info=True)

    except SQLAlchemyError as e:
        # Log SQLAlchemy-specific errors that occur during processing
        logger.error(f"SQLAlchemyError occurred while processing tracks: {e}")
        session.rollback()

    except Exception as e:
        # Log any unexpected errors that occur during processing
        logger.error(f"Unexpected error: {e}")
        session.rollback()

    finally:
        # Close the session if it was created locally
        if created_locally:
            session.close()
            logger.debug("Session closed.")

    # Log the successful completion of storing all track information
    logger.success("All track information stored successfully.")
    logger.debug("Finished store_track_information function")
