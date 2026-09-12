# Corpus Rene Balke

Materiau source pour l'etude de la chaine YouTube et du site de Rene Balke (BM Trading) :
transcripts video, pages EA du site, articles de blog. Utilise en entree des etudes de strategie
(range breakout, turnaround tuesday, etc.) — cf. `SYNTHESE.md` (15 videos, aout), `SYNTHESE_tranche1_2026-09-12.md`,
`SYNTHESE_tranche2_2026-09-12.md`, `EA_inputs_et_reglages-live_2026-09-12.md` (→ S022/S023/S024),
`TRADEBUDDY_analyse-ecrans_2026-09-12.md` (→ module `/analytics`), `GRID_martingale_extraction_2026-09-12.md` (→ S021).

## Contenu

- `01_..._15_*.txt` — 15 transcripts recuperes manuellement en aout 2026 (sous-titres automatiques
  YouTube, dedupliques). **Ne pas modifier** — historiques, mappees par id video dans `CORPUS_INDEX.md`
  (colonne `transcrit` = `aout`). Le compte « 84 transcrits » de l'index les inclut (22 api + 47 whisper + 15 aout).
- `corpus/<video_id>.md` — un fichier par transcript genere par `tools/build_corpus.py` : en-tete
  (titre, URL, date, vues, duree, categorie, source de transcription) puis le texte en paragraphes
  d'environ 60 s / 600 caracteres, chacun prefixe d'un marqueur `[mm:ss]`. Les durees (en-tete et
  colonne `duree` de `CORPUS_INDEX.md`) sont toujours au format `mm:ss`, minutes non plafonnees
  (ex. `89:19`, `158:10`) — pas de bascule vers `h:mm:ss`, conforme a la consigne d'origine.
- `site/` — pages du site bm-trading (expert-advisors + les 6 pages EA) copiees en texte brut.
- `site/blog/` — les 11 articles du blog, copies en texte brut.
- `CORPUS_INDEX.md` — index des 773 items de la chaine (videos + streams + shorts), tries par vues
  decroissantes, avec statut de transcription (`api` / `whisper` / `aout` / `—`) et lien vers le
  fichier transcrit quand il existe. Section finale : ids du top-50 pas encore transcrits (backlog
  Whisper restant).
- `SYNTHESE.md`, `SYNTHESE_tranche1_2026-09-12.md`, `SYNTHESE_tranche2_2026-09-12.md`,
  `GRID_martingale_extraction_2026-09-12.md`, `EA_inputs_et_reglages-live_2026-09-12.md`,
  `TRADEBUDDY_analyse-ecrans_2026-09-12.md`, `ea_inputs/`, `code/` — analyses derivees, non touchees par le script de build.
- `frames/tradebuddy/` — 168 captures `.jpg` de la video qgsi-u0kOVw (36:50 → 48:06), dont 68 exploitees dans l'analyse TradeBuddy.
- `tools/build_corpus.py` — script de construction (voir ci-dessous).

## Reconstruire le corpus

```bash
python docs/sources/renebalke/tools/build_corpus.py --scratch <dossier_scratchpad>
```

`--scratch` est optionnel : par defaut il pointe vers le scratchpad de la session qui a produit
le premier lot (`channel_listing.json`, `top50.json`, `corpus/*.json`, `site/`). Pour une relance
ulterieure (nouveaux transcripts Whisper, nouveau scrape du site), relancer le script avec un
scratchpad a jour contenant la meme arborescence.

Le script est **idempotent** : un fichier `corpus/<id>.md`, `site/...` ou `CORPUS_INDEX.md` n'est
reecrit que si son contenu a change, donc les relances sont bon marche et les diffs git restent
propres — `CORPUS_INDEX.md` ne porte volontairement aucun horodatage de build (l'historique git
porte deja la date), donc deux runs sans nouvelle source produisent un contenu strictement identique.
Le mapping des 15 fichiers `NN_*.txt` d'aout est fait automatiquement en lisant l'URL YouTube
declaree dans leur en-tete — aucune liste d'ids codee en dur.

## Provenance des sources scratchpad

Recuperees via `yt-dlp` (listing plat de la chaine + audio) et un pipeline Whisper local
(`whisper-small`, quantification `int8`) pour les videos sans sous-titres YouTube exploitables,
plus un scrape simple (urllib/html.parser) du site bm-trading (pages EA + blog). Le scratchpad
source n'est pas versionne (dossier temporaire de session) — seul le resultat du build l'est.

## Points d'attention

- **Rate limit YouTube** : l'endpoint de transcription (sous-titres automatiques) bloque apres
  ~25 recuperations rapides (`IpBlocked` pendant plusieurs heures). Respecter un rythme ≥ 25 s entre
  fetches et un backoff de plusieurs heures en cas de blocage (le flux audio, lui, reste accessible).
  Cf. memoire `youtube-transcript-rate-limit`.
- **Qualite Whisper** : les transcripts marques `whisper` dans l'en-tete (`Transcription : whisper`)
  utilisent le modele `small` en quantification `int8` — les noms propres et termes techniques
  (MQL5, noms d'indicateurs, tickers) peuvent etre mal transcrits. Les transcripts `api` utilisent
  les sous-titres automatiques YouTube natifs, generalement plus fiables mais pas infaillibles non
  plus.
- Les dates de publication (`upload_date`) ne sont pas fournies par le listing plat `yt-dlp` utilise
  ici (toujours `null` en amont) — elles apparaissent donc en `-` dans les fichiers generes et dans
  `CORPUS_INDEX.md`, sauf pour les 15 fichiers d'aout dont l'en-tete porte une date recuperee
  autrement.
