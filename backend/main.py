from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from pathlib import Path

from backend.config import get_settings
from backend.database import get_db, init_db
from backend.redis_client import get_redis, close_redis
from backend.models import User, Language, EncodeLog, AccessKey
from backend.auth import authenticate_code, authenticate_login, get_current_user, decode_jwt


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_redis()


app = FastAPI(title="Emojirean", lifespan=lifespan)

PROJECT_DIR = Path(__file__).parent.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"


# --- Static files ---
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")


# --- Helpers ---
async def require_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "not authenticated")
    token = authorization.split(" ", 1)[1]
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(401, "invalid or expired session")
    return user


async def require_admin(user: User = Depends(require_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "admin only")
    return user


# --- Auth ---
class AuthRequest(BaseModel):
    username: str | None = None
    password: str | None = None
    code: str | None = None  # legacy: bot uses code-only auth
    telegram_id: int | None = None
    telegram_username: str | None = None


class AuthResponse(BaseModel):
    token: str
    user_id: int
    username: str
    is_admin: bool
    can_create_languages: bool


@app.post("/api/auth", response_model=AuthResponse)
async def auth(
    body: AuthRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    tg_id = body.telegram_id
    tg_user = body.telegram_username

    # New flow: username + password (web app)
    if body.username and body.password:
        result = await authenticate_login(
            username=body.username,
            password=body.password,
            db=db,
            code=body.code,
            ip=ip,
            user_agent=ua,
            telegram_id=tg_id,
            telegram_username=tg_user,
        )
        if not result:
            raise HTTPException(403, "identity rejected")
        return result

    # Legacy flow: code only (bot, old clients)
    if body.code:
        result = await authenticate_code(
            code=body.code,
            db=db,
            ip=ip,
            user_agent=ua,
            telegram_id=tg_id,
            telegram_username=tg_user,
        )
        if not result:
            raise HTTPException(403, "identity rejected")
        return result

    raise HTTPException(400, "username+password or code required")


# --- User info ---
@app.get("/api/me")
async def me(user: User = Depends(require_user)):
    return {
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "can_create_languages": user.can_create_languages or user.is_admin,
        "telegram_username": user.telegram_username,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


# --- Languages CRUD ---
class LanguageSave(BaseModel):
    lang_id: str
    name: str
    token_data: dict
    token_b64: str
    mode: str = "ru"


@app.post("/api/languages")
async def save_language(
    body: LanguageSave,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    # Check if exists
    result = await db.execute(
        select(Language).where(Language.lang_id == body.lang_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        if existing.creator_id != user.id and not user.is_admin:
            raise HTTPException(403, "not your language")
        existing.token_data = body.token_data
        existing.token_b64 = body.token_b64
        existing.name = body.name
    else:
        lang = Language(
            lang_id=body.lang_id,
            name=body.name,
            creator_id=user.id,
            token_data=body.token_data,
            token_b64=body.token_b64,
            mode=body.mode,
        )
        db.add(lang)

    await db.commit()
    return {"ok": True}


@app.get("/api/languages")
async def list_languages(user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Language).where(Language.creator_id == user.id).order_by(desc(Language.created_at))
    )
    langs = result.scalars().all()
    return [
        {
            "lang_id": l.lang_id,
            "name": l.name,
            "token_b64": l.token_b64,
            "mode": l.mode,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in langs
    ]


@app.delete("/api/languages/{lang_id}")
async def delete_language(lang_id: str, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Language).where(Language.lang_id == lang_id))
    lang = result.scalar_one_or_none()
    if not lang:
        raise HTTPException(404)
    if lang.creator_id != user.id and not user.is_admin:
        raise HTTPException(403)
    await db.delete(lang)
    await db.commit()
    return {"ok": True}


# --- Encode log ---
class EncodeLogEntry(BaseModel):
    language_id: str | None = None
    char_count: int = 0
    emoji_count: int = 0
    source: str = "web"


@app.post("/api/encode-log")
async def log_encode(
    body: EncodeLogEntry,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    entry = EncodeLog(
        user_id=user.id,
        language_id=body.language_id,
        char_count=body.char_count,
        emoji_count=body.emoji_count,
        source=body.source,
    )
    db.add(entry)
    await db.commit()

    # Increment Redis counter
    r = await get_redis()
    await r.incr("emojirean:total_encodes")
    return {"ok": True}


# --- Admin ---
@app.get("/api/admin/users")
async def admin_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).order_by(desc(User.last_seen)).limit(200)
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "telegram_id": u.telegram_id,
            "telegram_username": u.telegram_username,
            "access_code_used": u.access_code_used,
            "is_admin": u.is_admin,
            "can_create_languages": u.can_create_languages,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_seen": u.last_seen.isoformat() if u.last_seen else None,
        }
        for u in users
    ]


@app.get("/api/admin/stats")
async def admin_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user_count = await db.scalar(select(func.count(User.id)))
    lang_count = await db.scalar(select(func.count(Language.id)))
    encode_count = await db.scalar(select(func.count(EncodeLog.id)))

    r = await get_redis()
    total_encodes = await r.get("emojirean:total_encodes") or encode_count

    return {
        "total_users": user_count,
        "total_languages": lang_count,
        "total_encodes": int(total_encodes),
    }


@app.post("/api/admin/users/{user_id}/toggle-create")
async def admin_toggle_create(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404)
    user.can_create_languages = not user.can_create_languages
    await db.commit()
    return {"ok": True, "can_create_languages": user.can_create_languages}


# --- Access Keys ---
import secrets as _secrets


class KeyGenRequest(BaseModel):
    count: int = 1
    note: str | None = None


@app.post("/api/admin/keys/generate")
async def generate_keys(
    body: KeyGenRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    count = min(body.count, 50)
    keys = []
    for _ in range(count):
        key = _secrets.token_urlsafe(12)
        ak = AccessKey(key=key, created_by=admin.id, note=body.note)
        db.add(ak)
        keys.append(key)
    await db.commit()
    return {"keys": keys}


@app.get("/api/admin/keys")
async def list_keys(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AccessKey).order_by(desc(AccessKey.created_at)).limit(200)
    )
    keys = result.scalars().all()
    return [
        {
            "id": k.id,
            "key": k.key,
            "is_used": k.is_used,
            "used_by_username": k.used_by_username,
            "used_by_telegram": k.used_by_telegram,
            "used_by_ip": k.used_by_ip,
            "note": k.note,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "used_at": k.used_at.isoformat() if k.used_at else None,
        }
        for k in keys
    ]


class KeyActivateRequest(BaseModel):
    key: str
    username: str | None = None
    telegram_username: str | None = None


@app.post("/api/keys/activate")
async def activate_key(
    body: KeyActivateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AccessKey).where(AccessKey.key == body.key.strip())
    )
    ak = result.scalar_one_or_none()
    if not ak:
        raise HTTPException(404, "ключ не найден")
    if ak.is_used:
        raise HTTPException(410, "ключ уже использован")

    import datetime
    ak.is_used = True
    ak.used_at = datetime.datetime.utcnow()
    ak.used_by_username = body.username
    ak.used_by_telegram = body.telegram_username
    ak.used_by_ip = request.client.host if request.client else None
    await db.commit()
    return {"ok": True, "key": ak.key}


@app.delete("/api/admin/keys/{key_id}")
async def delete_key(
    key_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AccessKey).where(AccessKey.id == key_id))
    ak = result.scalar_one_or_none()
    if not ak:
        raise HTTPException(404)
    await db.delete(ak)
    await db.commit()
    return {"ok": True}


# --- HTML pages ---
@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return FileResponse(str(FRONTEND_DIR / "admin.html"))


@app.get("/MUSIC 5.mp3")
async def music_file():
    return FileResponse(str(PROJECT_DIR / "MUSIC 5.mp3"), media_type="audio/mpeg")
