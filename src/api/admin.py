"""
管理员功能模块 API
提供管理员账户管理、用户管理、系统监控、向量知识库管理、系统配置等功能
"""
import hashlib
import hmac
import json
import os
import platform
import psutil
import re
import secrets
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, validator

router = APIRouter(prefix="/admin", tags=["admin"])

# ─────────────────────────────────────────────────────────────────
# 数据库配置（复用 auth.py 的数据库路径）
# ─────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "users.db"
SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-secret-change-in-production-please")
ADMIN_REGISTRATION_KEY = os.getenv("ADMIN_REGISTRATION_KEY", "admin-register-2024")
PBKDF2_ITERATIONS = 260_000
TOKEN_TTL = 7 * 24 * 3600

# Qdrant 配置
QDRANT_PATH = os.getenv("QDRANT_PATH", "data/qdrant")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "github_repo_multi_modal")


def _get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_admin_db() -> None:
    """初始化管理员相关数据库表"""
    with _get_db() as conn:
        # 为 users 表添加 role 字段（如果不存在）
        try:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        except sqlite3.OperationalError:
            pass  # 字段已存在

        # 审计日志表
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                username   TEXT,
                action     TEXT NOT NULL,
                target     TEXT,
                detail     TEXT,
                ip_address TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS system_config (
                key       TEXT PRIMARY KEY,
                value     TEXT NOT NULL,
                updated_by TEXT,
                updated_at INTEGER NOT NULL,
                version   INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS alert_rules (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                metric      TEXT NOT NULL,
                threshold   REAL NOT NULL,
                operator    TEXT DEFAULT 'gt',
                enabled     INTEGER DEFAULT 1,
                created_at  INTEGER NOT NULL,
                last_triggered INTEGER
            );
        """)
        conn.commit()


_init_admin_db()


# ─────────────────────────────────────────────────────────────────
# 安全工具函数（与 auth.py 一致）
# ─────────────────────────────────────────────────────────────────
def _hash_password(password: str) -> str:
    import secrets as _s
    salt = _s.token_hex(16)
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
    full_payload = {**payload, "iat": int(time.time()), "exp": int(time.time()) + TOKEN_TTL}
    header = _b64_encode({"alg": "HS256", "typ": "JWT"})
    body = _b64_encode(full_payload)
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
# 审计日志
# ─────────────────────────────────────────────────────────────────
def _log_audit(user_id: int, username: str, action: str, target: str = "",
               detail: str = "", ip_address: str = "") -> None:
    with _get_db() as conn:
        conn.execute(
            "INSERT INTO audit_logs (user_id, username, action, target, detail, ip_address, created_at) VALUES (?,?,?,?,?,?,?)",
            (user_id, username, action, target, detail, ip_address, int(time.time())),
        )
        conn.commit()


# ─────────────────────────────────────────────────────────────────
# 依赖注入：管理员身份验证
# ─────────────────────────────────────────────────────────────────
def get_admin_user(authorization: Optional[str] = Header(None)) -> dict:
    """验证当前用户是否为管理员"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未认证，请先登录")
    token = authorization[7:].strip()
    payload = _verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效或已过期，请重新登录")

    with _get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (payload["sub"],)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    if row["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足，需要管理员权限")

    return {"id": row["id"], "username": row["username"], "email": row["email"], "role": row["role"]}


