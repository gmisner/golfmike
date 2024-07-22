# models/__init__.py

from .sqlalchemy.aircraft import AircraftDBModel
from .sqlalchemy.flight_plan import FlightPlanDBModel
from .sqlalchemy.tmi_updates import TmiUpdatesDBModel
from .sqlalchemy.fxa_updates import FxaUpdatesDBModel
from .sqlalchemy.status import StatusDBModel
from .pydantic.flight_plan import FlightPlanModel
from .pydantic.tmi_updates import TmiUpdatesModel
from .pydantic.fxa_updates import FxaUpdatesModel
from .pydantic.flight_sectors import FlightSectorsModel
from .pydantic.track import TrackInformation, FltdMessage
from .pydantic.status import StatusModel
from .pydantic.tmi_flight_list import TmiFlightListModel


__all__ = [
    "AircraftDBModel",
    "TmiUpdatesDBModel",
    "FxaUpdatesDBModel",
    "FlightPlanDBModel",
    "FlightSectorsDBModel",
    "TmiFlightListDBModel",
    "TrackDBModel",
    "StatusDBModel",
    "AircraftModel",
    "TmiUpdatesModel",
    "FxaUpdatesModel",
    "FlightPlanModel",
    "FlightSectorsModel",
    "TmiFlightListModel",
    "TrackModel",
    "StatusModel",
]
