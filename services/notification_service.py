"""
Notification service powered by Apprise.

Supports any Apprise-compatible URL: Slack, Discord, Telegram, Pushover,
ntfy, email (SMTP), PagerDuty, Teams, and 50+ others.

See https://github.com/caronc/apprise for URL format documentation.

Configuration:
  Set APPRISE_URLS in environment as a comma-separated list of Apprise URLs
  for a global broadcast channel (used in addition to per-subscription URLs).

  Examples:
    APPRISE_URLS=slack://token/channel,discord://webhook_id/webhook_token
    APPRISE_URLS=ntfy://mytopic,mailto://user:pass@smtp.example.com/recipient@example.com
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

try:
    import apprise as _apprise_lib
    _APPRISE_AVAILABLE = True
except ImportError:
    _apprise_lib = None
    _APPRISE_AVAILABLE = False

from sqlalchemy.orm import Session

from models.sqlalchemy.flight_overlay import NotificationSubscriptionDBModel
from utils.logger import main_logger as logger


# ── Global broadcast channels (from env) ──────────────────────────────────────

def _build_global_apprise():
    if not _APPRISE_AVAILABLE:
        logger.warning("apprise not installed — notifications disabled. Run: pip install apprise")
        return None
    ap = _apprise_lib.Apprise()
    raw = os.getenv("APPRISE_URLS", "")
    for url in (u.strip() for u in raw.split(",") if u.strip()):
        ap.add(url)
    return ap


_global_ap = _build_global_apprise()


# ── Core send helpers ─────────────────────────────────────────────────────────

def _send(ap, title: str, body: str) -> bool:
    if not ap:
        return False
    try:
        return ap.notify(title=title, body=body)
    except Exception as e:
        logger.error(f"Apprise send error: {e}")
        return False


def _event_title(event_type: str, aircraft_id: str) -> str:
    labels = {
        "FILED": "✈ Flight Plan Filed",
        "DEPARTED": "🛫 Departed",
        "ARRIVED": "🛬 Arrived",
        "DIVERTED": "⚠️ Diverted",
        "CANCELLED": "❌ Cancelled",
        "DEVIATION": "📍 Route Deviation",
    }
    label = labels.get(event_type, event_type)
    return f"{label} — {aircraft_id}"


def _event_body(event_type: str, event_data: Dict[str, Any]) -> str:
    origin = event_data.get("departure_airport", "")
    dest = event_data.get("arrival_airport", "")
    gufi = event_data.get("gufi", "")

    if event_type == "FILED":
        etd = event_data.get("departure_time", "")
        route = event_data.get("route_text", "Direct")
        return f"{origin} → {dest} | ETD: {etd}\nRoute: {route}\nGUFI: {gufi}"

    if event_type == "DEPARTED":
        return f"{origin} → {dest} | Airborne\nGUFI: {gufi}"

    if event_type == "ARRIVED":
        return f"{origin} → {dest} | On ground\nGUFI: {gufi}"

    if event_type == "DIVERTED":
        divert_to = event_data.get("divert_airport", "unknown")
        return f"{origin} → {dest} | Diverted to {divert_to}\nGUFI: {gufi}"

    if event_type == "DEVIATION":
        nm = event_data.get("cross_track_nm", 0)
        alt_delta = event_data.get("altitude_delta_ft", 0)
        level = event_data.get("alert_level", "CAUTION")
        fix = event_data.get("nearest_fix", "")
        return (
            f"{origin} → {dest} | {level}\n"
            f"Off-track: {nm:.1f} nm | Alt delta: {alt_delta:+d} ft\n"
            f"Near: {fix} | GUFI: {gufi}"
        )

    return str(event_data)


# ── Subscription matching ─────────────────────────────────────────────────────

def _subscription_matches(
    sub: NotificationSubscriptionDBModel,
    event_type: str,
    event_data: Dict[str, Any],
) -> bool:
    if not sub.is_active:
        return False

    if sub.event_types and event_type not in sub.event_types:
        return False

    origin = event_data.get("departure_airport", "")
    dest = event_data.get("arrival_airport", "")
    aircraft_id = event_data.get("aircraft_id", "")

    if sub.filter_origin and sub.filter_origin.upper() != origin.upper():
        return False
    if sub.filter_destination and sub.filter_destination.upper() != dest.upper():
        return False
    if sub.filter_aircraft_id and sub.filter_aircraft_id.upper() != aircraft_id.upper():
        return False

    if event_type == "DEVIATION" and sub.filter_alert_level:
        levels = ["NORMAL", "CAUTION", "WARNING"]
        event_level = event_data.get("alert_level", "NORMAL")
        if levels.index(event_level) < levels.index(sub.filter_alert_level):
            return False

    return True


# ── Public API ────────────────────────────────────────────────────────────────

def send_flight_event(
    event_type: str,
    event_data: Dict[str, Any],
    session: Optional[Session] = None,
) -> None:
    """
    Send a flight event notification to all matching subscribers plus
    any global broadcast channels configured via APPRISE_URLS.

    Args:
        event_type: One of FILED, DEPARTED, ARRIVED, DIVERTED, CANCELLED, DEVIATION
        event_data: Dict with aircraft_id, gufi, departure_airport, arrival_airport,
                    and any event-specific fields
        session:    Open SQLAlchemy session for querying subscriptions (optional —
                    if None, only global channels are notified)
    """
    aircraft_id = event_data.get("aircraft_id", "unknown")
    title = _event_title(event_type, aircraft_id)
    body = _event_body(event_type, event_data)

    # Global broadcast
    if _global_ap:
        _send(_global_ap, title, body)

    # Per-subscription delivery
    if session is None:
        return

    try:
        subs: List[NotificationSubscriptionDBModel] = (
            session.query(NotificationSubscriptionDBModel)
            .filter_by(is_active=True)
            .all()
        )
    except Exception as e:
        logger.error(f"Failed to query notification subscriptions: {e}")
        return

    for sub in subs:
        if not _subscription_matches(sub, event_type, event_data):
            continue

        if not _APPRISE_AVAILABLE:
            continue
        ap = _apprise_lib.Apprise()
        ap.add(sub.apprise_url)
        sent = _send(ap, title, body)

        if sent:
            sub.last_notified_at = datetime.now(timezone.utc)
            logger.info(
                f"Notification sent [{event_type}] {aircraft_id} → sub#{sub.id}"
            )
        else:
            logger.warning(
                f"Notification failed [{event_type}] {aircraft_id} → sub#{sub.id}"
            )

    try:
        session.commit()
    except Exception:
        session.rollback()
