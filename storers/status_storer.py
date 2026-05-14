from sqlalchemy import insert, exc
from models.sqlalchemy.status import StatusDBModel
from db_config import SessionLocal
from utils.logger import main_logger as logger

import json


def store_status(status):
    try:
        with SessionLocal() as session:
            try:
                status_dict = status.dict()
                status_dict["artcc"] = json.dumps(status_dict["artcc"])
                stmt = insert(StatusDBModel.__table__).values(**status_dict)
                session.execute(stmt)
                session.commit()
                logger.info("Successfully stored status data.")
            except exc.IntegrityError as e:
                session.rollback()
                logger.error(f"Integrity error storing status: {e}", exc_info=True)
            except Exception as e:
                session.rollback()
                logger.error(f"Error storing status: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Session error in store_status: {e}", exc_info=True)
