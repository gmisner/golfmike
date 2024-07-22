from sqlalchemy import insert, exc
from models.sqlalchemy.status import StatusDBModel
from db_config import SessionLocal
from utils.logger import main_logger as logger

import json


def store_status(status):
    """
    store_status _summary_

    Args:
        status (_type_): _description_
    """
    try:
        with SessionLocal() as session:
            # Convert the artcc list of dictionaries to a JSON string
            status_dict = status.dict()
            status_dict["artcc"] = json.dumps(status_dict["artcc"])

            stmt = insert(StatusDBModel.__table__).values(**status_dict)
            session.execute(stmt)
            session.commit()
            logger.info("Successfully stored status data.")
    except exc.IntegrityError as e:
        logger.error(f"Integrity error storing status: {e}", exc_info=True)
        session.rollback()
    except Exception as e:
        logger.error(f"Error storing status: {e}", exc_info=True)
        session.rollback()
