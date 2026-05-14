"""
Flow control prediction storage.

Each row is one prediction snapshot for one airport. Storing predictions lets
us show probability trends over time and — once we accumulate enough data —
provides labeled training data for upgrading the heuristic scorer to an ML model.

Ground truth labeling strategy:
  After the prediction window expires, a background job can check whether
  TMI data contains a GDP/GS record for that airport in that window and
  set `actual_flow_control` accordingly. This turns the prediction log into
  a training dataset for scikit-learn.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import func, Index
from models.base import Base


class FlowPredictionDBModel(Base):
    __tablename__ = "flow_predictions"

    id = Column(Integer, primary_key=True, index=True)

    # Airport this prediction is for
    airport_icao = Column(String(10), nullable=False, index=True)

    # When the prediction was generated
    predicted_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)

    # Window this prediction covers (e.g. predicted_at + window_hours)
    window_hours = Column(Integer, nullable=False, default=2)

    # ── Core outputs ──────────────────────────────────────────────────────────
    # 0.0–1.0 probability that flow control will be active during the window
    flow_probability = Column(Float, nullable=False)

    # VERY_LOW / LOW / MODERATE / HIGH / VERY_HIGH
    risk_level = Column(String(20), nullable=False)

    # HIGH / MEDIUM / LOW — data completeness
    confidence = Column(String(20), nullable=False)

    # ── Feature snapshot (preserved for model training) ───────────────────────
    ceiling_ft = Column(Integer)                   # lowest BKN/OVC layer
    visibility_sm = Column(Float)                  # statute miles
    flight_category = Column(String(10))           # VFR / MVFR / IFR / LIFR
    wind_speed_kt = Column(Integer)
    wind_gust_kt = Column(Integer)
    taf_trend = Column(String(20))                 # IMPROVING / STEADY / DETERIORATING

    active_tmi_types = Column(JSONB)               # ["GDP", "GS", "MIT", "AFP"]
    active_sigmet = Column(Boolean, default=False)
    active_airmet_sierra = Column(Boolean, default=False)
    active_airmet_tango = Column(Boolean, default=False)
    arrival_count_1h = Column(Integer)             # tracks destined here in last 1h

    # ── Explainability ────────────────────────────────────────────────────────
    # List of {factor, contribution, description} dicts — shown to API consumers
    risk_factors = Column(JSONB)

    # Raw data snapshot — full feature dict for ML training
    feature_snapshot = Column(JSONB)

    # ── Ground truth (filled in retrospectively by a labeling job) ────────────
    actual_flow_control = Column(Boolean)          # True if GDP/GS was active in window
    actual_tmi_types = Column(JSONB)               # What actually happened
    labeled_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        Index("ix_flow_predictions_airport_ts", "airport_icao", "predicted_at"),
    )
