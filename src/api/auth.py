"""
完整的用户认证系统 API
提供注册、登录、忘记密码、重置密码功能
使用 SQLite 存储用户数据，PBKDF2 哈希密码，HMAC-SHA256 令牌
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, validator

router = APIRouter(prefix="/auth", tags=["authentication"])

# ─────────────────────────────────────────────────────────────────
# 数据库配置
# ─────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "users.db"
SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-secret-change-in-production-please")
TOKEN_TTL = 7 * 24 * 3600          # 7天
RESET_TOKEN_TTL = 3600             # 1小时
PBKDF2_ITERATIONS = 260_000


def _get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                username     TEXT    UNIQUE NOT NULL,
                email        TEXT    UNIQUE NOT NULL,
                password_hash TEXT   NOT NULL,
                created_at   INTEGER NOT NULL,
                is_active    INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS reset_tokens (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                token      TEXT    UNIQUE NOT NULL,
                expires_at INTEGER NOT NULL,
                used       INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        conn.commit()


_init_db()


# ─────────────────────────────────────────────────────────────────
# 安全工具函数
# ─────────────────────────────────────────────────────────────────
def _hash_password(password: str) -> str:
    """使用 PBKDF2-HMAC-SHA256 哈希密码，包含随机 salt"""
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"{salt}:{h.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, h = password_hash.split(":", 1)
        new_h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
        return hmac.compare_digest(h, new_h.hex())
    except (ValueError, AttributeError):
        return False


def _b64_encode(data: dict) -> str:
    import base64
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64_decode(s: str) -> dict:
    import base64
    padding = 4 - len(s) % 4
    return json.loads(base64.urlsafe_b64decode(s + "=" * padding))


def _create_token(payload: dict) -> str:
    """生成 HMAC-SHA256 签名的 JWT-like 令牌"""
    full_payload = {
        **payload,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_TTL,
    }
    header = _b64_encode({"alg": "HS256", "typ": "JWT"})
    body   = _b64_encode(full_payload)
    unsigned = f"{header}.{body}"
    sig = hmac.new(SECRET_KEY.encode(), unsigned.encode(), hashlib.sha256).hexdigest()
    return f"{unsigned}.{sig}"


def _verify_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, body, sig = parts
        expected = hmac.new(SECRET_KEY.encode(), f"{header}.{body}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = _b64_decode(body)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
# Pydantic 模型
# ─────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email:    str
    password: str

    @validator("username")
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("用户名至少需要 3 个字符")
        if len(v) > 32:
            raise ValueError("用户名不能超过 32 个字符")
        if not re.match(r"^[a-zA-Z0-9_\u4e00-\u9fff]+$", v):
            raise ValueError("用户名只能包含字母、数字、下划线或中文字符")
        return v

    @validator("email")
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("邮箱格式不正确")
        return v

    @validator("password")
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少需要 8 个字符")
        if len(v) > 128:
            raise ValueError("密码太长（最多 128 个字符）")
        return v


class LoginRequest(BaseModel):
    email:    str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    reset_token:  str
    new_password: str


class UserResponse(BaseModel):
    id:         int
    username:   str
    email:      str
    created_at: int


class AuthResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserResponse


# ─────────────────────────────────────────────────────────────────
# 依赖注入：当前用户
# ─────────────────────────────────────────────────────────────────
def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未认证，请先登录")
    token = authorization[7:].strip()
    payload = _verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效或已过期，请重新登录")
    return payload


# ─────────────────────────────────────────────────────────────────
# API 端点
# ─────────────────────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=201,
             summary="用户注册")
def register(request: RegisterRequest):
    """创建新用户账号"""
    with _get_db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email=?", (request.email,)).fetchone():
            raise HTTPException(status_code=409, detail="该邮箱已被注册")
        if conn.execute("SELECT 1 FROM users WHERE username=?", (request.username,)).fetchone():
            raise HTTPException(status_code=409, detail="该用户名已被使用")

        now = int(time.time())
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?,?,?,?)",
            (request.username, request.email, _hash_password(request.password), now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()

    return UserResponse(
        id=row["id"], username=row["username"],
        email=row["email"], created_at=row["created_at"]
    )


@router.post("/login", response_model=AuthResponse, summary="用户登录")
def login(request: LoginRequest):
    """验证凭据并返回访问令牌"""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email=?", (request.email.strip().lower(),)
        ).fetchone()

    if not row or not _verify_password(request.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    token = _create_token({
        "sub":      row["id"],
        "email":    row["email"],
        "username": row["username"],
    })
    return AuthResponse(
        access_token=token,
        user=UserResponse(
            id=row["id"], username=row["username"],
            email=row["email"], created_at=row["created_at"]
        ),
    )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
def get_me(current_user: dict = Depends(get_current_user)):
    """返回当前登录用户的详细信息"""
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (current_user["sub"],)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserResponse(
        id=row["id"], username=row["username"],
        email=row["email"], created_at=row["created_at"]
    )


@router.post("/forgot-password", summary="申请密码重置")
def forgot_password(request: ForgotPasswordRequest):
    """发送密码重置令牌（开发模式下直接返回）"""
    email = request.email.strip().lower()
    result: dict = {"message": "如果该邮箱已注册，重置链接已发送至邮箱"}

    with _get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if row:
            token = secrets.token_urlsafe(32)
            expires = int(time.time()) + RESET_TOKEN_TTL
            conn.execute(
                "INSERT INTO reset_tokens (user_id, token, expires_at) VALUES (?,?,?)",
                (row["id"], token, expires),
            )
            conn.commit()
            # 生产环境应通过邮件发送；开发模式直接返回 token
            result["reset_token"]  = token
            result["dev_note"]     = "仅开发模式返回 reset_token，生产环境请配置邮件服务"
            result["expires_in"]   = f"{RESET_TOKEN_TTL // 60} 分钟"

    return result


@router.post("/reset-password", summary="重置密码")
def reset_password(request: ResetPasswordRequest):
    """使用重置令牌设置新密码"""
    if len(request.new_password) < 8:
        raise HTTPException(status_code=422, detail="密码至少需要 8 个字符")

    with _get_db() as conn:
        row = conn.execute(
            "SELECT * FROM reset_tokens WHERE token=? AND used=0",
            (request.reset_token,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="重置令牌无效或已使用")
        if row["expires_at"] < time.time():
            raise HTTPException(status_code=400, detail="重置令牌已过期，请重新申请")

        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (_hash_password(request.new_password), row["user_id"]),
        )
        conn.execute("UPDATE reset_tokens SET used=1 WHERE id=?", (row["id"],))
        conn.commit()

    return {"message": "密码已成功重置，请使用新密码登录"}
