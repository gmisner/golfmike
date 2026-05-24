"""
Notification service powered by Apprise + Web Push.

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

import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

try:
    import apprise as _apprise_lib
    _APPRISE_AVAILABLE = True
except ImportError:
    _apprise_lib = None
    _APPRISE_AVAILABLE = False

try:
    from pywebpush import webpush, WebPushException
    _WEBPUSH_AVAILABLE = True
except ImportError:
    _WEBPUSH_AVAILABLE = False

VAPID_PUBLIC_KEY  = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_EMAIL       = os.environ.get("VAPID_CLAIMS_EMAIL", "admin@golfmike.app")

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


# ── Browser push helpers ──────────────────────────────────────────────────────

def send_push_notification(endpoint: str, p256dh: str, auth: str,
                           title: str, body: str, url: str = "/") -> bool:
    """Send a single Web Push notification. Returns True on success, raises on 410."""
    if not _WEBPUSH_AVAILABLE or not VAPID_PRIVATE_KEY:
        return False
    try:
        payload = json.dumps({"title": title, "body": body, "url": url})
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{VAPID_EMAIL}"},
        )
        return True
    except WebPushException as e:
        status = e.response.status_code if e.response is not None else 0
        logger.warning(f"Push failed ({status}): {e}")
        if status == 410:
            raise  # subscription expired — caller removes it
        return False
    except Exception as e:
        logger.exception(f"Push error: {e}")
        return False


def notify_watchlist_user(db_session, user_id: int, title: str, body: str, url: str = "/") -> int:
    """
    Fire all active push subscriptions + Apprise channels for a user.
    Returns count of successful sends. Removes expired push subs automatically.
    """
    from sqlalchemy import text
    sent = 0

    # --- Browser push ---
    if _WEBPUSH_AVAILABLE and VAPID_PRIVATE_KEY:
        subs = db_session.execute(
            text("SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchall()
        dead = []
        for sub in subs:
            try:
                if send_push_notification(sub.endpoint, sub.p256dh, sub.auth, title, body, url):
                    sent += 1
            except Exception:
                dead.append(sub.id)
        for dead_id in dead:
            db_session.execute(text("DELETE FROM push_subscriptions WHERE id = :id"), {"id": dead_id})

    # --- Apprise channels ---
    if _APPRISE_AVAILABLE:
        channels = db_session.execute(
            text("SELECT apprise_url FROM notification_channels WHERE user_id = :uid AND enabled = true"),
            {"uid": user_id},
        ).fetchall()
        for ch in channels:
            try:
                ap = _apprise_lib.Apprise()
                ap.add(ch.apprise_url)
                if ap.notify(title=title, body=body):
                    sent += 1
            except Exception as e:
                logger.exception(f"Apprise channel error: {e}")

    return sent
