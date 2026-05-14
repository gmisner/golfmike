from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.sqlalchemy.upcoming_flights import UpcomingFlightDBModel
from utils.logger import main_logger as logger
from datetime import datetime, timezone


class UpcomingFlightStorer:
    """Stores upcoming flight plan data to the database"""
    
    def __init__(self):
        self.logger = logger
    
    def store_flight_plan(self, flight_plan_data: dict, session: Session) -> bool:
        """
        Store or update flight plan data in the database
        
        Args:
            flight_plan_data: Dictionary containing flight plan information
            session: SQLAlchemy database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if flight plan already exists (by GUFI or aircraft_id + departure_time)
            existing_flight = None
            
            if flight_plan_data.get('gufi'):
                existing_flight = session.query(UpcomingFlightDBModel).filter(
                    UpcomingFlightDBModel.gufi == flight_plan_data['gufi']
                ).first()
            
            if not existing_flight and flight_plan_data.get('aircraft_id') and flight_plan_data.get('departure_time'):
                existing_flight = session.query(UpcomingFlightDBModel).filter(
                    UpcomingFlightDBModel.aircraft_id == flight_plan_data['aircraft_id'],
                    UpcomingFlightDBModel.departure_time == flight_plan_data['departure_time']
                ).first()
            
            if existing_flight:
                # Update existing flight plan
                self.logger.info(f"Updating existing flight plan: {flight_plan_data.get('aircraft_id')}")
                
                # Update fields
                for key, value in flight_plan_data.items():
                    if hasattr(existing_flight, key) and value is not None:
                        setattr(existing_flight, key, value)
                
                existing_flight.updated_at = datetime.now(timezone.utc)
                
            else:
                # Create new flight plan
                self.logger.info(f"Creating new flight plan: {flight_plan_data.get('aircraft_id')}")
                
                new_flight = UpcomingFlightDBModel(**flight_plan_data)
                session.add(new_flight)
            
            session.commit()
            self.logger.info(f"Successfully stored flight plan for aircraft: {flight_plan_data.get('aircraft_id')}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error storing flight plan: {e}")
            return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error storing flight plan: {e}", exc_info=True)
            return False
    
    def get_upcoming_flights_for_aircraft(self, aircraft_id: str, session: Session, limit: int = 10) -> list:
        """
        Get upcoming flights for a specific aircraft
        
        Args:
            aircraft_id: Aircraft identifier
            session: SQLAlchemy database session
            limit: Maximum number of flights to return
            
        Returns:
            List of upcoming flight records
        """
        try:
            flights = session.query(UpcomingFlightDBModel).filter(
                UpcomingFlightDBModel.aircraft_id == aircraft_id.upper(),
                UpcomingFlightDBModel.departure_time > datetime.now(timezone.utc),
                UpcomingFlightDBModel.status.in_(['PLANNED', 'ACTIVE'])
            ).order_by(UpcomingFlightDBModel.departure_time.asc()).limit(limit).all()
            
            return flights
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting upcoming flights: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error getting upcoming flights: {e}", exc_info=True)
            return []
    
    def get_upcoming_flights_by_route(self, departure_airport: str, arrival_airport: str, 
                                    session: Session, limit: int = 20) -> list:
        """
        Get upcoming flights by route
        
        Args:
            departure_airport: Departure airport code
            arrival_airport: Arrival airport code
            session: SQLAlchemy database session
            limit: Maximum number of flights to return
            
        Returns:
            List of upcoming flight records
        """
        try:
            flights = session.query(UpcomingFlightDBModel).filter(
                UpcomingFlightDBModel.departure_airport == departure_airport.upper(),
                UpcomingFlightDBModel.arrival_airport == arrival_airport.upper(),
                UpcomingFlightDBModel.departure_time > datetime.now(timezone.utc),
                UpcomingFlightDBModel.status.in_(['PLANNED', 'ACTIVE'])
            ).order_by(UpcomingFlightDBModel.departure_time.asc()).limit(limit).all()
            
            return flights
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting flights by route: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error getting flights by route: {e}", exc_info=True)
            return []
    
    def update_flight_status(self, gufi: str, new_status: str, session: Session) -> bool:
        """
        Update flight status
        
        Args:
            gufi: Global Unique Flight Identifier
            new_status: New status (PLANNED, ACTIVE, COMPLETED, CANCELLED)
            session: SQLAlchemy database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            flight = session.query(UpcomingFlightDBModel).filter(
                UpcomingFlightDBModel.gufi == gufi
            ).first()
            
            if flight:
                flight.status = new_status.upper()
                flight.updated_at = datetime.now(timezone.utc)
                session.commit()
                self.logger.info(f"Updated flight status for GUFI {gufi} to {new_status}")
                return True
            else:
                self.logger.warning(f"Flight with GUFI {gufi} not found")
                return False
                
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error updating flight status: {e}")
            return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error updating flight status: {e}", exc_info=True)
            return False

