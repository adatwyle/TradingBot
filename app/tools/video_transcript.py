"""
Récupère le sous-titrage d'une vidéo YouTube et le nettoie en texte lisible.

    python tools/video_transcript.py --id qbyQ8322m-M --out strategies/sXX/src.txt

Les sous-titres automatiques arrivent en VTT avec un chevauchement massif
(chaque ligne répète la précédente pour l'effet de défilement). On déduplique,
sinon le fichier fait trois fois la taille utile et sature la lecture.
"""
import argparse
import os
import re
import subprocess
import sys

import imageio_ffmpeg
import yt_dlp

OPTS = {
    "quiet": True, "no_warnings": True, "skip_download": True,
    "writesubtitles": True, "writeautomaticsub": True,
    "subtitleslangs": ["en", "en-orig", "en-US"], "subtitlesformat": "vtt",
    # Pas de client `tv` ici : il ne propose que des flux protégés par DRM, ce
    # qui fait échouer yt-dlp avant même d'arriver aux sous-titres. Les clients
    # applicatifs suffisent, on ne télécharge pas la vidéo.
    "extractor_args": {"youtube": {"player_client": ["ios", "web", "android"]}},
}

TAG = re.compile(r"<[^>]+>")
TIME = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s+-->")


def clean(vtt_path: str) -> str:
    out, seen = [], set()
    stamp = None
    for line in open(vtt_path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if TIME.match(line):
            stamp = line[:8]
            continue
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        text = TAG.sub("", line).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append((stamp, text))

    # Regroupe par tranche de 30 s pour garder un repère temporel sans hacher.
    lines, buf, cur = [], [], None
    for stamp, text in out:
        key = stamp[:6] + ("0" if stamp and int(stamp[6:8]) < 30 else "3") if stamp else "?"
        if key != cur and buf:
            lines.append(f"[{cur}] " + " ".join(buf))
            buf = []
        cur = key
        buf.append(text)
    if buf:
        lines.append(f"[{cur}] " + " ".join(buf))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="identifiant vidéo YouTube")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default=os.path.join(
        os.environ.get("TEMP", "/tmp"), "tbot_subs"))
    args = ap.parse_args()

    os.makedirs(args.cache, exist_ok=True)
    opts = dict(OPTS, outtmpl=os.path.join(args.cache, "%(id)s.%(ext)s"))
    url = f"https://www.youtube.com/watch?v={args.id}"
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(url, download=True)

    cands = [os.path.join(args.cache, f) for f in os.listdir(args.cache)
             if f.startswith(args.id) and f.endswith(".vtt")]
    if not cands:
        print(f"aucun sous-titre pour {args.id}")
        return 1

    body = clean(sorted(cands)[0])
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(f"# {info.get('title')}\n")
        f.write(f"# https://www.youtube.com/watch?v={args.id}\n")
        f.write(f"# {info.get('duration')} s — {info.get('view_count')} vues — "
                f"{info.get('upload_date')}\n")
        f.write("# Sous-titres automatiques YouTube, dédupliqués. "
                "Erreurs de transcription possibles sur les termes techniques.\n\n")
        f.write(body + "\n")
    print(f"{args.out}  ({len(body)} caracteres)  {info.get('title')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
