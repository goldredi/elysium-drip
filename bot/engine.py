"""
Emojirean encoding engine for the bot (Python port of core JS logic).
Handles encoding and decoding text to/from emoji using a language token.
"""

import json
import base64
import math
import random
import zlib
import struct

# Emoji pool — same order as JS engine
EMOJI_POOL = [
    '🦊','🐺','🦁','🐯','🐻','🦝','🦨','🦡','🦦','🐙','🦑','🦀','🦞','🦐','🐳','🐋',
    '🐬','🦈','🐊','🐢','🦎','🐍','🦖','🦕','🦋','🐝','🦗','🦂','🦟','🐿️','🦔','🦜',
    '🦩','🦚','🦅','🦉','🕊️','🦆','🦢','🦄','🐉','🦇','🐠','🐡','🐟','🐛','🐌','🐜',
    '🐞','🐆','🦓','🦏','🦛','🐘','🦒','🦘','🦙','🐐','🦌','🐓','🦬','🦥','🦭',
    '🍄','🌺','🌸','🌼','🌻','🌹','🌷','🌿','🍀','🌱','🌲','🌳','🌴','🌵','🎋','🌾',
    '🪴','🍃','🪷','💐','🌑','🌒','🌓','🌔','🌕','🌖','🌗','🌘','🍁','🍂',
    '🍇','🍈','🍉','🍊','🍋','🍌','🍍','🥭','🍎','🍏','🍐','🍑','🍒','🍓','🫐','🥝',
    '🍅','🫒','🥥','🥑','🌽','🥕',
    '⭐','🌟','💫','✨','⚡','🌪️','☄️','🌈','🔥','💥','💢','💨','🫧','❄️','🌊','🌋',
    '🌙','🌤️','⛅','🌧️','⛈️','🌩️','🌨️','🌫️','🌬️','🌝','🌛','🌜','🌞','🌠',
    '💎','🔮','🧿','💠','🔷','🔹','🪬','🫙','🧊','🗝️','⚔️','🏹','🔱','⚜️','🛡️',
    '⚙️','🔩','🔧','🧲','🪝','🔒','🔓','📡','💾','📺','📻','🖥️','💡','🔋','💿','📀',
    '📷','📸','🔬','🔭','⚗️','🧪','🧫','🧬','🔑','🪄','🎩',
    '🎸','🎺','🎻','🥁','🎹','🎤','🎧','🎵','🎶','🎼','🎭','🎨','🎯','🎲','🃏','🎰',
    '🎳','🎱','🎮','🎆','🎇','🧨','🎈','🎉','🎊','🎀','🎁','🏆','🥇','🥈','🥉','🏅',
    '🎖️','🎪','🎠','🎡','🎢',
    '🔴','🟠','🟡','🟢','🔵','🟣','⚫','⚪','🟤','🔶','🔸','🔺','🔻',
    '♠️','♥️','♦️','♣️',
    '🚀','🛸','🛰️','🌌','🪐','🏔️','🗻','🌏','🌐','🗺️','🧭','🏝️','🏜️','🌃','🌆',
    '💀','👾','🎃','👻','⚰️','🕯️','🪦','☯️','⚠️','🌀',
    '🫀','🧠','🦷','🦴','👁️',
    '🎑','🏺','🗼','🏯','💧','⛄','👑','💍','🔔','🎐','🎏','🪩',
    '🧶','🧵','🏛️','🏰','🌂',
    '🧩','🪔','🏮','💊','🩺','🩻',
    '🟥','🟧','🟨','🟩','🟦','🟪','🟫',
    '🐾','🦶','👣','🌿','🍃','🌾','🎋',
    '🪸','🦠','🪲','🪳','🪰','🪱',
    '🫆','🫳','🫴','🫵','🤌','🤏',
    '🪬','🧿','🔯','✡️','☪️','⛎','♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓',
]

