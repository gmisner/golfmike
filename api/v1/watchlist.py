"""
GET    /v1/watchlist          — list user's watched aircraft
POST   /v1/watchlist          — add aircraft to watchlist
PATCH  /v1/watchlist/<id>     — update label / notification prefs
DELETE /v1/watchlist/<id>     — remove from watchlist
GET    /v1/watchlist/flights  — current flight status for all watched aircraft
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import text
from db_config import SessionLocal
from utils.logger import main_logger as logger

bp = Blueprint("v1_watchlist", __name__, url_prefix="/v1/watchlist")


def _session():
    return SessionLocal()


def _current_user_id() -> int:
    return int(get_jwt_identity())


# ── List ──────────────────────────────────────────────────────────────
@bp.get("")
@jwt_required()
def list_watchlist():
    user_id = _current_user_id()
    try:
        with _session() as db:
            rows = db.execute(
                text("""
                    SELECT id, aircraft_id, label,
                           notify_departure, notify_arrival, notify_filed,
                           created_at
                    FROM watchlist
                    WHERE user_id = :uid
                    ORDER BY created_at DESC
                """),
                {"uid": user_id},
            ).fetchall()

        items = [
            {
                "id":                r.id,
                "aircraft_id":       r.aircraft_id,
                "label":             r.label,
                "notify_departure":  r.notify_departure,
                "notify_arrival":    r.notify_arrival,
                "notify_filed":      r.notify_filed,
                "created_at":        r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
        return jsonify({"items": items})
    except Exception as e:
        logger.exception("watchlist list error")
        return jsonify({"error": str(e)}), 500


# ── Add ───────────────────────────────────────────────────────────────
@bp.post("")
@jwt_required()
def add_to_watchlist():
    user_id = _current_user_id()
    data = request.get_json(silent=True) or {}
    aircraft_id = (data.get("aircraft_id") or "").strip().upper()
    label       = (data.get("label") or "").strip() or None

    if not aircraft_id:
        return jsonify({"error": "aircraft_id required"}), 422
    if len(aircraft_id) > 20:
        return jsonify({"error": "aircraft_id too long"}), 422

    try:
        with _session() as db:
            # Check limit (max 50 per user)
            count = db.execute(
                text("SELECT COUNT(*) FROM watchlist WHERE user_id = :uid"),
                {"uid": user_id},
            ).scalar()
            if count >= 50:
                return jsonify({"error": "Watchlist limit reached (50 max)"}), 429

            row = db.execute(
                text("""
                    INSERT INTO watchlist (user_id, aircraft_id, label)
                    VALUES (:uid, :aid, :label)
                    ON CONFLICT (user_id, aircraft_id) DO NOTHING
                    RETURNING id, aircraft_id, label, notify_departure, notify_arrival,
                              notify_filed, created_at
                """),
                {"uid": user_id, "aid": aircraft_id, "label": label},
            ).fetchone()
            db.commit()

        if not row:
            return jsonify({"error": "Already watching this aircraft"}), 409

        return jsonify({
            "id":               row.id,
            "aircraft_id":      row.aircraft_id,
            "label":            row.label,
            "notify_departure": row.notify_departure,
            "notify_arrival":   row.notify_arrival,
            "notify_filed":     row.notify_filed,
            "created_at":       row.created_at.isoformat() if row.created_at else None,
        }), 201

    except Exception as e:
        logger.exception("watchlist add error")
        return jsonify({"error": str(e)}), 500


# ── Update prefs ──────────────────────────────────────────────────────
@bp.patch("/<int:item_id>")
@jwt_required()
def update_watchlist_item(item_id: int):
    user_id = _current_user_id()
    data = request.get_json(silent=True) or {}

    allowed = {"label", "notify_departure", "notify_arrival", "notify_filed"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "Nothing to update"}), 422

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    try:
        with _session() as db:
            row = db.execute(
                text(f"""
                    UPDATE watchlist
                    SET {set_clause}
                    WHERE id = :item_id AND user_id = :uid
                    RETURNING id, aircraft_id, label,
                              notify_departure, notify_arrival, notify_filed
                """),
                {**updates, "item_id": item_id, "uid": user_id},
            ).fetchone()
            db.commit()

        if not row:
            return jsonify({"error": "Not found"}), 404

        return jsonify({
            "id":               row.id,
            "aircraft_id":      row.aircraft_id,
            "label":            row.label,
            "notify_departure": row.notify_departure,
            "notify_arrival":   row.notify_arrival,
            "notify_filed":     row.notify_filed,
        })
    except Exception as e:
        logger.exception("watchlist update error")
        return jsonify({"error": str(e)}), 500


# ── Remove ────────────────────────────────────────────────────────────
@bp.delete("/<int:item_id>")
@jwt_required()
def remove_from_watchlist(item_id: int):
    user_id = _current_user_id()
    try:
        with _session() as db:
            result = db.execute(
                text("DELETE FROM watchlist WHERE id = :item_id AND user_id = :uid"),
                {"item_id": item_id, "uid": user_id},
            )
            db.commit()

        if result.rowcount == 0:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"deleted": item_id})
    except Exception as e:
        logger.exception("watchlist delete error")
        return jsonify({"error": str(e)}), 500


# ── Live status for all watched aircraft ──────────────────────────────
@bp.get("/flights")
@jwt_required()
def watchlist_flights():
    user_id = _current_user_id()
    try:
        with _session() as db:
            watched = db.execute(
                text("SELECT id, aircraft_id, label FROM watchlist WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchall()

            if not watched:
                return jsonify({"flights": []})

            ids = [r.aircraft_id for r in watched]
            labels = {r.aircraft_id: r.label for r in watched}
            wl_ids  = {r.aircraft_id: r.id   for r in watched}

            placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
            params = {f"id{i}": v for i, v in enumerate(ids)}

            rows = db.execute(
                text(f"""
                    SELECT
                        fp.aircraft_id      AS ident,
                        fp.departure_airport AS origin,
                        fp.arrival_airport   AS destination,
                        fp.aircraft_type,
                        fp.proposed_departure_time AS departure_time,
                        COALESCE(fp.flight_status, 'unknown') AS status,
                        ti.latitude, ti.longitude, ti.altitude,
                        ti.speed AS ground_speed
                    FROM flight_plan fp
                    LEFT JOIN LATERAL (
                        SELECT latitude, longitude, altitude, speed
                        FROM track_information
                        WHERE aircraft_id = fp.aircraft_id
                        ORDER BY time_at_position DESC
                        LIMIT 1
                    ) ti ON true
                    WHERE fp.aircraft_id IN ({placeholders})
                      AND fp.proposed_departure_time > NOW() - INTERVAL '24 hours'
                    ORDER BY fp.aircraft_id, fp.proposed_departure_time DESC
                """),
                params,
            ).fetchall()

        seen = set()
        flights = []
        for r in rows:
            if r.ident in seen:
                continue
            seen.add(r.ident)
            flights.append({
                "watchlist_id":  wl_ids.get(r.ident),
                "label":         labels.get(r.ident),
                "ident":         r.ident,
                "origin":        r.origin,
                "destination":   r.destination,
                "aircraft_type": r.aircraft_type,
                "departure_time": r.departure_time.isoformat() if r.departure_time else None,
                "status":        r.status,
                "latitude":      float(r.latitude)   if r.latitude    is not None else None,
                "longitude":     float(r.longitude)  if r.longitude   is not None else None,
                "altitude":      int(r.altitude)     if r.altitude    is not None else None,
                "ground_speed":  int(r.ground_speed) if r.ground_speed is not None else None,
            })

        # Include watched aircraft with no recent flight
        for r in watched:
            if r.aircraft_id not in seen:
                flights.append({
                    "watchlist_id": r.id,
                    "label":        r.label,
                    "ident":        r.aircraft_id,
                    "origin":       None, "destination": None,
                    "aircraft_type": None, "departure_time": None,
                    "status":       "no recent flight",
                    "latitude": None, "longitude": None,
                    "altitude": None, "ground_speed": None,
                })

        return jsonify({"flights": flights})
    except Exception as e:
        logger.exception("watchlist flights error")
        return jsonify({"error": str(e)}), 500
