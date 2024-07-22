# models/sqlalchemy/__init__.py
from models.sqlalchemy.aircraft import AircraftDBModel
from models.sqlalchemy.flight_plan import FlightPlanDBModel
from models.sqlalchemy.tmi_updates import TmiUpdatesDBModel
from models.sqlalchemy.track import TrackDBModel
from models.sqlalchemy.status import StatusDBModel
from models.sqlalchemy.fxa_updates import FxaUpdatesDBModel
from models.base import Base
