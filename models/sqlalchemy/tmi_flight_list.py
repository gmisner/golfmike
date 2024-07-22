from sqlalchemy import Column, String, Integer, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TmiFlightListDBModel(Base):
    __tablename__ = "tmi_flight_list"
    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String, unique=True, index=True)
    update_time = Column(DateTime)
    fca_id = Column(String)
    fca_name = Column(String)
    last_update = Column(DateTime)
    bentry_tm = Column(DateTime)
    create_tm = Column(DateTime)
    eentry_tm = Column(DateTime)
    entry_tm = Column(DateTime)
    exit_tm = Column(DateTime)
    extended_exit_tm = Column(DateTime)
    ientry_tm = Column(DateTime)
    oentry_tm = Column(DateTime)
    entry_lat = Column(Float)
    entry_lon = Column(Float)
    entry_heading = Column(Float)
    exit_ind = Column(String)
    additional_data = Column(JSON)  # for any additional data not mapped
