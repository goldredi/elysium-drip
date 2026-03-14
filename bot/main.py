"""
Emojirean Telegram Bot
- /start: приветствие
- /help: список команд
- /token <base64>: загрузить токен
- /encode <текст>: закодировать
- /decode: расшифровать (ответ на сообщение)
- /key <ключ>: активировать ключ доступа
- /admin: панель админа (кнопки)
- Пересылка эмоджи → автодекод
- Отправка ключа без команды → автоактивация
- Inline: @bot <текст> → зашифрованные варианты
"""

import os
import re
import logging
from uuid import uuid4

import redis as _redis_sync

from telegram import (
    Update, InlineQueryResultArticle, InputTextMessageContent,
    InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo,
)
from telegram.ext import (
    Application, CommandHandler, InlineQueryHandler,
    MessageHandler, CallbackQueryHandler, ContextTypes, filters,
)

from bot.engine import (
    decode_token, encode_token, encode_text, encode_compressed,
    decode_text, build_rows, rows_to_shaped, rows_to_flat,
    parse_emojis, generate_token, add_nulls, pad_to_grid,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage
user_tokens: dict[int, dict] = {}
activated_users: set[int] = set()

# Global shared token — one for all users
global_token: dict | None = None

# Admin telegram IDs
ADMIN_IDS: set[int] = set()

# Track admin states for multi-step flows
admin_state: dict[int, dict] = {}


def _load_admin_ids():
    raw = os.environ.get("ADMIN_TELEGRAM_IDS", "")
    for x in raw.split(","):
        x = x.strip()
        if x.isdigit():
            ADMIN_IDS.add(int(x))


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def _get_lang(user_id: int) -> dict | None:
    """Get user's token — personal or global fallback."""
    return user_tokens.get(user_id) or global_token


REDIS_TOKEN_KEY = "emojirean:global_token_b64"
REDIS_ENCODE_KEY = "emojirean:total_encodes"


def _load_global_token_from_redis() -> dict | None:
    """Load global token from Redis (sync, for startup)."""
    redis_url = os.environ.get("REDIS_URL", "redis://:redis_secret@localhost:6379/0")
    try:
        r = _redis_sync.from_url(redis_url)
        b64 = r.get(REDIS_TOKEN_KEY)
        r.close()
        if b64:
            return decode_token(b64.decode() if isinstance(b64, bytes) else b64)
    except Exception as e:
        logger.warning(f"Failed to load token from Redis: {e}")
    return None


def _save_global_token_to_redis(lang: dict):
    """Save global token to Redis (sync)."""
    redis_url = os.environ.get("REDIS_URL", "redis://:redis_secret@localhost:6379/0")
    try:
        b64 = encode_token(lang)
        r = _redis_sync.from_url(redis_url)
        r.set(REDIS_TOKEN_KEY, b64)
        r.close()
    except Exception as e:
        logger.warning(f"Failed to save token to Redis: {e}")


def _incr_encode_count():
    """Increment global encode counter in Redis."""
    redis_url = os.environ.get("REDIS_URL", "redis://:redis_secret@localhost:6379/0")
    try:
        r = _redis_sync.from_url(redis_url)
        r.incr(REDIS_ENCODE_KEY)
        r.close()
    except Exception:
        pass


async def _admin_auth(session, user_id: int):
    """Get JWT token for admin API calls."""
    backend_url = os.environ.get("BACKEND_URL", "http://backend:8000")
    admin_secret = os.environ.get("ADMIN_SECRET", "")
    resp = await session.post(
        f"{backend_url}/api/auth",
        json={"code": admin_secret, "telegram_id": user_id},
    )
    if resp.status != 200:
        return None
    data = await resp.json()
    return data.get("token")


# Track users waiting for one-time code input
awaiting_code: set[int] = set()


# ── /start ──

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # If already activated — show welcome with token
    if user_id in activated_users:
        webapp_url = os.environ.get("WEBAPP_URL", "")
        kb = []
        if webapp_url:
            kb.append([InlineKeyboardButton(
                "Открыть Emojirean",
                web_app=WebAppInfo(url=webapp_url),
            )])

        lang = _get_lang(user_id)
        token_info = ""
        if lang:
            token_info = f"\n\n// активный токен: {lang.get('name', '?').lower()}"

        await update.message.reply_text(
            "emojirean // #няшныйдвиж\n\n"
            "С возвращением.\n"
            "Токен — это ключ, слово — это дверь.\n\n"
            "Напиши /help чтобы увидеть команды."
            f"{token_info}",
            reply_markup=InlineKeyboardMarkup(kb) if kb else None,
        )
        return

    # New user — ask for one-time code
    awaiting_code.add(user_id)
    await update.message.reply_text(
        "emojirean // #няшныйдвиж\n\n"
        "Тайный язык.\n"
        "Токен — это ключ, слово — это дверь.\n\n"
        "// отправь мне одноразовый код доступа"
    )


# ── /help ──

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "// команды emojirean\n\n"
        "/start — приветствие\n"
        "/help — этот список\n\n"
        "ТОКЕН:\n"
        "/token <base64> — загрузить токен\n\n"
        "КОДИРОВАНИЕ:\n"
        "/encode <текст> — закодировать\n"
        "/decode — ответь на сообщение\n\n"
        "ДОСТУП:\n"
        "Просто отправь ключ доступа боту — он активируется автоматически.\n\n"
        "INLINE:\n"
        "В любом чате: @имя_бота <текст>\n"
    )

    await update.message.reply_text(text)


