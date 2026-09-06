# doudtrading — provenance du corpus

**Chaîne** : `Doud Trading` — <https://www.youtube.com/@TheQueenDoud> (8 010 abonnés).
**Ce qui est ici** : les **lives publics et gratuits**, pas le produit payant.

| | |
|---|---|
| Streams listés sur la chaîne | 40 |
| Transcriptions obtenues | **35** (5 échecs : piste absente ou stream sans sous-titres) |
| Durée cumulée | **54 heures** |
| Segments horodatés | **68 984** |
| Langue | `fr`, sous-titres **générés automatiquement** |
| Date de collecte | 2026-09-06 |

## Ce que sont ces lives

Du scalping XAUUSD en direct, sur événement identifié — la série la plus fournie
est « scalping GOLD pendant les inscriptions hebdomadaires au chômage » (jeudi,
publication à 14h30 CET), plus des lives NFP, FOMC, discours de Powell, et des
sessions asiatiques de nuit. Durées de 43 à 191 minutes.

Elle y annonce ses points d'entrée, ses stops, ses TP, ses clôtures partielles et
ses ratios à voix haute, en temps réel, à sa communauté. C'est la raison d'être de
ce corpus : le podcast (`docs/sources/moneytalk/`) la fait **raconter** sa méthode,
ces lives la montrent l'**exécuter** — et sur quatre points les deux divergent
(cf. `SYNTHESE_METHODE.md` § 0).

## Obtention

`yt-dlp -J --flat-playlist` sur l'onglet `/streams` pour l'inventaire (l'accès web
direct bute sur le mur de consentement YouTube), puis `youtube_transcript_api`
piste `fr` par vidéo. Un segment par ligne, horodatage `[mmm:ss]` en tête, aucune
retouche.

**Limite de la source, à garder en tête pour toute citation** : la reconnaissance
vocale déforme systématiquement les nombres et les termes techniques — « SL » →
« essel » / « celle », « lot » → « l'eau », « mèche de rejet » → « mèche de
Roger », prix tronqués (« les 68 » pour 4368). `SYNTHESE_METHODE.md` ne s'appuie
donc que sur des énoncés de **règle**, qui restent lisibles malgré le bruit, et
jamais sur une extraction chiffrée automatique.

## Fichiers

- `lives/<video_id>.txt` — 35 transcriptions brutes, en-tête titre + métadonnées.
- `INDEX_lives.md` — inventaire trié par durée.
- `EXTRAIT_regles.txt` — 104 passages de 90 s sélectionnés pour leur densité en
  vocabulaire de règle (entrée, SL, TP, break-even, taille, niveaux) : c'est le
  sous-corpus effectivement lu pour produire la synthèse.
- `SYNTHESE_METHODE.md` — la méthode reconstituée, et les quatre corrections
  qu'elle impose au dossier `strategies/S018_gold_doud_v2/`.
