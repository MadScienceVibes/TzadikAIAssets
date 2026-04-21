#!/usr/bin/env python3
"""
Phase 1: Pull all prayer section texts from Sefaria's Ashkenaz Siddur API.
Strips HTML, removes instructional text, applies Adony fix.
Saves each prayer as a plain .txt file for review before any TTS generation.

ZERO ElevenLabs credits spent. This is text preparation only.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse

# Output directory for staging text files
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
TEXT_DIR = os.path.join(OUT_DIR, 'staged_texts')
os.makedirs(TEXT_DIR, exist_ok=True)

SEFARIA_BASE = 'https://www.sefaria.org/api/texts'

# ── Prayer section → Sefaria reference mapping ──────────────────────────────
# Each entry: (section_id, display_name, [list of Sefaria leaf references to concatenate])
# Multiple refs are joined in order to form one continuous prayer scene.

PRAYER_SECTIONS = [
    # ── SHACHARIT (Morning) ──
    ('shacharit_modehAni', 'Modeh Ani', [
        'Siddur Ashkenaz, Weekday, Shacharit, Preparatory Prayers, Modeh Ani',
    ]),
    ('shacharit_netilat', 'Netilat Yadayim', [
        'Siddur Ashkenaz, Weekday, Shacharit, Preparatory Prayers, Netilat Yadayim',
    ]),
    ('shacharit_birkotHashachar', 'Birkot HaShachar', [
        'Siddur Ashkenaz, Weekday, Shacharit, Preparatory Prayers, Morning Blessings',
    ]),
    ('shacharit_birkotHatorah', 'Birkot HaTorah', [
        'Siddur Ashkenaz, Weekday, Shacharit, Preparatory Prayers, Torah Blessings',
        'Siddur Ashkenaz, Weekday, Shacharit, Preparatory Prayers, Torah Study',
    ]),
    ('shacharit_pesukeiDezimra', 'Pesukei d\'Zimra', [
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Barukh She\'amar',
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Hodu',
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Ashrei',
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Psalm 146',
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Psalm 147',
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Psalm 148',
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Psalm 149',
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Psalm 150',
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Closing Verses',
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Vayevarech David',
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Ata Hu',
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Az Yashir',
        'Siddur Ashkenaz, Weekday, Shacharit, Pesukei Dezimra, Yishtabach',
    ]),
    ('shacharit_shema', 'Shema and Blessings (Shacharit)', [
        'Siddur Ashkenaz, Weekday, Shacharit, Blessings of the Shema, Barchu',
        'Siddur Ashkenaz, Weekday, Shacharit, Blessings of the Shema, First Blessing before Shema',
        'Siddur Ashkenaz, Weekday, Shacharit, Blessings of the Shema, Second Blessing before Shema',
        'Siddur Ashkenaz, Weekday, Shacharit, Blessings of the Shema, Shema',
        'Siddur Ashkenaz, Weekday, Shacharit, Blessings of the Shema, Blessing after Shema',
    ]),
    ('shacharit_amidahWeekday', 'Amidah (Weekday Shacharit)', [
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Patriarchs',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Divine Might',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Holiness of God',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Knowledge',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Repentance',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Forgiveness',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Redemption',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Healing',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Prosperity',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Gathering the Exiles',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Justice',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Against Enemies',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, The Righteous',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Rebuilding Jerusalem',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Kingdom of David',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Response to Prayer',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Temple Service',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Thanksgiving',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Birkat Kohanim',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Peace',
        'Siddur Ashkenaz, Weekday, Shacharit, Amidah, Concluding Passage',
    ]),
    ('shacharit_tachanun', 'Tachanun (Shacharit)', [
        'Siddur Ashkenaz, Weekday, Shacharit, Post Amidah, Tachanun, Nefilat Apayim',
    ]),
    ('shacharit_torahReading', 'Torah Reading (Shacharit)', [
        'Siddur Ashkenaz, Weekday, Shacharit, Torah Reading, Removing the Torah from Ark, Vayehi Binsoa',
        'Siddur Ashkenaz, Weekday, Shacharit, Torah Reading, Removing the Torah from Ark, Lekha Hashem',
        'Siddur Ashkenaz, Weekday, Shacharit, Torah Reading, Reading from Sefer, Birkat HaTorah',
        'Siddur Ashkenaz, Weekday, Shacharit, Torah Reading, Returning Sefer to Aron, Yehalelu',
        'Siddur Ashkenaz, Weekday, Shacharit, Torah Reading, Returning Sefer to Aron, Uvenucho Yomar',
    ]),
    ('shacharit_ashrei', 'Ashrei (Post-Torah)', [
        'Siddur Ashkenaz, Weekday, Shacharit, Concluding Prayers, Ashrei',
    ]),
    ('shacharit_uvaLetzion', 'Uva L\'Tziyon', [
        'Siddur Ashkenaz, Weekday, Shacharit, Concluding Prayers, Uva Letzion',
    ]),
    ('shacharit_aleinu', 'Aleinu (Shacharit)', [
        'Siddur Ashkenaz, Weekday, Shacharit, Concluding Prayers, Alenu',
    ]),
    ('shacharit_shirShelYom', 'Shir Shel Yom', [
        'Siddur Ashkenaz, Weekday, Shacharit, Concluding Prayers, Song of the Day',
    ]),
    ('shacharit_einKeloheinu', 'Ein Keloheinu', [
        'Siddur Ashkenaz, Weekday, Shacharit, Concluding Prayers, Korbanot (Israel), Ein Kelohenu',
    ]),

    # ── MINCHA (Afternoon) ──
    ('mincha_ashrei', 'Ashrei (Mincha)', [
        'Siddur Ashkenaz, Weekday, Minchah, Ashrei',
    ]),
    ('mincha_amidah', 'Amidah (Mincha)', [
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Patriarchs',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Divine Might',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Holiness of God',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Knowledge',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Repentance',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Forgiveness',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Redemption',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Healing',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Prosperity',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Gathering the Exiles',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Justice',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Against Enemies',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, The Righteous',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Rebuilding Jerusalem',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Kingdom of David',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Response to Prayer',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Temple Service',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Thanksgiving',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Peace',
        'Siddur Ashkenaz, Weekday, Minchah, Amidah, Concluding Passage',
    ]),
    ('mincha_tachanun', 'Tachanun (Mincha)', [
        'Siddur Ashkenaz, Weekday, Minchah, Tachanun, Nefilat Apayim',
    ]),
    ('mincha_aleinu', 'Aleinu (Mincha)', [
        'Siddur Ashkenaz, Weekday, Minchah, Alenu',
    ]),

    # ── MAARIV (Evening) ──
    ('maariv_shema', 'Shema and Blessings (Maariv)', [
        'Siddur Ashkenaz, Weekday, Maariv, Barchu',
        'Siddur Ashkenaz, Weekday, Maariv, Blessings of the Shema, First Blessing before Shema',
        'Siddur Ashkenaz, Weekday, Maariv, Blessings of the Shema, Second Blessing before Shema',
        'Siddur Ashkenaz, Weekday, Maariv, Blessings of the Shema, Shema',
        'Siddur Ashkenaz, Weekday, Maariv, Blessings of the Shema, First Blessing after Shema',
        'Siddur Ashkenaz, Weekday, Maariv, Blessings of the Shema, Second Blessing after Shema',
    ]),
    ('maariv_amidah', 'Amidah (Maariv)', [
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Patriarchs',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Divine Might',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Holiness of God',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Knowledge',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Repentance',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Forgiveness',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Redemption',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Healing',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Prosperity',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Gathering the Exiles',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Justice',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Against Enemies',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, The Righteous',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Rebuilding Jerusalem',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Kingdom of David',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Response to Prayer',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Temple Service',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Thanksgiving',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Peace',
        'Siddur Ashkenaz, Weekday, Maariv, Amidah, Concluding Passage',
    ]),
    ('maariv_aleinu', 'Aleinu (Maariv)', [
        'Siddur Ashkenaz, Weekday, Maariv, Alenu',
    ]),
    ('maariv_veyitenLecha', 'V\'yiten Lecha', [
        'Siddur Ashkenaz, Weekday, Maariv, Additions for Motza\'ei Shabbat, Veyiten Lekha',
    ]),

    # ── SHABBAT ──
    ('shabbat_kabbalatShabbat', 'Kabbalat Shabbat', [
        'Siddur Ashkenaz, Shabbat, Kabbalat Shabbat',
    ]),
    ('shabbat_nishmat', 'Nishmat Kol Chai', [
        'Siddur Ashkenaz, Shabbat, Shacharit, Pesukei Dezimra, Nishmat',
    ]),

    # ── BENCHING ──
    ('benching', 'Birkat HaMazon', [
        'Siddur Ashkenaz, Berachot, Birkat HaMazon',
    ]),
]


def fetch_sefaria_text(ref: str) -> str:
    """Fetch Hebrew text from Sefaria API for a given reference."""
    encoded = urllib.parse.quote(ref.replace(' ', '_'), safe='')
    # Use the ref directly with spaces replaced by underscores, then URL-encode commas
    url = f'{SEFARIA_BASE}/{ref.replace(" ", "_")}?context=0&pad=0'
    url = url.replace(',', '%2C').replace("'", '%27')

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'TzadikTTS/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f'  ERROR fetching {ref}: {e}', file=sys.stderr)
        return ''

    he = data.get('he', [])
    if isinstance(he, str):
        return he
    if isinstance(he, list):
        return flatten_text(he)
    return ''


def flatten_text(items) -> str:
    """Recursively flatten nested lists of strings into one string."""
    parts = []
    for item in items:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, list):
            parts.append(flatten_text(item))
    return ' '.join(parts)


def clean_text(html_text: str) -> str:
    """Strip HTML tags, instructional text, and apply pronunciation fixes."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_text)

    # Remove common instructional text (Hebrew)
    instructions = [
        r'יש להפסיק מעט',
        r'בלחש',
        r'ש"ץ חוזר',
        r'הש"ץ אומר',
        r'הקהל אומר',
        r'אומרים בלחש',
        r'כשמתפלל ביחיד',
        r'בעשי"ת אומרים',
        r'בין ר"ה ליו"כ',
    ]
    for instr in instructions:
        text = re.sub(instr, '', text)

    # Adony fix: אֲדֹנָי → אָדוֹנַי (explicit vowels for correct TTS pronunciation)
    text = text.replace('אֲדֹנָי', 'אָדוֹנַי')

    # Also handle the Tetragrammaton: יְהוָה and יְהֹוָה → אָדוֹנַי (prayer context)
    text = re.sub(r'יְהוָה', 'אָדוֹנַי', text)
    text = re.sub(r'יְהֹוָה', 'אָדוֹנַי', text)

    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove standalone colons and other punctuation artifacts
    text = re.sub(r'\s*:\s*', ' ', text)

    return text


