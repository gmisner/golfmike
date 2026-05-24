"""
Celery beat task — fires every 60s, checks watched aircraft for status changes
and sends notifications for departure / arrival / flight plan filed events.
"""

from celery import shared_task
from sqlalchemy import text
from db_config import SessionLocal
from services.notification_service import notify_watchlist_user
from utils.logger import main_logger as logger


@shared_task(name="tasks.notify_watchlist.check_watchlist_events", bind=True, max_retries=2)
def check_watchlist_events(self):
    """
    For every watched aircraft, detect new departure/arrival/filed events
    and send push/channel notifications, deduped via notification_log.
    """
    try:
        with SessionLocal() as db:
            # Load all active watchlist entries
            watched = db.execute(text("""
                SELECT w.id, w.user_id, w.aircraft_id,
                       w.notify_departure, w.notify_arrival, w.notify_filed
                FROM watchlist w
                JOIN users u ON u.id = w.user_id AND u.is_active = true
            """)).fetchall()

            if not watched:
                return {"checked": 0}

            aircraft_ids = list({r.aircraft_id for r in watched})
            placeholders = ", ".join(f":id{i}" for i in range(len(aircraft_ids)))
            params = {f"id{i}": v for i, v in enumerate(aircraft_ids)}

            # Get the most recent flight event for each aircraft in the last 2 hours
            events = db.execute(text(f"""
                SELECT DISTINCT ON (aircraft_id, event_type)
                    aircraft_id,
                    event_type,
                    COALESCE(airport_code, '') AS airport,
                    COALESCE(message, '')       AS message,
                    event_time,
                    COALESCE(gufi, aircraft_id || '_' || DATE_TRUNC('hour', event_time)::text) AS event_key
                FROM flight_events
                WHERE aircraft_id IN ({placeholders})
                  AND event_time > NOW() - INTERVAL '2 hours'
                ORDER BY aircraft_id, event_type, event_time DESC
            """), params).fetchall()

            # Build a lookup: aircraft_id -> list of recent events
            from collections import defaultdict
            recent: dict = defaultdict(list)
            for ev in events:
                recent[ev.aircraft_id].append(ev)

            # Also check flight_plan for filed events
            filed_rows = db.execute(text(f"""
                SELECT DISTINCT ON (aircraft_id)
                    aircraft_id,
                    gufi,
                    departure_airport,
                    arrival_airport,
                    proposed_departure_time,
                    created_at
                FROM flight_plan
                WHERE aircraft_id IN ({placeholders})
                  AND created_at > NOW() - INTERVAL '2 hours'
                ORDER BY aircraft_id, created_at DESC
            """), params).fetchall()

            filed_map = {r.aircraft_id: r for r in filed_rows}

            sent_total = 0

            for entry in watched:
                uid = entry.user_id
                acid = entry.aircraft_id

                # --- Departure / Arrival via flight_events ---
                for ev in recent.get(acid, []):
                    etype = (ev.event_type or "").lower()

                    if etype == "departed" and not entry.notify_departure:
                        continue
                    if etype == "arrived" and not entry.notify_arrival:
                        continue
                    if etype not in ("departed", "arrived"):
                        continue

                    event_key = f"{uid}:{ev.event_key}:{etype}"

                    # Dedup check
                    already = db.execute(text(
                        "SELECT id FROM notification_log WHERE user_id = :uid AND event_key = :ek"
                    ), {"uid": uid, "ek": event_key}).fetchone()
                    if already:
                        continue

                    # Build message
                    icon = "🛫" if etype == "departed" else "🛬"
                    airport = ev.airport or ""
                    title = f"{icon} {acid} {'departed' if etype == 'departed' else 'arrived'}"
                    body = f"{acid} {etype} {airport}".strip()
                    if ev.message:
                        body = ev.message

                    n = notify_watchlist_user(db, uid, title, body, url=f"/flight/{acid}")
                    sent_total += n

                    # Log it regardless of send count (avoid hammering on no-channel users)
                    db.execute(text("""
                        INSERT INTO notification_log (user_id, aircraft_id, event_type, event_key)
                        VALUES (:uid, :acid, :etype, :ek)
                        ON CONFLICT (user_id, event_key) DO NOTHING
                    """), {"uid": uid, "acid": acid, "etype": etype, "ek": event_key})

                # --- Filed flight plan ---
                if entry.notify_filed and acid in filed_map:
                    fp = filed_map[acid]
                    event_key = f"{uid}:{fp.gufi}:filed"

                    already = db.execute(text(
                        "SELECT id FROM notification_log WHERE user_id = :uid AND event_key = :ek"
                    ), {"uid": uid, "ek": event_key}).fetchone()
                    if already:
                        continue

                    title = f"✈ Flight plan filed — {acid}"
                    body = (
                        f"{acid}: {fp.departure_airport} → {fp.arrival_airport}"
                        + (f" | ETD {fp.proposed_departure_time.strftime('%H:%M')} UTC"
                           if fp.proposed_departure_time else "")
                    )

                    n = notify_watchlist_user(db, uid, title, body, url=f"/flight/{acid}")
                    sent_total += n

                    db.execute(text("""
                        INSERT INTO notification_log (user_id, aircraft_id, event_type, event_key)
                        VALUES (:uid, :acid, 'filed', :ek)
                        ON CONFLICT (user_id, event_key) DO NOTHING
                    """), {"uid": uid, "acid": acid, "ek": event_key})

            db.commit()

        logger.info(f"check_watchlist_events: {len(watched)} entries, {sent_total} notifications sent")
        return {"checked": len(watched), "sent": sent_total}

    except Exception as e:
        logger.exception("check_watchlist_events error")
        raise self.retry(exc=e, countdown=30)
