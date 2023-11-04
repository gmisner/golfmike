from sqlalchemy import create_engine, Column, String, Integer, Sequence, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

class DeparturePointDB(Base):
    __tablename__ = 'departure_points'
    id = Column(Integer, Sequence('dep_point_id_seq'), primary_key=True)
    airport = Column(String(50))

class ArrivalPointDB(Base):
    __tablename__ = 'arrival_points'
    id = Column(Integer, Sequence('arr_point_id_seq'), primary_key=True)
    airport = Column(String(50))

class FlightDB(Base):
    __tablename__ = 'flights'
    id = Column(Integer, Sequence('flight_id_seq'), primary_key=True)
    aircraftId = Column(String(50))
    gufi = Column(String(50))
    igtd = Column(String(50))
    departure_point_id = Column(Integer, ForeignKey('departure_points.id'))
    arrival_point_id = Column(Integer, ForeignKey('arrival_points.id'))
    departure_point = relationship("DeparturePointDB", back_populates="flights")
    arrival_point = relationship("ArrivalPointDB", back_populates="flights")

DeparturePointDB.flights = relationship("FlightDB", order_by=FlightDB.id, back_populates="departure_point")
ArrivalPointDB.flights = relationship("FlightDB", order_by=FlightDB.id, back_populates="arrival_point")

# ... other SQLAlchemy models for other parts of your XML data 