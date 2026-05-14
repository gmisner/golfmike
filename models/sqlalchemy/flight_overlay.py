"""
Data models for planned vs. actual flight track overlay, deviation detection,
and notification subscriptions.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import func
from models.base import Base


class PlannedWaypointDBModel(Base):
    """
    Ordered waypoints decoded from a filed flight plan route string.
    One row per fix/waypoint per flight plan. Populated by route_decoder service
    when a flight plan is stored.
    """

    __tablename__ = "planned_waypoints"

    id = Column(Integer, primary_key=True, index=True)
    gufi = Column(String(100), nullable=False, index=True)
    aircraft_id = Column(String(50), nullable=False, index=True)

    # Position in the planned route (0 = departure, N = destination)
    sequence = Column(Integer, nullable=False)

    # Fix/waypoint identifier (e.g. "BRUSR", "DEANO", "KLAX")
    fix_name = Column(String(20), nullable=False)

    # Decoded coordinates (null if fix not found in navaid DB)
    latitude = Column(Float)
    longitude = Column(Float)

    # Filed restrictions from the route string
    altitude_restriction = Column(String(20))   # e.g. "FL350", "10000"
    speed_restriction = Column(String(20))      # e.g. "250K"

    # Estimated time over (ETO) — derived from ETD + leg elapsed times when available
    estimated_time_over = Column(DateTime(timezone=True))

    # Source — "FILED" or "AMENDED" (updated when FlightModifyData arrives)
    route_source = Column(String(20), default="FILED")

    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        Index("ix_planned_waypoints_gufi_seq", "gufi", "sequence"),
    )


class FlightDeviationDBModel(Base):
    """
    Computed deviation records written by route_overlay_service each time a
    track point is processed. Enables time-series analysis of route adherence.
    """

    __tablename__ = "flight_deviations"

    id = Column(Integer, primary_key=True, index=True)
    gufi = Column(String(100), nullable=False, index=True)
    aircraft_id = Column(String(50), nullable=False, index=True)

    # Actual position at time of deviation check
    actual_latitude = Column(Float, nullable=False)
    actual_longitude = Column(Float, nullable=False)
    actual_altitude = Column(Integer)
    actual_speed = Column(Integer)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Nearest planned route segment
    nearest_planned_sequence = Column(Integer)
    nearest_fix_name = Column(String(20))

    # Cross-track distance in nautical miles (signed: positive = right of track)
    cross_track_distance_nm = Column(Float)

    # Altitude delta from filed/cleared altitude in feet
    altitude_delta_ft = Column(Integer)

    # Alert level: "NORMAL", "CAUTION" (>2nm or >500ft), "WARNING" (>5nm or >1000ft)
    alert_level = Column(String(20), default="NORMAL")

    # Whether this deviation triggered a notification
    notification_sent = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        Index("ix_flight_deviations_gufi_ts", "gufi", "timestamp"),
    )


class NotificationSubscriptionDBModel(Base):
    """
    Customer subscriptions for flight event push notifications via Apprise.
    Supports filtering by airport pair, aircraft ID, or event type.
    """

    __tablename__ = "notification_subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    # Apprise-compatible notification URL (e.g. slack://, discord://, mailto://)
    # See: https://github.com/caronc/apprise
    apprise_url = Column(String(500), nullable=False)

    # Optional label for this subscription (customer-provided)
    label = Column(String(100))

    # Event filter — null = subscribe to all of that type
    event_types = Column(JSONB, default=list)       # ["FILED", "DEPARTED", "ARRIVED", "DIVERTED", "DEVIATION"]
    filter_origin = Column(String(10))              # ICAO departure airport filter
    filter_destination = Column(String(10))         # ICAO arrival airport filter
    filter_aircraft_id = Column(String(50))         # Specific tail/callsign filter
    filter_alert_level = Column(String(20))         # Minimum deviation alert level

    # Lifecycle
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    last_notified_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_notification_subscriptions_active", "is_active"),
    )
