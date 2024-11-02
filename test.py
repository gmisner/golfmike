from db_config import SessionLocal
from models.sqlalchemy import AircraftDBModel, FlightSectorsDBModel


session = SessionLocal()
new_aircraft = AircraftDBModel(aircraft_id="N12348")
session.add(new_aircraft)
session.commit()  # Ensure data is committed to the database
