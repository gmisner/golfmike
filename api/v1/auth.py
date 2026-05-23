"""
POST /v1/auth/register  — create account
POST /v1/auth/login     — get access + refresh tokens
POST /v1/auth/refresh   — exchange refresh token for new access token
POST /v1/auth/logout    — revoke current token
GET  /v1/auth/me        — current user info (requires access token)
"""

import bcrypt
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy import text
from db_config import SessionLocal
from utils.logger import main_logger as logger

bp = Blueprint("v1_auth", __name__, url_prefix="/v1/auth")


def _session():
    return SessionLocal()


# ── Register ──────────────────────────────────────────────────────────
@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email        = (data.get("email") or "").strip().lower()
    password     = data.get("password") or ""
    display_name = (data.get("display_name") or "").strip() or None

    if not email or "@" not in email:
        return jsonify({"error": "Valid email required"}), 422
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 422

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        with _session() as db:
            existing = db.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            ).fetchone()
            if existing:
                return jsonify({"error": "Email already registered"}), 409

            row = db.execute(
                text("""
                    INSERT INTO users (email, password_hash, display_name)
                    VALUES (:email, :pw_hash, :display_name)
                    RETURNING id, email, display_name, created_at
                """),
                {"email": email, "pw_hash": pw_hash, "display_name": display_name},
            ).fetchone()
            db.commit()

        user_id = str(row.id)
        return jsonify({
            "user": {
                "id":           row.id,
                "email":        row.email,
                "display_name": row.display_name,
            },
            "access_token":  create_access_token(identity=user_id),
            "refresh_token": create_refresh_token(identity=user_id),
        }), 201

    except Exception as e:
        logger.exception("register error")
        return jsonify({"error": "Registration failed"}), 500


# ── Login ─────────────────────────────────────────────────────────────
@bp.post("/login")
def login():
    data     = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 422

    try:
        with _session() as db:
            row = db.execute(
                text("""
                    SELECT id, email, password_hash, display_name, is_active
                    FROM users WHERE email = :email
                """),
                {"email": email},
            ).fetchone()

            if not row or not bcrypt.checkpw(password.encode(), row.password_hash.encode()):
                return jsonify({"error": "Invalid email or password"}), 401

            if not row.is_active:
                return jsonify({"error": "Account disabled"}), 403

            db.execute(
                text("UPDATE users SET last_login = NOW() WHERE id = :id"),
                {"id": row.id},
            )
            db.commit()

        user_id = str(row.id)
        return jsonify({
            "user": {
                "id":           row.id,
                "email":        row.email,
                "display_name": row.display_name,
            },
            "access_token":  create_access_token(identity=user_id),
            "refresh_token": create_refresh_token(identity=user_id),
        })

    except Exception as e:
        logger.exception("login error")
        return jsonify({"error": "Login failed"}), 500


# ── Refresh ───────────────────────────────────────────────────────────
@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    return jsonify({"access_token": create_access_token(identity=identity)})


# ── Logout ────────────────────────────────────────────────────────────
@bp.post("/logout")
@jwt_required(verify_type=False)
def logout():
    jwt_data = get_jwt()
    jti        = jwt_data["jti"]
    token_type = jwt_data["type"]
    try:
        with _session() as db:
            db.execute(
                text("INSERT INTO jwt_denylist (jti, token_type) VALUES (:jti, :tt)"),
                {"jti": jti, "tt": token_type},
            )
            db.commit()
        return jsonify({"message": "Logged out"})
    except Exception as e:
        logger.exception("logout error")
        return jsonify({"error": "Logout failed"}), 500


# ── Me ────────────────────────────────────────────────────────────────
@bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    try:
        with _session() as db:
            row = db.execute(
                text("SELECT id, email, display_name, created_at FROM users WHERE id = :id"),
                {"id": int(user_id)},
            ).fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404
        return jsonify({
            "id":           row.id,
            "email":        row.email,
            "display_name": row.display_name,
            "member_since": row.created_at.isoformat() if row.created_at else None,
        })
    except Exception as e:
        logger.exception("me error")
        return jsonify({"error": "Failed to fetch user"}), 500
