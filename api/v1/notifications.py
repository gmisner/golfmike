"""
GET  /v1/notifications/vapid-public-key  — public key for browser subscription
POST /v1/notifications/push/subscribe    — save browser push subscription
DEL  /v1/notifications/push/unsubscribe  — remove push subscription
GET  /v1/notifications/channels          — list Apprise channels
POST /v1/notifications/channels          — add Apprise channel
DEL  /v1/notifications/channels/<id>     — remove channel
PATCH /v1/notifications/channels/<id>    — toggle enabled
"""

import os
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import text
from db_config import SessionLocal
from utils.logger import main_logger as logger

bp = Blueprint("v1_notifications", __name__, url_prefix="/v1/notifications")

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")


def _session():
    return SessionLocal()


def _uid() -> int:
    return int(get_jwt_identity())


# ── VAPID public key (unauthenticated — needed before login to subscribe) ─────
@bp.get("/vapid-public-key")
def vapid_public_key():
    return jsonify({"public_key": VAPID_PUBLIC_KEY})


# ── Push subscriptions ────────────────────────────────────────────────────────
@bp.post("/push/subscribe")
@jwt_required()
def push_subscribe():
    uid  = _uid()
    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint")
    p256dh   = data.get("keys", {}).get("p256dh")
    auth     = data.get("keys", {}).get("auth")
    ua       = request.headers.get("User-Agent", "")[:200]

    if not all([endpoint, p256dh, auth]):
        return jsonify({"error": "endpoint, keys.p256dh, and keys.auth required"}), 422

    try:
        with _session() as db:
            db.execute(text("""
                INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth, user_agent)
                VALUES (:uid, :ep, :p256dh, :auth, :ua)
                ON CONFLICT (endpoint) DO UPDATE
                    SET user_id = :uid, p256dh = :p256dh, auth = :auth, user_agent = :ua
            """), {"uid": uid, "ep": endpoint, "p256dh": p256dh, "auth": auth, "ua": ua})
            db.commit()
        return jsonify({"subscribed": True}), 201
    except Exception as e:
        logger.exception("push_subscribe error")
        return jsonify({"error": str(e)}), 500


@bp.delete("/push/unsubscribe")
@jwt_required()
def push_unsubscribe():
    uid  = _uid()
    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint")
    try:
        with _session() as db:
            db.execute(text(
                "DELETE FROM push_subscriptions WHERE user_id = :uid AND endpoint = :ep"
            ), {"uid": uid, "ep": endpoint})
            db.commit()
        return jsonify({"unsubscribed": True})
    except Exception as e:
        logger.exception("push_unsubscribe error")
        return jsonify({"error": str(e)}), 500


# ── Notification channels (Apprise) ──────────────────────────────────────────
@bp.get("/channels")
@jwt_required()
def list_channels():
    uid = _uid()
    try:
        with _session() as db:
            rows = db.execute(text("""
                SELECT id, label, apprise_url, enabled, created_at
                FROM notification_channels WHERE user_id = :uid ORDER BY created_at
            """), {"uid": uid}).fetchall()
        return jsonify({"channels": [
            {
                "id":          r.id,
                "label":       r.label,
                "apprise_url": r.apprise_url,
                "enabled":     r.enabled,
                "created_at":  r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]})
    except Exception as e:
        logger.exception("list_channels error")
        return jsonify({"error": str(e)}), 500


@bp.post("/channels")
@jwt_required()
def add_channel():
    uid  = _uid()
    data = request.get_json(silent=True) or {}
    label       = (data.get("label") or "").strip()
    apprise_url = (data.get("apprise_url") or "").strip()

    if not label or not apprise_url:
        return jsonify({"error": "label and apprise_url required"}), 422

    try:
        with _session() as db:
            count = db.execute(
                text("SELECT COUNT(*) FROM notification_channels WHERE user_id = :uid"),
                {"uid": uid}
            ).scalar()
            if count >= 10:
                return jsonify({"error": "Max 10 channels per user"}), 429

            row = db.execute(text("""
                INSERT INTO notification_channels (user_id, label, apprise_url)
                VALUES (:uid, :label, :url)
                RETURNING id, label, apprise_url, enabled, created_at
            """), {"uid": uid, "label": label, "url": apprise_url}).fetchone()
            db.commit()

        return jsonify({
            "id":          row.id,
            "label":       row.label,
            "apprise_url": row.apprise_url,
            "enabled":     row.enabled,
            "created_at":  row.created_at.isoformat() if row.created_at else None,
        }), 201
    except Exception as e:
        logger.exception("add_channel error")
        return jsonify({"error": str(e)}), 500


@bp.patch("/channels/<int:channel_id>")
@jwt_required()
def update_channel(channel_id: int):
    uid  = _uid()
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled")
    label   = data.get("label")

    if enabled is None and label is None:
        return jsonify({"error": "Nothing to update"}), 422

    try:
        with _session() as db:
            sets, params = [], {"cid": channel_id, "uid": uid}
            if enabled is not None:
                sets.append("enabled = :enabled"); params["enabled"] = bool(enabled)
            if label is not None:
                sets.append("label = :label"); params["label"] = str(label).strip()

            row = db.execute(text(f"""
                UPDATE notification_channels SET {", ".join(sets)}
                WHERE id = :cid AND user_id = :uid
                RETURNING id, label, apprise_url, enabled
            """), params).fetchone()
            db.commit()

        if not row:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"id": row.id, "label": row.label, "apprise_url": row.apprise_url, "enabled": row.enabled})
    except Exception as e:
        logger.exception("update_channel error")
        return jsonify({"error": str(e)}), 500


@bp.delete("/channels/<int:channel_id>")
@jwt_required()
def delete_channel(channel_id: int):
    uid = _uid()
    try:
        with _session() as db:
            result = db.execute(text(
                "DELETE FROM notification_channels WHERE id = :cid AND user_id = :uid"
            ), {"cid": channel_id, "uid": uid})
            db.commit()
        if result.rowcount == 0:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"deleted": channel_id})
    except Exception as e:
        logger.exception("delete_channel error")
        return jsonify({"error": str(e)}), 500
