import datetime
import hashlib
import secrets
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.config import get_settings
from backend.models import User, Session, AccessKey
from backend.redis_client import get_redis

ALGORITHM = "HS256"


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_session_token() -> str:
    return secrets.token_urlsafe(48)


def create_jwt(user_id: int, is_admin: bool = False) -> str:
    settings = get_settings()
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=settings.token_expire_hours)
    payload = {
        "sub": str(user_id),
        "admin": is_admin,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_jwt(token: str) -> dict | None:
    try:
        return jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


async def _create_session(user, db, ip, user_agent):
    """Create JWT session for user, save to DB and Redis."""
    settings = get_settings()
    is_admin = user.is_admin
    token = create_jwt(user.id, is_admin)
    expires = datetime.datetime.utcnow() + datetime.timedelta(hours=settings.token_expire_hours)

    session = Session(
        user_id=user.id,
        token=token,
        ip_address=ip,
        user_agent=user_agent,
        expires_at=expires,
    )
    db.add(session)
    user.last_seen = datetime.datetime.utcnow()
    await db.commit()

    r = await get_redis()
    await r.setex(
        f"session:{user.id}",
        settings.token_expire_hours * 3600,
        token,
    )

    return {
        "token": token,
        "user_id": user.id,
        "username": user.username,
        "is_admin": is_admin,
        "can_create_languages": user.can_create_languages or is_admin,
    }


async def authenticate_login(
    username: str,
    password: str,
    db: AsyncSession,
    code: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    telegram_id: int | None = None,
    telegram_username: str | None = None,
) -> dict | None:
    """
    Auth flow:
    1. Existing user + correct password → login (no code needed)
    2. New user → code required (admin secret / env code / one-time DB key)
       Password is what the user chose freely, code validates registration.
    """
    settings = get_settings()
    username = username.strip()
    password = password.strip()

    if not username or not password:
        return None

    pw_hash = _hash_password(password)

    # --- 1. Try existing user login ---
    result = await db.execute(
        select(User).where(User.username == username)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user and existing_user.password_hash:
        if existing_user.password_hash == pw_hash:
            if telegram_id and not existing_user.telegram_id:
                existing_user.telegram_id = telegram_id
            if telegram_username and not existing_user.telegram_username:
                existing_user.telegram_username = telegram_username
            return await _create_session(existing_user, db, ip, user_agent)
        else:
            return None  # wrong password

    # --- 2. Registration — need a valid code ---
    if not code:
        return None  # no code = can't register

    code = code.strip()

    # Check admin secret
    is_admin = code.lower() == settings.admin_secret.lower()

    # Check env access codes
    valid_code = is_admin or code.lower() in settings.access_code_list

    # Check one-time DB keys
    activated_key = None
    if not valid_code:
        result = await db.execute(
            select(AccessKey).where(
                AccessKey.key == code,
                AccessKey.is_used == False,
            )
        )
        ak = result.scalar_one_or_none()
        if ak:
            ak.is_used = True
            ak.used_at = datetime.datetime.utcnow()
            ak.used_by_ip = ip
            ak.used_by_telegram = telegram_username
            activated_key = ak
            valid_code = True

    if not valid_code:
        return None

    # --- 3. Create new user or set password on existing ---
    if existing_user:
        existing_user.password_hash = pw_hash
        if is_admin:
            existing_user.is_admin = True
        if telegram_id and not existing_user.telegram_id:
            existing_user.telegram_id = telegram_id
        if activated_key:
            activated_key.used_by = existing_user.id
            activated_key.used_by_username = existing_user.username
        return await _create_session(existing_user, db, ip, user_agent)

    user = User(
        username=username,
        password_hash=pw_hash,
        telegram_id=telegram_id,
        telegram_username=telegram_username,
        access_code_used=code.lower(),
        is_admin=is_admin,
    )
    db.add(user)
    await db.flush()

    if activated_key:
        activated_key.used_by = user.id
        activated_key.used_by_username = user.username

    return await _create_session(user, db, ip, user_agent)


async def authenticate_code(
    code: str,
    db: AsyncSession,
    ip: str | None = None,
    user_agent: str | None = None,
    telegram_id: int | None = None,
    telegram_username: str | None = None,
) -> dict | None:
    """Legacy code-only auth (used by bot)."""
    settings = get_settings()
    code_lower = code.strip().lower()

    is_admin = code_lower == settings.admin_secret.lower()
    valid_code = is_admin or code_lower in settings.access_code_list

    activated_key = None
    if not valid_code:
        result = await db.execute(
            select(AccessKey).where(
                AccessKey.key == code.strip(),
                AccessKey.is_used == False,
            )
        )
        ak = result.scalar_one_or_none()
        if ak:
            ak.is_used = True
            ak.used_at = datetime.datetime.utcnow()
            ak.used_by_ip = ip
            ak.used_by_telegram = telegram_username
            activated_key = ak
            valid_code = True

    if not valid_code:
        return None

    user = None
    if telegram_id:
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

    if not user:
        user = User(
            username=telegram_username or f"anon_{secrets.token_hex(4)}",
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            access_code_used=code_lower,
            is_admin=is_admin,
        )
        db.add(user)
        await db.flush()
    else:
        user.last_seen = datetime.datetime.utcnow()
        if is_admin:
            user.is_admin = True

    if activated_key:
        activated_key.used_by = user.id
        activated_key.used_by_username = user.username

    return await _create_session(user, db, ip, user_agent)


async def get_current_user(token: str, db: AsyncSession) -> User | None:
    payload = decode_jwt(token)
    if not payload:
        return None
    user_id = int(payload["sub"])

    # Check Redis cache first
    r = await get_redis()
    cached = await r.get(f"session:{user_id}")
    if cached and cached != token:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