# ── /token ──

async def load_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "// вставь токен после /token\n"
            "/token eyJpIjo..."
        )
        return

    b64 = ' '.join(context.args)
    lang = decode_token(b64)

    if not lang:
        await update.message.reply_text("// ✗ неверный токен — проверь формат")
        return

    user_id = update.effective_user.id
    user_tokens[user_id] = lang

    name = lang.get('name', 'UNKNOWN')
    mode = lang.get('mode', 'ru')
    lang_type = lang.get('type', 'master')
    letters_count = len(lang.get('letters', lang.get('rev_mapping', {})))
    bigrams_count = len(lang.get('bigrams', {}))
    deco_names = ['WING', 'BOX', 'MATH', 'RUNE', 'BRAILLE']
    deco = deco_names[lang.get('decoStyle', 0) % 5]
    has_crypto = bool(lang.get('byteMap'))

    await update.message.reply_text(
        f"// ✓ токен загружен\n\n"
        f"имя: {name.lower()}\n"
        f"тип: {lang_type}\n"
        f"режим: {mode}\n"
        f"символы: {letters_count} | биграммы: {bigrams_count}\n"
        f"деко: {deco}\n"
        f"сжатие: {'да' if has_crypto else 'нет'}\n\n"
        f"{'Используй /encode <текст> или inline режим.' if lang_type == 'master' else 'Reader токен — только декодирование.'}"
    )


# ── /encode ──

async def encode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = _get_lang(user_id)

    if not lang:
        await update.message.reply_text("// токен не загружен\n/token <base64>")
        return

    if lang.get('type') == 'reader':
        await update.message.reply_text("// reader токен — кодирование недоступно")
        return

    text = ' '.join(context.args) if context.args else ''
    if not text:
        await update.message.reply_text("// /encode <текст>")
        return

    letter_enc = encode_text(text, lang)
    comp_enc = encode_compressed(text, lang)
    if comp_enc and len(comp_enc) < len(letter_enc):
        emojis = comp_enc
        mode_label = "СЖАТИЕ"
    else:
        emojis = letter_enc
        emojis = add_nulls(emojis, lang.get('nullEmojis', []), 0.3)
        mode_label = "БУКВЫ"

    if not emojis:
        await update.message.reply_text("// ✗ ошибка кодирования")
        return

    emojis = pad_to_grid(emojis, lang.get('nullEmojis', []))
    rows = build_rows(emojis, 'grid')
    shaped = rows_to_shaped(rows, lang.get('decoStyle', 0))

    _incr_encode_count()
    await update.message.reply_text(
        f"{shaped}\n\n"
        f"// {mode_label} · {lang.get('name', '?').lower()}"
    )


# ── /decode ──

async def decode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = _get_lang(user_id)

    if not lang:
        await update.message.reply_text("// токен не загружен\n/token <base64>")
        return

    raw = None
    if update.message.reply_to_message and update.message.reply_to_message.text:
        raw = update.message.reply_to_message.text
    elif context.args:
        raw = ' '.join(context.args)

    if not raw:
        await update.message.reply_text(
            "// ответь на сообщение с /decode\n"
            "// или: /decode 🦊🐺🌸..."
        )
        return

    emojis = parse_emojis(raw)
    result = decode_text(emojis, lang)

    if result:
        await update.message.reply_text(
            f"// ✓ расшифровано\n\n{result}\n\n"
            f"// {len(emojis)} символов"
        )
    else:
        await update.message.reply_text("// ✗ не удалось расшифровать — неправильный токен?")


