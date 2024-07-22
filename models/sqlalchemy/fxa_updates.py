from sqlalchemy import Column, String, Integer, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from db_config import Base


class FxaUpdatesDBModel(Base):
    __tablename__ = "fxa_updates"
    __table_args__ = {"extend_existing": True}  # Ensure this is present

    id = Column(Integer, primary_key=True, autoincrement=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"))
    update_time = Column(DateTime)
    fcaId = Column(String)
    fcaName = Column(String)
    lastUpdate = Column(DateTime)
    bentryTm = Column(DateTime)
    createTm = Column(DateTime)
    eentryTm = Column(DateTime)
    entryTm = Column(DateTime)
    exitTm = Column(DateTime)
    extendedExitTm = Column(DateTime)
    ientryTm = Column(DateTime)
    oentryTm = Column(DateTime)
    entryLat = Column(Float)
    entryLon = Column(Float)
    entryHeading = Column(Integer)
    exitInd = Column(String)
    aircraft = relationship("AircraftDBModel", back_populates="fxa_updates")
