from sqlalchemy.orm import Session
from models.sqlalchemy.fltd_message import FltdMessageDBModel
from db_config import SessionLocal
from utils.logger import main_logger as logger


def store_fltd_message(message):
    """
    store_fltd_message _summary_

    Args:
        message (_type_): _description_
    """
    try:
        with SessionLocal() as session:
            message_data = message.dict()
            stmt = insert(FltdMessageDBModel.__table__).values(**message_data)
            update_dict = {c.name: c for c in stmt.excluded}
            update_stmt = stmt.on_conflict_do_update(
                index_elements=["id"], set_=update_dict
            )
            session.execute(update_stmt)
            session.commit()

            logger.info("Successfully stored fltdMessage data.")
    except exc.IntegrityError as e:
        logger.error(f"Integrity error storing fltdMessage: {e}", exc_info=True)
        session.rollback()
    except Exception as e:
        logger.error(f"Error storing fltdMessage: {e}", exc_info=True)
        session.rollback()