DECO_SETS = [
    list('✮☠☂☁☀☼☽☾☣❀ї☄✯♣♧◔◕♬✽♫♪°❃❉✣⁂✦*.'),
    list('░▒▓│┤╔╗╚╝─═╠╣╦╩╬▐▌▀▄▪▫'),
    list('∴∵∞≡∇⋮∑∏∂∫√∆≈∃∀∈⊕⊗⊙∯≜'),
    list('ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛜ'),
    list('⠿⠯⠷⠾⠸⠼⠻⠽⠱⠩⠙⠋⠃⠅⠇⠏⠟⠗⠛⠓⠚⠢'),
]

FRAME_EMOJIS = ['⬛','🔲','🔳','◼️','▪️','⬜','◻️','▫️']

ALL_DECO = set()
for ds in DECO_SETS:
    ALL_DECO.update(ds)

COMPRESS_MARKER = 0xC0

# Stealth
STEALTH_COVER = list('😊😂❤️🔥👍😍🥰😘💕🙏😭💪🎉✅🥺😎👏💯🤣😁😆🤩🙌💗💖🌟⭐🎶🎵💜💙💚🤗😋🤤😜🤪🥳🫶🫡👀💅🤝🏆🎊🎈💝🙈😅🤭🫣')
STEALTH_ANCHOR = '🫥'


def parse_emojis(raw: str) -> list[str]:
    """Parse string into individual emoji/grapheme clusters."""
    import regex
    return regex.findall(r'\X', raw)


def decode_token(b64: str) -> dict | None:
    """Decode a base64 token into a language object."""
    try:
        raw = base64.b64decode(b64).decode('utf-8')
        c = json.loads(raw)

        if 'letters' in c and c['letters']:
            first_val = next(iter(c['letters'].values()), None)
            if first_val and isinstance(first_val, list) and isinstance(first_val[0], str) and len(first_val[0]) > 1:
                return c

        from_idx = lambda x: EMOJI_POOL[x] if isinstance(x, int) and 0 <= x < len(EMOJI_POOL) else x

        def expand_map(m):
            return {k: [from_idx(v) for v in (vs if isinstance(vs, list) else [vs])] for k, vs in m.items()}

        mode_map = {'r': 'ru', 'e': 'en', 'b': 'both'}

        obj = {
            'id': c.get('i'),
            'name': c.get('n', 'UNKNOWN'),
            'v': 3,
            'mode': mode_map.get(c.get('m'), 'ru'),
            'type': 'reader' if c.get('t') == 'r' else 'master',
            'letters': expand_map(c.get('l', {})),
            'bigrams': expand_map(c.get('b', {})),
            'spaceEmoji': from_idx(c['s']) if c.get('s') is not None else None,
            'spaceSep': c.get('p', '·'),
            'decoStyle': c.get('d', 0),
            'nullEmojis': [from_idx(x) for x in c.get('x', [])],
            'created': c.get('c', ''),
            'ttl': c.get('ttl'),
            'crypto': 'aes256gcm' if c.get('cr') == 'a' else None,
        }

        # byteMap
        if 'bm' in c:
            obj['byteMap'] = [from_idx(x) for x in c['bm']]

        if 'rv' in c:
            obj['rev_mapping'] = {
                from_idx(int(k) if k.isdigit() else k): v
                for k, v in c['rv'].items()
            }
            obj['source_id'] = c.get('si')

        return obj
    except Exception:
        return None


