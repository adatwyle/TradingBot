"""
Extraction d'images d'une vidéo source, aux horodatages qui portent le contenu.

    python tools/video_frames.py --url <URL> --out strategies/sXX/frames \
        --at 9:50 11:48 16:50 ...

Pourquoi un outil plutôt qu'une capture à la main : les horodatages retenus sont
tracés dans le dépôt à côté des images. Une image de graphique sans sa position
dans la source n'est pas vérifiable — on ne peut pas y revenir pour contrôler ce
qui a été lu dedans.

ffmpeg vient de `imageio-ffmpeg` (binaire embarqué), pas du PATH système.
"""
import argparse
import os
import subprocess
import sys

import imageio_ffmpeg
import yt_dlp

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def to_seconds(ts: str) -> int:
    parts = [int(x) for x in ts.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def fetch(url: str, cache_dir: str) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    opts = {
        # 720p suffit très largement pour lire un graphique et divise le
        # téléchargement par ~4 par rapport au 1080p.
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "outtmpl": os.path.join(cache_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": FFMPEG,
        # Le client `web` renvoie des URL de flux qui répondent 403 sur les
        # requêtes hors navigateur. Les clients applicatifs n'ont pas cette
        # protection ; on les essaie dans l'ordre.
        "extractor_args": {"youtube": {"player_client": ["tv", "ios", "android", "web"]}},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


def grab(video: str, seconds: int, dest: str) -> bool:
    cmd = [FFMPEG, "-y", "-ss", str(seconds), "-i", video,
           "-frames:v", "1", "-q:v", "2", dest]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(f"  ECHEC {dest} : {r.stderr.decode(errors='replace')[-200:]}")
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--at", nargs="+", required=True,
                    help="horodatages mm:ss ou h:mm:ss")
    ap.add_argument("--cache", default=os.path.join(
        os.environ.get("TEMP", "/tmp"), "tbot_video"))
    args = ap.parse_args()

    print(f"telechargement {args.url} ...")
    video = fetch(args.url, args.cache)
    if not os.path.exists(video):
        base = os.path.splitext(video)[0]
        for ext in (".mp4", ".webm", ".mkv"):
            if os.path.exists(base + ext):
                video = base + ext
                break
    print(f"  -> {video} ({os.path.getsize(video)/1e6:.0f} Mo)")

    os.makedirs(args.out, exist_ok=True)
    ok = 0
    for ts in args.at:
        sec = to_seconds(ts)
        dest = os.path.join(args.out, f"t{ts.replace(':', 'm')}s.jpg")
        if grab(video, sec, dest):
            ok += 1
            print(f"  {ts:>8}  ->  {os.path.basename(dest)}")
    print(f"{ok}/{len(args.at)} images dans {args.out}")


if __name__ == "__main__":
    sys.exit(main())
