from sqlalchemy.orm import Session
from models.sqlalchemy.track import TrackDBModel
from db_config import SessionLocal
from utils.logger import main_logger as logger


def store_track(track):
    """
    store_track _summary_

    Args:
        track (_type_): _description_
    """
    try:
        with SessionLocal() as session:
            track_data = track.dict(exclude_unset=True)  # Exclude unset attributes

            stmt = insert(TrackDBModel.__table__).values(**track_data)
            session.execute(stmt)
            session.commit()

            logger.info("Successfully stored track data.")
    except exc.IntegrityError as e:
        logger.error(f"Integrity error storing track: {e}", exc_info=True)
        session.rollback()
    except Exception as e:
        logger.error(f"Error storing track: {e}", exc_info=True)
        session.rollback()