def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """可选的用户验证，用于获取当前用户信息"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    payload = _verify_token(token)
    if not payload:
        return None
    return payload


# ─────────────────────────────────────────────────────────────────
# Pydantic 模型
# ─────────────────────────────────────────────────────────────────
class AdminRegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    admin_key: str  # 管理员注册密钥

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
        return v


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "user"

    @validator("role")
    def validate_role(cls, v: str) -> str:
        if v not in ("user", "admin"):
            raise ValueError("角色必须是 user 或 admin")
        return v


class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[int] = None

    @validator("role", pre=True, always=True)
    def validate_role(cls, v):
        if v is not None and v not in ("user", "admin"):
            raise ValueError("角色必须是 user 或 admin")
        return v

    @validator("is_active", pre=True, always=True)
    def validate_active(cls, v):
        if v is not None and v not in (0, 1):
            raise ValueError("状态必须是 0 或 1")
        return v


class ConfigUpdateRequest(BaseModel):
    key: str
    value: str


class AlertRuleRequest(BaseModel):
    name: str
    metric: str
    threshold: float
    operator: str = "gt"
    enabled: int = 1


class PasswordResetRequest(BaseModel):
    user_id: int
    new_password: str

    @validator("new_password")
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少需要 8 个字符")
        return v


# ─────────────────────────────────────────────────────────────────
# 1. 管理员账户管理 API
# ─────────────────────────────────────────────────────────────────
@router.post("/register", status_code=201, summary="管理员注册")
def admin_register(request: AdminRegisterRequest):
    """使用管理员注册密钥创建管理员账号"""
    if request.admin_key != ADMIN_REGISTRATION_KEY:
        raise HTTPException(status_code=403, detail="管理员注册密钥无效")

    with _get_db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email=?", (request.email,)).fetchone():
            raise HTTPException(status_code=409, detail="该邮箱已被注册")
        if conn.execute("SELECT 1 FROM users WHERE username=?", (request.username,)).fetchone():
            raise HTTPException(status_code=409, detail="该用户名已被使用")

        now = int(time.time())
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at, is_active, role) VALUES (?,?,?,?,?,?)",
            (request.username, request.email, _hash_password(request.password), now, 1, "admin"),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()

    _log_audit(row["id"], row["username"], "admin_register", detail="管理员账号注册")
    return {"id": row["id"], "username": row["username"], "email": row["email"], "role": row["role"]}


@router.post("/login", summary="管理员登录")
def admin_login(request: AdminLoginRequest):
    """管理员专用登录入口"""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email=?", (request.email.strip().lower(),)
        ).fetchone()

    if not row or not _verify_password(request.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    if row["role"] != "admin":
        raise HTTPException(status_code=403, detail="该账号不是管理员")

    token = _create_token({
        "sub": row["id"],
        "email": row["email"],
        "username": row["username"],
        "role": "admin",
    })

    _log_audit(row["id"], row["username"], "admin_login", detail="管理员登录")
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "role": row["role"],
            "created_at": row["created_at"],
        },
    }


@router.post("/logout", summary="管理员安全退出")
def admin_logout(admin: dict = Depends(get_admin_user)):
    """管理员安全退出，记录审计日志"""
    _log_audit(admin["id"], admin["username"], "admin_logout", detail="管理员退出")
    return {"message": "已安全退出"}


@router.get("/session", summary="获取管理员会话信息")
def admin_session(admin: dict = Depends(get_admin_user)):
    """验证管理员会话并返回信息"""
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (admin["id"],)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
        "is_active": row["is_active"],
        "created_at": row["created_at"],
    }


# ─────────────────────────────────────────────────────────────────
# 2. 用户管理 API
# ─────────────────────────────────────────────────────────────────
@router.get("/users", summary="获取用户列表")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    role: str = Query(""),
    status: str = Query(""),
    admin: dict = Depends(get_admin_user),
):
    """分页查询用户列表，支持搜索和筛选"""
    with _get_db() as conn:
        conditions = []
        params = []
        if search:
            conditions.append("(username LIKE ? OR email LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if role:
            conditions.append("role = ?")
            params.append(role)
        if status:
            conditions.append("is_active = ?")
            params.append(int(status))

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        total = conn.execute(f"SELECT COUNT(*) FROM users {where}", params).fetchone()[0]

        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT id, username, email, role, is_active, created_at FROM users {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "users": [dict(r) for r in rows],
    }


@router.post("/users", status_code=201, summary="创建用户")
def create_user(request: UserCreateRequest, admin: dict = Depends(get_admin_user)):
    """管理员创建新用户"""
    with _get_db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email=?", (request.email.strip().lower(),)).fetchone():
            raise HTTPException(status_code=409, detail="该邮箱已被注册")
        if conn.execute("SELECT 1 FROM users WHERE username=?", (request.username.strip(),)).fetchone():
            raise HTTPException(status_code=409, detail="该用户名已被使用")

        now = int(time.time())
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at, is_active, role) VALUES (?,?,?,?,1,?)",
            (request.username.strip(), request.email.strip().lower(),
             _hash_password(request.password), now, request.role),
        )
        conn.commit()
        row = conn.execute("SELECT id, username, email, role, is_active, created_at FROM users WHERE id=?",
                           (cur.lastrowid,)).fetchone()

    _log_audit(admin["id"], admin["username"], "create_user", target=str(row["id"]),
               detail=f"创建用户 {row['username']} (角色: {request.role})")
    return dict(row)


@router.get("/users/{user_id}", summary="获取用户详情")
def get_user(user_id: int, admin: dict = Depends(get_admin_user)):
    """获取指定用户的详细信息"""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT id, username, email, role, is_active, created_at FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    return dict(row)


@router.put("/users/{user_id}", summary="更新用户信息")
def update_user(user_id: int, request: UserUpdateRequest, admin: dict = Depends(get_admin_user)):
    """管理员更新用户信息（角色/状态等）"""
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")

        updates = []
        params = []
        if request.username is not None:
            if conn.execute("SELECT 1 FROM users WHERE username=? AND id!=?",
                            (request.username, user_id)).fetchone():
                raise HTTPException(status_code=409, detail="用户名已被使用")
            updates.append("username = ?")
            params.append(request.username)
        if request.email is not None:
            if conn.execute("SELECT 1 FROM users WHERE email=? AND id!=?",
                            (request.email.strip().lower(), user_id)).fetchone():
                raise HTTPException(status_code=409, detail="邮箱已被使用")
            updates.append("email = ?")
            params.append(request.email.strip().lower())
        if request.role is not None:
            updates.append("role = ?")
            params.append(request.role)
        if request.is_active is not None:
            updates.append("is_active = ?")
            params.append(request.is_active)

        if not updates:
            raise HTTPException(status_code=400, detail="没有需要更新的字段")

        params.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)
        conn.commit()

        updated = conn.execute(
            "SELECT id, username, email, role, is_active, created_at FROM users WHERE id=?",
            (user_id,),
        ).fetchone()

    _log_audit(admin["id"], admin["username"], "update_user", target=str(user_id),
               detail=f"更新字段: {', '.join(updates)}")
    return dict(updated)


@router.delete("/users/{user_id}", summary="删除用户")
def delete_user(user_id: int, admin: dict = Depends(get_admin_user)):
    """管理员删除用户"""
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")

    with _get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")

        conn.execute("DELETE FROM reset_tokens WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()

    _log_audit(admin["id"], admin["username"], "delete_user", target=str(user_id),
               detail=f"删除用户 {row['username']}")
    return {"message": "用户已删除"}


@router.post("/users/{user_id}/reset-password", summary="重置用户密码")
def reset_user_password(user_id: int, request: PasswordResetRequest, admin: dict = Depends(get_admin_user)):
    """管理员重置用户密码"""
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")

        conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                     (_hash_password(request.new_password), user_id))
        conn.commit()

    _log_audit(admin["id"], admin["username"], "reset_password", target=str(user_id),
               detail=f"重置用户 {row['username']} 的密码")
    return {"message": "密码已重置"}


@router.get("/users/{user_id}/audit-logs", summary="获取用户操作日志")
def get_user_audit_logs(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_admin_user),
):
    """查询指定用户的操作审计日志"""
    with _get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE user_id=?", (user_id,)).fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            "SELECT * FROM audit_logs WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, page_size, offset),
        ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "logs": [dict(r) for r in rows],
    }


@router.get("/audit-logs", summary="获取全局审计日志")
def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str = Query(""),
    search: str = Query(""),
    admin: dict = Depends(get_admin_user),
):
    """查询全局操作审计日志"""
    with _get_db() as conn:
        conditions = []
        params = []
        if action:
            conditions.append("action = ?")
            params.append(action)
        if search:
            conditions.append("(username LIKE ? OR detail LIKE ? OR target LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        total = conn.execute(f"SELECT COUNT(*) FROM audit_logs {where}", params).fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT * FROM audit_logs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "logs": [dict(r) for r in rows],
    }


# ─────────────────────────────────────────────────────────────────
# 3. 系统监控 API
# ─────────────────────────────────────────────────────────────────
@router.get("/monitor/dashboard", summary="系统监控仪表盘")
def monitor_dashboard(admin: dict = Depends(get_admin_user)):
    """获取系统运行状态概览"""
    # 系统资源
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot_time = psutil.boot_time()
    uptime = int(time.time()) - int(boot_time)

    # 网络统计
    net_io = psutil.net_io_counters()

    # 用户统计
    with _get_db() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0]
        admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]

    # Qdrant 状态
    qdrant_status = "unknown"
    qdrant_info = {}
    try:
        from src.retrieval.vector_store import get_qdrant_client, COLLECTION_NAME
        client = get_qdrant_client()
        if client.collection_exists(COLLECTION_NAME):
            info = client.get_collection(COLLECTION_NAME)
            qdrant_status = "healthy"
            qdrant_info = {
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status,
                "indexed_vectors": getattr(info, 'indexed_vectors_count', 0),
            }
        else:
            qdrant_status = "empty"
    except Exception as e:
        qdrant_status = f"error: {str(e)[:100]}"

    # 进程信息
    process = psutil.Process()
    proc_memory = process.memory_info()

    return {
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "uptime": uptime,
            "boot_time": boot_time,
        },
        "resources": {
            "cpu_percent": cpu_percent,
            "cpu_count": psutil.cpu_count(),
            "memory_total": memory.total,
            "memory_used": memory.used,
            "memory_percent": memory.percent,
            "disk_total": disk.total,
            "disk_used": disk.used,
            "disk_percent": disk.percent,
            "net_bytes_sent": net_io.bytes_sent,
            "net_bytes_recv": net_io.bytes_recv,
        },
        "process": {
            "pid": process.pid,
            "memory_rss": proc_memory.rss,
            "memory_vms": proc_memory.vms,
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads(),
            "create_time": process.create_time(),
        },
        "users_stats": {
            "total": total_users,
            "active": active_users,
            "admins": admin_count,
            "inactive": total_users - active_users,
        },
        "qdrant": {
            "status": qdrant_status,
            "info": qdrant_info,
        },
    }


@router.get("/monitor/health", summary="服务健康检查")
def health_check(admin: dict = Depends(get_admin_user)):
    """检查各关键服务的健康状态"""
    services = []

    # API 服务
    services.append({
        "name": "API 服务",
        "status": "healthy",
        "latency_ms": 0,
        "detail": "FastAPI 运行中",
    })

    # 数据库
    try:
        with _get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        services.append({"name": "SQLite 数据库", "status": "healthy", "latency_ms": 0, "detail": "连接正常"})
    except Exception as e:
        services.append({"name": "SQLite 数据库", "status": "unhealthy", "latency_ms": 0, "detail": str(e)[:100]})

    # Qdrant
    try:
        from src.retrieval.vector_store import get_qdrant_client
        client = get_qdrant_client()
        start = time.time()
        collections = client.get_collections()
        latency = round((time.time() - start) * 1000, 2)
        services.append({
            "name": "Qdrant 向量数据库",
            "status": "healthy",
            "latency_ms": latency,
            "detail": f"集合数: {len(collections.collections)}",
        })
    except Exception as e:
        services.append({"name": "Qdrant 向量数据库", "status": "unhealthy", "latency_ms": 0, "detail": str(e)[:100]})

    # LLM API
    llm_base = os.getenv("LLM_BASE_URL", "")
    llm_key = os.getenv("LLM_API_KEY", "")
    if llm_base and llm_key:
        services.append({"name": "LLM API", "status": "configured", "latency_ms": 0,
                         "detail": f"端点: {llm_base}"})
    else:
        services.append({"name": "LLM API", "status": "not_configured", "latency_ms": 0,
                         "detail": "未配置，使用离线模式"})

    # Embedding
    emb_provider = os.getenv("RAG_EMBEDDING_PROVIDER", "hash")
    services.append({"name": "Embedding 服务", "status": "healthy" if emb_provider == "hash" else "configured",
                     "latency_ms": 0, "detail": f"提供者: {emb_provider}"})

    overall = "healthy" if all(s["status"] in ("healthy", "configured", "not_configured") for s in services) else "degraded"
    return {"overall": overall, "services": services, "checked_at": int(time.time())}


@router.get("/monitor/resources", summary="系统资源监控")
def monitor_resources(admin: dict = Depends(get_admin_user)):
    """获取系统资源使用详情"""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_per_core = psutil.cpu_percent(interval=0.5, percpu=True)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net_io = psutil.net_io_counters()

    return {
        "cpu": {
            "percent": cpu_percent,
            "per_core": cpu_per_core,
            "count": psutil.cpu_count(),
            "count_logical": psutil.cpu_count(logical=True),
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "free": memory.free,
            "percent": memory.percent,
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
        },
        "network": {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
        },
        "timestamp": int(time.time()),
    }


# ─────────────────────────────────────────────────────────────────
# 告警规则
# ─────────────────────────────────────────────────────────────────
@router.get("/alerts", summary="获取告警规则列表")
def list_alerts(admin: dict = Depends(get_admin_user)):
    with _get_db() as conn:
        rows = conn.execute("SELECT * FROM alert_rules ORDER BY id").fetchall()
    return {"rules": [dict(r) for r in rows]}


@router.post("/alerts", status_code=201, summary="创建告警规则")
def create_alert(request: AlertRuleRequest, admin: dict = Depends(get_admin_user)):
    now = int(time.time())
    with _get_db() as conn:
        cur = conn.execute(
            "INSERT INTO alert_rules (name, metric, threshold, operator, enabled, created_at) VALUES (?,?,?,?,?,?)",
            (request.name, request.metric, request.threshold, request.operator, request.enabled, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM alert_rules WHERE id=?", (cur.lastrowid,)).fetchone()
    _log_audit(admin["id"], admin["username"], "create_alert", target=str(cur.lastrowid),
               detail=f"创建告警规则: {request.name}")
    return dict(row)


@router.put("/alerts/{alert_id}", summary="更新告警规则")
def update_alert(alert_id: int, request: AlertRuleRequest, admin: dict = Depends(get_admin_user)):
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM alert_rules WHERE id=?", (alert_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="告警规则不存在")
        conn.execute(
            "UPDATE alert_rules SET name=?, metric=?, threshold=?, operator=?, enabled=? WHERE id=?",
            (request.name, request.metric, request.threshold, request.operator, request.enabled, alert_id),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM alert_rules WHERE id=?", (alert_id,)).fetchone()
    _log_audit(admin["id"], admin["username"], "update_alert", target=str(alert_id),
               detail=f"更新告警规则: {request.name}")
    return dict(updated)


@router.delete("/alerts/{alert_id}", summary="删除告警规则")
def delete_alert(alert_id: int, admin: dict = Depends(get_admin_user)):
    with _get_db() as conn:
        conn.execute("DELETE FROM alert_rules WHERE id=?", (alert_id,))
        conn.commit()
    _log_audit(admin["id"], admin["username"], "delete_alert", target=str(alert_id))
    return {"message": "告警规则已删除"}


@router.get("/alerts/check", summary="检查告警状态")
def check_alerts(admin: dict = Depends(get_admin_user)):
    """检查所有启用的告警规则，返回触发的告警"""
    with _get_db() as conn:
        rules = conn.execute("SELECT * FROM alert_rules WHERE enabled=1").fetchall()

    triggered = []
    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    metric_values = {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "disk_percent": disk.percent,
    }

    for rule in rules:
        value = metric_values.get(rule["metric"])
        if value is None:
            continue
        is_triggered = False
        if rule["operator"] == "gt" and value > rule["threshold"]:
            is_triggered = True
        elif rule["operator"] == "lt" and value < rule["threshold"]:
            is_triggered = True
        elif rule["operator"] == "gte" and value >= rule["threshold"]:
            is_triggered = True
        elif rule["operator"] == "lte" and value <= rule["threshold"]:
            is_triggered = True

        if is_triggered:
            triggered.append({
                "rule_id": rule["id"],
                "name": rule["name"],
                "metric": rule["metric"],
                "threshold": rule["threshold"],
                "current_value": value,
                "operator": rule["operator"],
                "message": f"{rule['name']}: {rule['metric']} 当前值 {value} {rule['operator']} {rule['threshold']}",
            })
            # 更新最后触发时间
            with _get_db() as conn:
                conn.execute("UPDATE alert_rules SET last_triggered=? WHERE id=?",
                             (int(time.time()), rule["id"]))
                conn.commit()

    return {"triggered": triggered, "total_rules": len(rules), "checked_at": int(time.time())}



# ─────────────────────────────────────────────────────────────────
# 4. 系统参数配置 API
# ─────────────────────────────────────────────────────────────────
@router.get("/config", summary="获取系统配置")
def get_config(admin: dict = Depends(get_admin_user)):
    """获取当前系统运行配置"""
    config = {
        "embedding": {
            "provider": os.getenv("RAG_EMBEDDING_PROVIDER", "hash"),
            "model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            "hash_dimension": os.getenv("RAG_HASH_EMBEDDING_DIM", "384"),
        },
        "retrieval": {
            "top_k": os.getenv("RAG_RETRIEVAL_K", "16"),
            "max_context_chars": os.getenv("RAG_MAX_CONTEXT_CHARS", "24000"),
            "repo_context_doc_limit": os.getenv("RAG_REPO_CONTEXT_DOC_LIMIT", "8"),
            "hybrid_vector_candidates": os.getenv("RAG_HYBRID_VECTOR_CANDIDATES", "48"),
            "hybrid_keyword_candidates": os.getenv("RAG_HYBRID_KEYWORD_CANDIDATES", "800"),
            "hybrid_neighbor_window": os.getenv("RAG_HYBRID_NEIGHBOR_WINDOW", "1"),
        },
        "qdrant": {
            "mode": os.getenv("QDRANT_MODE", "local"),
            "path": os.getenv("QDRANT_PATH", "data/qdrant"),
            "collection": os.getenv("QDRANT_COLLECTION", "github_repo_multi_modal"),
        },
        "llm": {
            "model": os.getenv("LLM_CHAT_MODEL", "gpt-4o"),
            "base_url": os.getenv("LLM_BASE_URL", ""),
            "provider": os.getenv("LLM_PROVIDER", ""),
        },
        "ocr": {
            "enabled": os.getenv("OCR_ENABLED", "true"),
            "langs": os.getenv("OCR_LANGS", "eng+chi_sim"),
        },
        "indexing": {
            "batch_size": os.getenv("RAG_INDEX_BATCH_SIZE", "64"),
            "max_text_file_bytes": os.getenv("RAG_MAX_TEXT_FILE_BYTES", "1048576"),
        },
    }

    # 从数据库获取自定义配置
    with _get_db() as conn:
        rows = conn.execute("SELECT * FROM system_config ORDER BY key").fetchall()
        custom = {r["key"]: {"value": r["value"], "updated_by": r["updated_by"],
                             "updated_at": r["updated_at"], "version": r["version"]} for r in rows}

    return {"runtime": config, "custom": custom}


@router.put("/config", summary="更新系统配置")
def update_config(request: ConfigUpdateRequest, admin: dict = Depends(get_admin_user)):
    """更新系统配置项"""
    # 允许更新的配置项白名单
    allowed_keys = {
        "RAG_RETRIEVAL_K", "RAG_MAX_CONTEXT_CHARS", "RAG_REPO_CONTEXT_DOC_LIMIT",
        "RAG_HYBRID_VECTOR_CANDIDATES", "RAG_HYBRID_KEYWORD_CANDIDATES",
        "RAG_HYBRID_NEIGHBOR_WINDOW", "RAG_EMBEDDING_PROVIDER",
        "OPENAI_EMBEDDING_MODEL", "RAG_HASH_EMBEDDING_DIM",
        "OCR_ENABLED", "OCR_LANGS", "RAG_INDEX_BATCH_SIZE",
    }

    if request.key not in allowed_keys:
        raise HTTPException(status_code=400, detail=f"不允许修改配置项: {request.key}")

    now = int(time.time())
    with _get_db() as conn:
        existing = conn.execute("SELECT * FROM system_config WHERE key=?", (request.key,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE system_config SET value=?, updated_by=?, updated_at=?, version=version+1 WHERE key=?",
                (request.value, admin["username"], now, request.key),
            )
        else:
            conn.execute(
                "INSERT INTO system_config (key, value, updated_by, updated_at, version) VALUES (?,?,?,?,1)",
                (request.key, request.value, admin["username"], now),
            )
        conn.commit()

    # 同时更新环境变量（运行时生效）
    os.environ[request.key] = request.value

    _log_audit(admin["id"], admin["username"], "update_config", target=request.key,
               detail=f"设置 {request.key} = {request.value}")
    return {"message": f"配置 {request.key} 已更新", "key": request.key, "value": request.value}


@router.get("/config/history", summary="配置修改审计日志")
def config_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_admin_user),
):
    """获取配置修改的历史记录"""
    with _get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action='update_config'").fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            "SELECT * FROM audit_logs WHERE action='update_config' ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "logs": [dict(r) for r in rows],
    }


@router.post("/config/rollback/{key}", summary="回滚配置")
def rollback_config(key: str, admin: dict = Depends(get_admin_user)):
    """回滚配置到上一个版本"""
    with _get_db() as conn:
        existing = conn.execute("SELECT * FROM system_config WHERE key=?", (key,)).fetchone()
        if not existing or existing["version"] <= 1:
            raise HTTPException(status_code=400, detail="无法回滚：配置不存在或已是初始版本")

        # 从审计日志中找到上一个值
        prev = conn.execute(
            "SELECT detail FROM audit_logs WHERE action='update_config' AND target=? ORDER BY created_at DESC LIMIT 1 OFFSET 1",
            (key,),
        ).fetchone()
        if not prev:
            raise HTTPException(status_code=400, detail="未找到历史版本")

        # 解析之前的值
        import re
        match = re.search(r"= (.+)$", prev["detail"])
        if not match:
            raise HTTPException(status_code=400, detail="无法解析历史值")

        old_value = match.group(1)
        now = int(time.time())
        conn.execute(
            "UPDATE system_config SET value=?, updated_by=?, updated_at=?, version=version-1 WHERE key=?",
            (old_value, admin["username"], now, key),
        )
        conn.commit()

    os.environ[key] = old_value
    _log_audit(admin["id"], admin["username"], "rollback_config", target=key,
               detail=f"回滚 {key} 到 {old_value}")
    return {"message": f"配置 {key} 已回滚", "key": key, "value": old_value}


@router.get("/stats/overview", summary="系统统计概览")
def stats_overview(admin: dict = Depends(get_admin_user)):
    """获取系统整体统计概览"""
    with _get_db() as conn:
        user_stats = {
            "total": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "active": conn.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0],
            "admins": conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0],
        }
        audit_count = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
        recent_logins = conn.execute(
            "SELECT username, created_at FROM audit_logs WHERE action IN ('admin_login','admin_register') ORDER BY created_at DESC LIMIT 5"
        ).fetchall()

    # Qdrant 统计
    kb_stats = {"total_points": 0, "repos": 0}
    try:
        from src.retrieval.vector_store import get_qdrant_client, COLLECTION_NAME
        client = get_qdrant_client()
        if client.collection_exists(COLLECTION_NAME):
            info = client.get_collection(COLLECTION_NAME)
            kb_stats["total_points"] = info.points_count
    except Exception:
        pass

    return {
        "users": user_stats,
        "audit_logs_count": audit_count,
        "recent_logins": [dict(r) for r in recent_logins],
        "knowledge_base": kb_stats,
    }