# ── /admin — admin panel with inline buttons ──

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        await update.message.reply_text("// доступ запрещён")
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Сгенерировать ключ", callback_data="admin_genkey")],
        [InlineKeyboardButton("🔑 Сгенерировать 5 ключей", callback_data="admin_genkey5")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📋 Список ключей", callback_data="admin_keys")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
    ])

    await update.message.reply_text(
        "// admin panel\n\nВыбери действие:",
        reply_markup=kb,
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not _is_admin(user_id):
        await query.answer("Доступ запрещён", show_alert=True)
        return

    await query.answer()
    data = query.data

    import aiohttp
    backend_url = os.environ.get("BACKEND_URL", "http://backend:8000")

    if data == "admin_genkey" or data == "admin_genkey5":
        count = 5 if data == "admin_genkey5" else 1
        try:
            async with aiohttp.ClientSession() as session:
                jwt = await _admin_auth(session, user_id)
                if not jwt:
                    await query.edit_message_text("// ошибка авторизации")
                    return

                resp = await session.post(
                    f"{backend_url}/api/admin/keys/generate",
                    json={"count": count, "note": "из бота"},
                    headers={"Authorization": f"Bearer {jwt}"},
                )
                if resp.status != 200:
                    await query.edit_message_text("// ✗ ошибка генерации")
                    return
                result = await resp.json()
                keys = result["keys"]

                keys_text = '\n'.join(f'`{k}`' for k in keys)
                await query.edit_message_text(
                    f"// ✓ {len(keys)} ключ(ей) сгенерировано\n\n{keys_text}\n\n"
                    f"Отправь ключ человеку — он просто скинет его боту.",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.error(f"Admin genkey error: {e}")
            await query.edit_message_text("// ✗ сервер недоступен")

    elif data == "admin_stats":
        try:
            async with aiohttp.ClientSession() as session:
                jwt = await _admin_auth(session, user_id)
                if not jwt:
                    await query.edit_message_text("// ошибка авторизации")
                    return

                keys_resp = await session.get(
                    f"{backend_url}/api/admin/keys",
                    headers={"Authorization": f"Bearer {jwt}"},
                )
                keys = await keys_resp.json() if keys_resp.status == 200 else []

                stats_resp = await session.get(
                    f"{backend_url}/api/admin/stats",
                    headers={"Authorization": f"Bearer {jwt}"},
                )
                stats = await stats_resp.json() if stats_resp.status == 200 else {}

                total = len(keys)
                used = sum(1 for k in keys if k.get('is_used'))
                active = total - used

                text = (
                    f"// статистика emojirean\n\n"
                    f"КЛЮЧИ: {total} всего · {active} активных · {used} использовано\n"
                    f"ПОЛЬЗОВАТЕЛИ: {stats.get('total_users', '?')}\n"
                    f"ЯЗЫКИ: {stats.get('total_languages', '?')}\n"
                    f"КОДИРОВАНИЙ: {stats.get('total_encodes', '?')}\n"
                    f"ТОКЕНОВ В БОТЕ: {len(user_tokens)} загружено"
                )
                await query.edit_message_text(text)
        except Exception as e:
            logger.error(f"Admin stats error: {e}")
            await query.edit_message_text("// ✗ сервер недоступен")

    elif data == "admin_keys":
        try:
            async with aiohttp.ClientSession() as session:
                jwt = await _admin_auth(session, user_id)
                if not jwt:
                    await query.edit_message_text("// ошибка авторизации")
                    return

                resp = await session.get(
                    f"{backend_url}/api/admin/keys",
                    headers={"Authorization": f"Bearer {jwt}"},
                )
                if resp.status != 200:
                    await query.edit_message_text("// ✗ ошибка получения ключей")
                    return
                keys = await resp.json()

                if not keys:
                    await query.edit_message_text("// ключей нет")
                    return

                text = "// список ключей\n\n"

                used_keys = [k for k in keys if k.get('is_used')]
                if used_keys:
                    text += "ИСПОЛЬЗОВАННЫЕ:\n"
                    for k in used_keys[:15]:
                        who = k.get('used_by_username', '?')
                        tg = k.get('used_by_telegram', '')
                        when = k.get('used_at', '?')[:10] if k.get('used_at') else '?'
                        text += f"  {k['key'][:8]}… → {who}"
                        if tg:
                            text += f" (@{tg})"
                        text += f" · {when}\n"

                unused_keys = [k for k in keys if not k.get('is_used')]
                if unused_keys:
                    text += f"\nАКТИВНЫЕ ({len(unused_keys)}):\n"
                    for k in unused_keys[:15]:
                        note = k.get('note', '')
                        text += f"  `{k['key']}`"
                        if note:
                            text += f" ({note})"
                        text += "\n"

                await query.edit_message_text(text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Admin keys error: {e}")
            await query.edit_message_text("// ✗ сервер недоступен")

    elif data == "admin_users":
        try:
            async with aiohttp.ClientSession() as session:
                jwt = await _admin_auth(session, user_id)
                if not jwt:
                    await query.edit_message_text("// ошибка авторизации")
                    return

                resp = await session.get(
                    f"{backend_url}/api/admin/users",
                    headers={"Authorization": f"Bearer {jwt}"},
                )
                if resp.status != 200:
                    await query.edit_message_text("// ✗ ошибка получения пользователей")
                    return
                users = await resp.json()

                # Filter out anon test users (created by curl tests etc)
                real_users = [u for u in users if u.get('telegram_username') or (u.get('username') and not u['username'].startswith('anon_'))]

                if not real_users:
                    await query.edit_message_text("// пользователей нет")
                    return

                text = f"// пользователи ({len(real_users)})\n\n"
                for u in real_users[:25]:
                    name = u.get('username', '?')
                    tg = u.get('telegram_username')
                    code = u.get('access_code_used', '?')
                    admin = " 👑" if u.get('is_admin') else ""
                    tg_str = f" @{tg}" if tg else ""
                    # Shorten access code for display
                    if len(code) > 12:
                        code = code[:8] + "…"
                    text += f"  {name}{tg_str}{admin}\n    ключ: {code}\n"

                await query.edit_message_text(text)
        except Exception as e:
            logger.error(f"Admin users error: {e}")
            await query.edit_message_text("// ✗ сервер недоступен")


# ── Auto-handle: forwarded emoji messages + key activation ──

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages:
    1. If looks like access key → auto activate
    2. If has many emojis and user has token → auto decode
    3. If plain text and user has token → auto encode (art mode)
    """
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not text:
        return

    # 0. If user just did /start and is sending their one-time code
    if user_id in awaiting_code:
        awaiting_code.discard(user_id)
        user = update.effective_user
        import aiohttp
        backend_url = os.environ.get("BACKEND_URL", "http://backend:8000")
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    f"{backend_url}/api/auth",
                    json={
                        "code": text,
                        "telegram_id": user_id,
                        "telegram_username": user.username or str(user_id),
                    },
                )
                if resp.status == 200:
                    activated_users.add(user_id)
                    lang = _get_lang(user_id) or global_token
                    token_info = ""
                    if lang:
                        deco_names = ['WING', 'BOX', 'MATH', 'RUNE', 'BRAILLE']
                        deco = deco_names[lang.get('decoStyle', 0) % 5]
                        token_info = f"\n// активный токен: {lang.get('name', '?').lower()} · деко: {deco}"

                    webapp_url = os.environ.get("WEBAPP_URL", "")
                    kb = []
                    if webapp_url:
                        kb.append([InlineKeyboardButton(
                            "Открыть Emojirean",
                            web_app=WebAppInfo(url=webapp_url),
                        )])

                    await update.message.reply_text(
                        "// ✓ код принят\n\n"
                        "добро пожаловать в emojirean.\n"
                        "машина флекса запущена.\n\n"
                        "просто пиши мне текст — я зашифрую.\n"
                        "скинь эмоджи — я расшифрую.\n\n"
                        "зайди в веб-приложение для полного доступа."
                        f"{token_info}",
                        reply_markup=InlineKeyboardMarkup(kb) if kb else None,
                    )
                    return
                else:
                    await update.message.reply_text(
                        "// ✗ код не подходит\n"
                        "// попробуй ещё раз или попроси новый код у админа"
                    )
                    awaiting_code.add(user_id)  # let them retry
                    return
        except Exception as e:
            logger.error(f"Code activation error: {e}")
            await update.message.reply_text("// ✗ сервер недоступен, попробуй позже")
            awaiting_code.add(user_id)
            return

    # 1. Try auto-activate key: alphanumeric string, 8-24 chars, no spaces
    if re.match(r'^[a-zA-Z0-9_\\-]{8,24}$', text) and user_id not in activated_users:
        user = update.effective_user
        import aiohttp
        backend_url = os.environ.get("BACKEND_URL", "http://backend:8000")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{backend_url}/api/keys/activate",
                    json={
                        "key": text,
                        "username": user.full_name,
                        "telegram_username": user.username or str(user.id),
                    },
                ) as resp:
                    if resp.status == 200:
                        activated_users.add(user_id)
                        # Use global token — everyone shares the same language
                        lang = global_token
                        token_info = ""
                        if lang:
                            deco_names = ['WING', 'BOX', 'MATH', 'RUNE', 'BRAILLE']
                            deco = deco_names[lang.get('decoStyle', 0) % 5]
                            token_info = f"\nдеко: {deco}"

                        await update.message.reply_text(
                            "// ✓ ключ активирован\n\n"
                            "машина флекса запущена.\n"
                            "ты уже можешь использовать её для кодировки и декодинга.\n\n"
                            f"// глобальный токен: {lang.get('name', '?') if lang else '?'}{token_info}\n\n"
                            f"// просто пиши мне текст — я зашифрую.\n"
                            f"// скинь эмоджи — я расшифрую.",
                            parse_mode="Markdown",
                        )
                        return
                    elif resp.status == 410:
                        await update.message.reply_text(
                            "// ✗ этот ключ уже был использован\n"
                            "// попроси новый ключ у админа"
                        )
                        return
                    elif resp.status == 404:
                        pass  # not a key, continue
        except Exception as e:
            logger.error(f"Auto key activation error: {e}")

    # Need token for encode/decode
    lang = _get_lang(user_id)
    if not lang:
        return

    # 2. Check if message is mostly emojis → auto decode
    emojis = parse_emojis(text)
    emoji_count = sum(1 for e in emojis if len(e.encode('utf-8')) > 3 or ord(e[0]) > 0x2600)
    total_chars = max(len(emojis), 1)

    if emoji_count >= 3 and emoji_count / total_chars > 0.3:
        result = decode_text(emojis, lang)
        if result and len(result) >= 2:
            await update.message.reply_text(
                f"// ✓ расшифровано\n\n{result}\n\n"
                f"// {len(emojis)} символов"
            )
            return

    # 3. Plain text → auto encode in art mode
    if lang.get('type') == 'reader':
        return  # reader can't encode

    # Skip very short or single-word messages that look like commands/noise
    if len(text) < 2:
        return

    letter_enc = encode_text(text, lang)
    comp_enc = encode_compressed(text, lang)
    if comp_enc and len(comp_enc) < len(letter_enc):
        encoded = comp_enc
        mode_label = "СЖАТИЕ"
    else:
        encoded = letter_enc
        encoded = add_nulls(encoded, lang.get('nullEmojis', []), 0.3)
        mode_label = "БУКВЫ"

    if not encoded:
        return

    encoded = pad_to_grid(encoded, lang.get('nullEmojis', []))
    rows = build_rows(encoded, 'grid')
    shaped = rows_to_shaped(rows, lang.get('decoStyle', 0))

    _incr_encode_count()
    await update.message.reply_text(
        f"{shaped}\n\n"
        f"// {mode_label}"
    )


# ── Inline mode ──

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    user_id = update.effective_user.id
    lang = _get_lang(user_id)

    if not query:
        await update.inline_query.answer(
            results=[],
            switch_pm_text="Сначала загрузи токен" if not lang else "Набери текст для кодирования",
            switch_pm_parameter="start",
            cache_time=5,
        )
        return

    if not lang or lang.get('type') == 'reader':
        await update.inline_query.answer(
            results=[InlineQueryResultArticle(
                id=str(uuid4()),
                title="Токен не загружен",
                description="Напиши /token <base64> в ЛС бота",
                input_message_content=InputTextMessageContent("// нужен токен"),
            )],
            cache_time=5,
        )
        return

    results = []

    nulls = lang.get('nullEmojis', [])

    # GRID
    emojis1 = encode_text(query, lang)
    comp1 = encode_compressed(query, lang)
    if comp1 and len(comp1) < len(emojis1):
        emojis1 = comp1
    else:
        emojis1 = add_nulls(emojis1, nulls, 0.3)
    if emojis1:
        emojis1 = pad_to_grid(emojis1, nulls)
        rows1 = build_rows(emojis1, 'grid')
        shaped1 = rows_to_shaped(rows1, lang.get('decoStyle', 0))
        results.append(InlineQueryResultArticle(
            id=str(uuid4()),
            title=f"GRID | {len(emojis1)} символов",
            description=shaped1[:60] + '...',
            input_message_content=InputTextMessageContent(shaped1),
        ))

    # FLAT
    emojis2 = encode_text(query, lang)
    comp2 = encode_compressed(query, lang)
    if comp2 and len(comp2) < len(emojis2):
        emojis2 = comp2
    else:
        emojis2 = add_nulls(emojis2, nulls, 0.3)
    if emojis2:
        flat2 = ''.join(emojis2)
        results.append(InlineQueryResultArticle(
            id=str(uuid4()),
            title=f"FLAT | {len(emojis2)} символов",
            description=flat2[:60] + '...',
            input_message_content=InputTextMessageContent(flat2),
        ))

    # DIAMOND
    emojis3 = encode_text(query, lang)
    comp3 = encode_compressed(query, lang)
    if comp3 and len(comp3) < len(emojis3):
        emojis3 = comp3
    else:
        emojis3 = add_nulls(emojis3, nulls, 0.3)
    if emojis3:
        emojis3 = pad_to_grid(emojis3, nulls)
        rows3 = build_rows(emojis3, 'diamond')
        shaped3 = rows_to_shaped(rows3, lang.get('decoStyle', 0))
        results.append(InlineQueryResultArticle(
            id=str(uuid4()),
            title=f"DIAMOND | {len(emojis3)} символов",
            description=shaped3[:60] + '...',
            input_message_content=InputTextMessageContent(shaped3),
        ))

    if results:
        _incr_encode_count()
    await update.inline_query.answer(results=results, cache_time=0)


# ── /settoken — admin sets global token ──

async def settoken_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return

    global global_token
    b64 = ' '.join(context.args).strip() if context.args else ''
    if not b64:
        await update.message.reply_text(
            "// /settoken <base64> — установить глобальный токен для всех\n"
            "// /newtoken — сгенерировать новый глобальный токен"
        )
        return

    lang = decode_token(b64)
    if not lang:
        await update.message.reply_text("// ✗ невалидный токен")
        return

    global_token = lang
    _save_global_token_to_redis(lang)
    # Clear personal tokens so everyone uses the global one
    user_tokens.clear()

    deco_names = ['WING', 'BOX', 'MATH', 'RUNE', 'BRAILLE']
    deco = deco_names[lang.get('decoStyle', 0) % 5]

    await update.message.reply_text(
        f"// ✓ глобальный токен установлен\n\n"
        f"язык: {lang.get('name', '?')}\n"
        f"деко: {deco}\n"
        f"// все юзеры теперь используют этот токен"
    )


async def newtoken_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return

    global global_token
    name = ' '.join(context.args).strip() if context.args else 'EMOJIREAN'
    lang = generate_token(name=name.upper(), mode='both')
    global_token = lang
    _save_global_token_to_redis(lang)
    user_tokens.clear()

    deco_names = ['WING', 'BOX', 'MATH', 'RUNE', 'BRAILLE']
    deco = deco_names[lang.get('decoStyle', 0) % 5]

    await update.message.reply_text(
        f"// ✓ новый глобальный токен сгенерирован\n\n"
        f"язык: {lang.get('name', '?')}\n"
        f"деко: {deco}\n\n"
        f"// токен (для веб-приложения):\n"
        f"`{lang.get('_b64', '')}`",
        parse_mode="Markdown",
    )


# ── Main ──

def main():
    _load_admin_ids()

    # Load global token from Redis, or generate a new one
    global global_token
    global_token = _load_global_token_from_redis()
    if global_token:
        logger.info(f"Global token loaded from Redis: {global_token.get('name')}")
    else:
        global_token = generate_token(name='EMOJIREAN', mode='both')
        _save_global_token_to_redis(global_token)
        logger.info(f"Global token generated and saved: {global_token.get('name')}")
    for admin_id in ADMIN_IDS:
        activated_users.add(admin_id)

    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        logger.error("BOT_TOKEN не задан")
        return

    app = Application.builder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("token", load_token))
    app.add_handler(CommandHandler("encode", encode_cmd))
    app.add_handler(CommandHandler("decode", decode_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("settoken", settoken_cmd))
    app.add_handler(CommandHandler("newtoken", newtoken_cmd))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^admin_"))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text,
    ))

    logger.info("Бот запускается...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