def main():
    print('=' * 60)
    print('Phase 1: Sefaria Text Pull — ZERO ElevenLabs credits')
    print('=' * 60)
    print()

    total_chars = 0
    results = []

    for section_id, display_name, refs in PRAYER_SECTIONS:
        print(f'Pulling: {display_name} ({len(refs)} refs)...')
        parts = []
        for ref in refs:
            raw = fetch_sefaria_text(ref)
            if raw:
                parts.append(raw)
            time.sleep(0.3)  # Be polite to Sefaria API

        if not parts:
            print(f'  WARNING: No text retrieved for {display_name}!')
            results.append((section_id, display_name, 0, ''))
            continue

        combined = ' '.join(parts)
        cleaned = clean_text(combined)
        char_count = len(cleaned)
        total_chars += char_count

        # Save to text file
        txt_path = os.path.join(TEXT_DIR, f'{section_id}.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(cleaned)

        results.append((section_id, display_name, char_count, txt_path))
        print(f'  ✓ {char_count:,} chars → {txt_path}')

    # Summary
    print()
    print('=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print(f'{"Section":<45} {"Chars":>8}')
    print('-' * 55)
    for section_id, display_name, chars, _ in results:
        status = '✓' if chars > 0 else '✗'
        print(f'{status} {display_name:<43} {chars:>8,}')
    print('-' * 55)
    print(f'  {"TOTAL":<43} {total_chars:>8,}')
    print()
    print(f'ElevenLabs credits remaining: 39,579')
    print(f'Credits needed for all sections: {total_chars:,}')
    print(f'Credits after generation: {39_579 - total_chars:,}')
    if total_chars > 39_579:
        print(f'⚠️  OVER BUDGET by {total_chars - 39_579:,} chars — MUST cut sections')
    else:
        print(f'✓ Within budget with {39_579 - total_chars:,} chars for retakes')
    print()
    print(f'Text files saved to: {TEXT_DIR}/')
    print('Review each .txt file before approving TTS generation.')


if __name__ == '__main__':
    main()
