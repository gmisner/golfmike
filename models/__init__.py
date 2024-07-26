# models/__init__.py
from models.sqlalchemy.aircraft import AircraftDBModel
from models.sqlalchemy.flight_plan import FlightPlanDBModel
from models.sqlalchemy.tmi_updates import TmiUpdatesDBModel
from models.sqlalchemy.track_information import TrackInformationDBModel
from models.sqlalchemy.status import StatusDBModel
from models.sqlalchemy.fxa_flight import FxaFlightDBModel
from .base import Base
from .pydantic.flight_plan import FlightPlanModel
from .pydantic.tmi_updates import TmiUpdatesModel
from .pydantic.fxa_flight import FxaFlightModel
from .pydantic.flight_sectors import FlightSectorsModel
from .pydantic.track_information import TrackInformationModel
from .pydantic.status import StatusModel
from .pydantic.tmi_flight_list import TMIFlightListModel


__all__ = [
    "AircraftDBModel",
    "TmiUpdatesDBModel",
    "FxaUpdatesDBModel",
    "FlightPlanDBModel",
    "FlightSectorsDBModel",
    "TmiFlightListDBModel",
    "TrackInformationDBModel",
    "StatusDBModel",
    "AircraftModel",
    "TmiUpdatesModel",
    "FxaFlightModel",
    "FlightPlanModel",
    "FlightSectorsModel",
    "TMIFlightListModel",
    "TrackInformationModel",
    "StatusModel",
]