RU_CHARS = list('АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
EN_CHARS = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
DIGITS = list('0123456789')
RU_BIGRAMS = [
    'НА','СТ','ЧТ','ПР','ОТ','ОН','ЕН','ЕТ','НО','НИ','ТО','НЕ','ОС','РА','ЕС','ОВ',
    'ВО','ТА','КО','РО','ДА','ЛИ','ОР','ТИ','АН','ЕР','ПО','РЕ','ЛА','КА','АТ','ОБ',
    'АЛ','ВА','ДЕ','ЕЛ','ИН','ИТ','ОЛ','ТЕ','АК','ВЕ','ВС','ГО','ЕД','ЕК','ИЛ','ИС',
    'ЛО','МО','ОД','ОК','ПА','СО','ЦИ','ЧА','ЧЕ','ШИ','ЫЙ','БО','ВИ','ДО','ДУ','ЕМ',
    'ЗА','ИВ','ИМ','ИЯ','КУ','МА','МЕ','МИ','ОГ','ОЖ','ОЗ','ОМ','ОП','ОЧ','РИ','РУ',
    'СА','СЕ','СИ','СК','СЛ','ТР','ТУ','ТЫ','УТ','ХО','ЧИ','ШЕ','ЫХ','ЬН','ЯТ','БЕ',
    'БУ','ВН','ВЫ','ГА','ГР','ДИ','ДР','ЕВ','ЕЖ','ЕЧ','ЖА','ЖД','ЖЕ','ЗВ','ЗН','ИК',
    'ИО','ЛЕ','ЛЬ','МН','МУ','НУ','ОЙ','ОЦ','ОШ',
]
SPACE_CHARS = ['·', '•', '⋅', '∙', '◦', '‣', '⁃', '⁘', '⁛', '⁜']


def generate_token(name: str = 'UNNAMED', mode: str = 'ru') -> dict:
    """Generate a new language token (master)."""
    chars = []
    if mode in ('ru', 'both'):
        chars.extend(RU_CHARS)
    if mode in ('en', 'both'):
        chars.extend(EN_CHARS)
    chars.extend(DIGITS)

    pool = list(EMOJI_POOL)
    random.shuffle(pool)
    used = set(FRAME_EMOJIS)

    # Space emoji
    space_emoji = None
    for e in pool:
        if e not in used:
            used.add(e)
            space_emoji = e
            break

    def assign(n):
        res = []
        for e in pool:
            if len(res) >= n:
                break
            if e not in used:
                used.add(e)
                res.append(e)
        return res

    # Letters
    ru_hi = set('АЕОИУТНСРЛ')
    letters = {}
    for ch in chars:
        n = 3 if ch in ru_hi else 2 if ch in RU_CHARS or ch in EN_CHARS else 1
        hs = assign(n)
        if hs:
            letters[ch] = hs

    # Bigrams
    bigrams = {}
    if mode in ('ru', 'both'):
        for bg in RU_BIGRAMS[:40]:
            hs = assign(2)
            if hs:
                bigrams[bg] = hs

    # Null emojis
    null_emojis = [e for e in pool if e not in used][:12]

    deco_style = random.randint(0, len(DECO_SETS) - 1)
    space_sep = random.choice(SPACE_CHARS)

    # Generate ID and byteMap
    token_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=24))
    byte_pool = list(EMOJI_POOL)
    random.shuffle(byte_pool)
    byte_map = byte_pool[:256]

    obj = {
        'id': token_id,
        'name': name.upper(),
        'letters': letters,
        'bigrams': bigrams,
        'spaceEmoji': space_emoji,
        'spaceSep': space_sep,
        'nullEmojis': null_emojis,
        'decoStyle': deco_style,
        'created': __import__('datetime').datetime.utcnow().isoformat(),
        'mode': mode,
        'type': 'master',
        'ttl': None,
        'v': 3,
        'crypto': 'aes256gcm',
        'byteMap': byte_map,
    }

    obj['_b64'] = encode_token(obj)
    return obj


