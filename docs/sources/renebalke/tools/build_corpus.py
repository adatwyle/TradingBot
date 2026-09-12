#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Construit le corpus Rene Balke (transcripts YouTube + pages du site BM Trading)
dans docs/sources/renebalke/, a partir des sources brutes du scratchpad.

Idempotent : chaque fichier n'est reecrit que si son contenu a change, pour que les
relances soient bon marche et que les diffs git restent propres.

Sources attendues dans <scratch>/ :
    channel_listing.json   listing yt-dlp a plat de toute la chaine (videos/streams/shorts)
    top50.json              les 50 videos les plus vues, selectionnees pour Whisper
    corpus/<id>.json        transcripts {"meta", "lang", "source", "segments"}
    site/*.txt|*.html       page expert-advisors + 6 pages EA (texte deja extrait si .txt)
    site/blog/*.txt         articles de blog

Usage:
    python docs/sources/renebalke/tools/build_corpus.py [--scratch <dossier>]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser

DEFAULT_SCRATCH = (
    r"C:/Users/adria/AppData/Local/Temp/claude/"
    r"C--projects-tradingBot-support/1bbd778f-9ee3-45f5-8b98-5c934937336e/"
    r"scratchpad/balke"
)

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)  # docs/sources/renebalke
CORPUS_DIR = os.path.join(ROOT, "corpus")
SITE_DIR = os.path.join(ROOT, "site")
BLOG_DIR = os.path.join(SITE_DIR, "blog")
INDEX_PATH = os.path.join(ROOT, "CORPUS_INDEX.md")

AUGUST_URL_RE = re.compile(r"https://www\.youtube\.com/watch\?v=([\w-]+)")
AUGUST_FILE_RE = re.compile(r"^\d{2}_.*\.txt$")

TYPE_LABELS = {"videos": "video", "streams": "stream", "shorts": "short"}

# Pages du site deja scrapees en .html mais qui ne font PAS partie du corpus
# demande (blog et cours ont leur propre traitement / sont hors scope).
SITE_HTML_EXCLUDE = {"blog.html", "courses.html"}


# ---------------------------------------------------------------------------
# Fallback HTML -> texte (stdlib uniquement), utilise seulement si une page
# EA/expert-advisors scrapee n'a pas de .txt compagnon.
# ---------------------------------------------------------------------------
class _TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self.chunks.append(text)

    def get_text(self) -> str:
        return "\n".join(self.chunks)


def html_to_text(raw_html: str) -> str:
    parser = _TextExtractor()
    parser.feed(raw_html)
    return parser.get_text()


# ---------------------------------------------------------------------------
# Formatage
# ---------------------------------------------------------------------------
def format_mmss(seconds) -> str:
    seconds = int(round(seconds or 0))
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def format_duration(seconds) -> str:
    """mm:ss (minutes non plafonnees, ex. 89:19 ou 158:10) -- conforme a la
    consigne d'origine ("duration mm:ss"), pas de bascule vers h:mm:ss."""
    if not seconds:
        return "inconnue"
    return format_mmss(seconds)


def format_views(n) -> str:
    if n is None:
        return "inconnues"
    return f"{n:,}".replace(",", "\u202f")


def format_upload_date(raw) -> str:
    if not raw:
        return "-"
    try:
        return datetime.strptime(str(raw), "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return str(raw)


def normalize_source(raw_source) -> str:
    if not raw_source:
        return "api"
    if "whisper" in raw_source:
        return "whisper"
    return raw_source


def escape_md_cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


# ---------------------------------------------------------------------------
# Ecriture idempotente
# ---------------------------------------------------------------------------
def write_if_changed(path: str, content: str) -> bool:
    """Ecrit `content` dans `path` seulement si different du contenu actuel.
    Retourne True si (re)ecrit, False si deja a jour."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            if f.read() == content:
                return False
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return True


# ---------------------------------------------------------------------------
# Transcripts -> markdown
# ---------------------------------------------------------------------------
def build_paragraphs(segments):
    """Regroupe les segments en paragraphes d'environ 60s ou 600 caracteres
    (le premier des deux seuils atteints declenche un nouveau paragraphe)."""
    paragraphs = []
    current_texts: list[str] = []
    current_start = None
    chars = 0
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = seg.get("start", 0.0)
        if current_start is None:
            current_start = start
        current_texts.append(text)
        chars += len(text) + 1
        elapsed = start - current_start
        if elapsed >= 60 or chars >= 600:
            paragraphs.append((current_start, " ".join(current_texts)))
            current_texts = []
            current_start = None
            chars = 0
    if current_texts:
        paragraphs.append((current_start, " ".join(current_texts)))
    return paragraphs


def render_transcript_md(meta: dict, lang, source, segments) -> str:
    vid = meta["id"]
    title = meta.get("title") or vid
    url = f"https://www.youtube.com/watch?v={vid}"
    tab = meta.get("tab") or "videos"
    live_status = meta.get("live_status")
    categorie = TYPE_LABELS.get(tab, tab)
    if live_status:
        categorie += f" ({live_status})"

    lines = [
        f"# {title}",
        "",
        f"- URL : {url}",
        f"- Date de publication : {format_upload_date(meta.get('upload_date'))}",
        f"- Vues : {format_views(meta.get('view_count'))}",
        f"- Duree : {format_duration(meta.get('duration'))}",
        f"- Categorie : {categorie}",
        f"- Transcription : {normalize_source(source)} (langue : {lang or 'inconnue'})",
        "",
        "---",
        "",
    ]
    for start, text in build_paragraphs(segments):
        lines.append(f"[{format_mmss(start)}] {text}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def build_corpus_markdown(scratch: str):
    written = unchanged = 0
    transcribed: dict[str, str] = {}  # id -> source label (api/whisper/...)
    corpus_glob = os.path.join(scratch, "corpus", "*.json")
    for path in sorted(glob.glob(corpus_glob)):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        meta = data.get("meta", {})
        vid = meta.get("id") or os.path.splitext(os.path.basename(path))[0]
        meta.setdefault("id", vid)
        content = render_transcript_md(
            meta, data.get("lang"), data.get("source"), data.get("segments", [])
        )
        out_path = os.path.join(CORPUS_DIR, f"{vid}.md")
        if write_if_changed(out_path, content):
            written += 1
        else:
            unchanged += 1
        transcribed[vid] = normalize_source(data.get("source"))
    return written, unchanged, transcribed


# ---------------------------------------------------------------------------
# Pages du site (blog + EA/expert-advisors)
# ---------------------------------------------------------------------------
def copy_site_texts(scratch: str):
    written = unchanged = 0

    # Articles de blog : copie directe (deja du texte extrait).
    for path in sorted(glob.glob(os.path.join(scratch, "site", "blog", "*.txt"))):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        out = os.path.join(BLOG_DIR, os.path.basename(path))
        if write_if_changed(out, content):
            written += 1
        else:
            unchanged += 1

    # Page expert-advisors + 6 pages EA (fichiers directement sous site/, hors blog/).
    site_txt_glob = os.path.join(scratch, "site", "*.txt")
    txt_slugs = set()
    for path in sorted(glob.glob(site_txt_glob)):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        out = os.path.join(SITE_DIR, os.path.basename(path))
        if write_if_changed(out, content):
            written += 1
        else:
            unchanged += 1
        txt_slugs.add(os.path.splitext(os.path.basename(path))[0])

    # Fallback : pages .html sans .txt compagnon (hors blog.html/courses.html qui
    # sont hors scope) -> extraction texte visible avec le stdlib html.parser.
    site_html_glob = os.path.join(scratch, "site", "*.html")
    for path in sorted(glob.glob(site_html_glob)):
        base = os.path.basename(path)
        if base in SITE_HTML_EXCLUDE:
            continue
        slug = os.path.splitext(base)[0]
        if slug in txt_slugs:
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = html_to_text(f.read())
        out = os.path.join(SITE_DIR, f"{slug}.txt")
        if write_if_changed(out, content):
            written += 1
        else:
            unchanged += 1

    return written, unchanged


# ---------------------------------------------------------------------------
# Mapping des 15 transcripts d'aout deja presents dans le repo
# ---------------------------------------------------------------------------
def load_august_map():
    """id YouTube -> nom de fichier docs/sources/renebalke/NN_*.txt, en lisant
    l'URL declaree dans l'en-tete de chaque fichier."""
    august = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "*.txt"))):
        base = os.path.basename(path)
        if not AUGUST_FILE_RE.match(base):
            continue
        with open(path, "r", encoding="utf-8") as f:
            head = f.read(2000)
        m = AUGUST_URL_RE.search(head)
        if m:
            august[m.group(1)] = base
    return august


# ---------------------------------------------------------------------------
# Index complet de la chaine
# ---------------------------------------------------------------------------
def load_channel_items(scratch: str):
    with open(os.path.join(scratch, "channel_listing.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    items = {}
    for entries in data.values():
        for it in entries:
            items[it["id"]] = it
    return items


def load_top50_ids(scratch: str):
    with open(os.path.join(scratch, "top50.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    return [d["id"] for d in data]


def build_index_content(channel_items, top50_ids, transcribed, august_map) -> str:
    total = len(channel_items)
    source_counts = Counter(transcribed.values())
    n_api = source_counts.get("api", 0)
    n_whisper = sum(v for k, v in source_counts.items() if k != "api")
    # Un id peut en theorie figurer a la fois dans le corpus scratch et dans le
    # mapping aout : la colonne "transcrit" du tableau donne priorite au corpus
    # (branche transcribed avant august_map plus bas), donc on applique la meme
    # priorite ici pour que n_api + n_whisper + n_aout == len(union des ids).
    aout_only_ids = set(august_map) - set(transcribed)
    n_aout = len(aout_only_ids)
    n_transcribed = len(transcribed) + n_aout

    total_duration = sum(it.get("duration") or 0 for it in channel_items.values())
    n_unknown_duration = sum(1 for it in channel_items.values() if not it.get("duration"))
    covered_duration = 0
    for vid, it in channel_items.items():
        if vid in transcribed or vid in august_map:
            covered_duration += it.get("duration") or 0

    lines = [
        "# Corpus Rene Balke -- index complet de la chaine",
        "",
        f"- Items au catalogue (videos + streams + shorts) : {total}",
        f"- Transcrits : {n_transcribed} ({n_api} api, {n_whisper} whisper, {n_aout} aout)",
        f"- Duree couverte / duree totale connue : "
        f"{covered_duration / 3600:.1f} h / {total_duration / 3600:.1f} h "
        f"({n_unknown_duration} items sans duree connue)",
        "",
        "| id | titre | type | duree | vues | date | transcrit |",
        "|---|---|---|---|---|---|---|",
    ]

    def sort_key(item):
        v = item.get("view_count")
        return v if v is not None else -1

    for vid, it in sorted(channel_items.items(), key=lambda kv: sort_key(kv[1]), reverse=True):
        title = escape_md_cell(it.get("title") or "")
        title_trunc = title if len(title) <= 70 else title[:67] + "..."
        typ = TYPE_LABELS.get(it.get("tab"), it.get("tab") or "?")
        dur = format_duration(it.get("duration"))
        views = format_views(it.get("view_count"))
        date = format_upload_date(it.get("upload_date"))

        if vid in transcribed:
            label = transcribed[vid]
            transcrit = f"[{label}](corpus/{vid}.md)"
        elif vid in august_map:
            transcrit = f"[aout]({august_map[vid]})"
        else:
            transcrit = "\u2014"

        lines.append(f"| {vid} | {title_trunc} | {typ} | {dur} | {views} | {date} | {transcrit} |")

    lines += ["", "## Backlog top-50 non encore transcrits", ""]
    remaining = [vid for vid in top50_ids if vid not in transcribed and vid not in august_map]
    if remaining:
        for vid in remaining:
            title = escape_md_cell(channel_items.get(vid, {}).get("title") or "")
            lines.append(f"- `{vid}` -- {title}")
    else:
        lines.append("(aucun -- backlog top-50 epuise)")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scratch",
        default=DEFAULT_SCRATCH,
        help="Dossier scratchpad contenant channel_listing.json, top50.json, corpus/, site/",
    )
    args = parser.parse_args()
    scratch = args.scratch

    if not os.path.isdir(scratch):
        print(f"ERREUR: dossier scratch introuvable: {scratch}", file=sys.stderr)
        return 1

    os.makedirs(CORPUS_DIR, exist_ok=True)
    os.makedirs(BLOG_DIR, exist_ok=True)

    md_written, md_unchanged, transcribed = build_corpus_markdown(scratch)
    site_written, site_unchanged = copy_site_texts(scratch)
    august_map = load_august_map()

    channel_items = load_channel_items(scratch)
    top50_ids = load_top50_ids(scratch)
    index_content = build_index_content(channel_items, top50_ids, transcribed, august_map)
    index_written = write_if_changed(INDEX_PATH, index_content)

    # Union des ids transcrits (corpus scratch + aout) : un id present des deux
    # cotes ne doit compter qu'une fois.
    n_transcribed_total = len(set(transcribed) | set(august_map))
    total_items = len(channel_items)
    print(
        f"corpus: {md_written} md ecrits, {md_unchanged} inchanges | "
        f"site: {site_written} fichiers ecrits, {site_unchanged} inchanges | "
        f"index: {'ecrit' if index_written else 'inchange'} | "
        f"transcrits: {n_transcribed_total}/{total_items} "
        f"({len(transcribed)} nouveaux + {len(august_map)} aout)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