def encode_token(obj: dict) -> str:
    """Encode a language object to base64 token string (compact format)."""
    pidx = {}
    for i, e in enumerate(EMOJI_POOL):
        pidx[e] = i

    def to_idx(emoji):
        return pidx.get(emoji, emoji)

    def compact_map(m):
        return {k: [to_idx(v) for v in vs] for k, vs in m.items()}

    mode_map = {'ru': 'r', 'en': 'e', 'both': 'b'}

    c = {
        'i': obj.get('id'),
        'n': obj.get('name', 'UNKNOWN'),
        'm': mode_map.get(obj.get('mode', 'ru'), 'r'),
        't': 'r' if obj.get('type') == 'reader' else 'm',
        'l': compact_map(obj.get('letters', {})),
        'b': compact_map(obj.get('bigrams', {})),
        's': to_idx(obj.get('spaceEmoji')) if obj.get('spaceEmoji') else None,
        'p': obj.get('spaceSep', '·'),
        'd': obj.get('decoStyle', 0),
        'x': [to_idx(e) for e in obj.get('nullEmojis', [])],
        'c': obj.get('created', ''),
        'cr': 'a' if obj.get('crypto') == 'aes256gcm' else None,
    }

    if obj.get('ttl'):
        c['ttl'] = obj['ttl']
    if obj.get('byteMap'):
        c['bm'] = [to_idx(e) for e in obj['byteMap']]
    if obj.get('rev_mapping'):
        c['rv'] = {str(to_idx(k)): v for k, v in obj['rev_mapping'].items()}
        c['si'] = obj.get('source_id')

    raw = json.dumps(c, ensure_ascii=False, separators=(',', ':'))
    return base64.b64encode(raw.encode('utf-8')).decode('ascii')


def encode_text(text: str, lang: dict) -> list[str]:
    """Encode text to emoji list using a language token."""
    if not lang or lang.get('type') == 'reader':
        return []

    letters = lang.get('letters', {})
    bigrams = lang.get('bigrams', {})
    space_emoji = lang.get('spaceEmoji')
    null_emojis = lang.get('nullEmojis', [])

    upper = text.upper()
    result = []
    i = 0

    while i < len(upper):
        ch = upper[i]
        pair = upper[i:i+2] if i + 1 < len(upper) else ''

        if ch == ' ':
            if space_emoji:
                result.append(space_emoji)
            elif null_emojis:
                result.append(null_emojis[0])
            i += 1
        elif pair in bigrams and len(pair) == 2 and upper[i+1] != ' ':
            hs = bigrams[pair]
            result.append(random.choice(hs))
            i += 2
        elif ch in letters:
            hs = letters[ch]
            result.append(random.choice(hs))
            i += 1
        else:
            i += 1

    return result


def encode_compressed(text: str, lang: dict) -> list[str] | None:
    """Encode text using deflate compression + byteMap."""
    byte_map = lang.get('byteMap')
    if not byte_map or len(byte_map) < 256:
        return None
    try:
        text_bytes = text.encode('utf-8')
        compressed = zlib.compress(text_bytes, 9)
        # Add COMPRESS_MARKER header
        data = bytes([COMPRESS_MARKER]) + compressed
        return [byte_map[b] for b in data]
    except Exception:
        return None


def decode_text(emojis: list[str], lang: dict) -> str | None:
    """Decode emoji list back to text. Tries compressed first, then letter mapping."""
    if not lang:
        return None

    null_set = set(lang.get('nullEmojis', []))
    frame_set = set(FRAME_EMOJIS)
    clean = [e for e in emojis if e not in frame_set and e not in ALL_DECO and e.strip()]

    # Stealth unwrap
    if STEALTH_ANCHOR in clean:
        idx = clean.index(STEALTH_ANCHOR)
        after = clean[idx+1:]
        extracted = after[::4]
        if extracted:
            clean = extracted

    # Try compressed decode
    byte_map = lang.get('byteMap')
    if byte_map:
        rev_byte = {}
        for i, e in enumerate(byte_map):
            rev_byte[e] = i
        byte_arr = []
        all_known = True
        for e in clean:
            if e in rev_byte:
                byte_arr.append(rev_byte[e])
            elif e not in null_set:
                all_known = False
        if byte_arr and byte_arr[0] == COMPRESS_MARKER:
            try:
                compressed_data = bytes(byte_arr[1:])
                decompressed = zlib.decompress(compressed_data)
                return decompressed.decode('utf-8')
            except Exception:
                pass

    # Letter/bigram mapping
    rev = {}
    if lang.get('type') == 'reader':
        rev.update(lang.get('rev_mapping', {}))
    else:
        for ch, hs in (lang.get('letters', {})).items():
            for e in hs:
                rev[e] = ch
        for bg, hs in (lang.get('bigrams', {})).items():
            for e in hs:
                rev[e] = bg
        se = lang.get('spaceEmoji')
        if se:
            rev[se] = ' '

    decoded = ''
    for e in clean:
        if e in rev:
            decoded += rev[e]
    return decoded if decoded else None


def build_rows(emojis: list[str], shape: str = 'grid') -> list[list[str]]:
    """Build rows from emoji list for a given shape."""
    import math
    if not emojis:
        return []

    rows = []
    e = list(emojis)

    if shape == 'grid':
        c = max(3, math.ceil(math.sqrt(len(e) * 0.8)))
        for i in range(0, len(e), c):
            rows.append(e[i:i+c])
    elif shape == 'diamond':
        mid = max(3, math.ceil(math.sqrt(len(e))))
        i, r, d = 0, 1, 1
        while i < len(e):
            rows.append(e[i:i+r])
            i += r
            if r >= mid: d = -1
            r = max(1, r + d)
    else:
        c = max(3, math.ceil(math.sqrt(len(e))))
        for i in range(0, len(e), c):
            rows.append(e[i:i+c])

    return rows


def rows_to_artistic(rows: list[list[str]], deco_style: int = 0) -> str:
    """Convert rows to artistic text with deco borders."""
    if not rows:
        return ''

    pad = FRAME_EMOJIS[deco_style % len(FRAME_EMOJIS)]
    max_w = max(len(r) for r in rows)
    ds = DECO_SETS[deco_style % len(DECO_SETS)]

    lines = []
    for ri, row in enumerate(rows):
        pad_l = (max_w - len(row)) // 2
        pad_r = max_w - len(row) - pad_l
        full = [pad] * pad_l + row + [pad] * pad_r
        inner = ''.join(
            e + ds[(ri*5 + i*3 + 7) % len(ds)] if i < len(full) - 1 else e
            for i, e in enumerate(full)
        )
        lines.append(ds[(ri*3) % len(ds)] + inner + ds[(ri*3+4) % len(ds)])

    row_w = max_w * 2 + (max_w - 1) + 2
    top = ''.join(ds[(i+3) % len(ds)] for i in range(row_w))
    bot = ''.join(ds[(row_w - i + 7) % len(ds)] for i in range(row_w))

    return top + '\n' + '\n'.join(lines) + '\n' + bot


def pad_to_grid(encoded: list[str], null_emojis: list[str], min_size: int = 49) -> list[str]:
    """Pad encoded emojis with nullEmojis to reach a uniform grid size.
    Uses nullEmojis which the decoder knows to skip, preserving decode accuracy."""
    if not null_emojis:
        return encoded
    target = max(min_size, int(math.ceil(math.sqrt(len(encoded))) ** 2))
    r = list(encoded)
    while len(r) < target:
        r.insert(random.randint(0, len(r)), random.choice(null_emojis))
    return r


def add_nulls(arr: list[str], nulls: list[str], density: float = 0.3) -> list[str]:
    """Insert random null emojis between real ones for variation."""
    if not nulls or density <= 0:
        return arr
    result = []
    for e in arr:
        result.append(e)
        if random.random() < density:
            result.append(random.choice(nulls))
    return result


def rows_to_shaped(rows: list[list[str]], deco_style: int = 0) -> str:
    """Convert rows to shaped grid with emoji padding (no deco chars)."""
    if not rows:
        return ''
    pad = FRAME_EMOJIS[deco_style % len(FRAME_EMOJIS)]
    max_w = max(len(r) for r in rows)
    lines = []
    for row in rows:
        pad_l = (max_w - len(row)) // 2
        pad_r = max_w - len(row) - pad_l
        lines.append(''.join([pad] * pad_l + row + [pad] * pad_r))
    return '\n'.join(lines)


def rows_to_flat(rows: list[list[str]]) -> str:
    """Flatten rows to single line."""
    return ''.join(e for row in rows for e in row)
