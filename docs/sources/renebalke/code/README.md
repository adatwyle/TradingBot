# Code René Balke — état de la récupération

**Date** : 2026-08-17. **Vérifié via** https://bmtrading.de/en/ et /en/expert-advisors/.

## Verdict : source NON récupérable, logique reconstituée

| Élément | Constat |
|---|---|
| Distribution officielle | Le site distribue **uniquement des `.ex5` compilés** (« You get ready-to-use .ex5 files. Drag-and-drop into MT5 ») |
| Licence | Gratuit mais **conditionné à un compte chez son broker partenaire** (IC Markets / IC Trading, referral BM Trading) + activation du numéro de compte MT5 dans leur base. Modèle économique : rebates broker, pas vente d'EA |
| Source `.mq5` | **Jamais publiée** pour la version complète (v1.40 : stop orders, buffer, TP/SL 3 modes, trailing, fréquences, filtres de range) |
| Ce qui EST public | Le transcript `02_range_breakout_coding.txt` est un **tutoriel où il dicte intégralement le code d'une version simple** (entrée au marché sur cassure, 1 trade/jour, SL = autre côté du range, pas de TP, clôture à heure fixe, sizing par risque monétaire fixe) |

## Fichier fourni ici

`RangeBreakout_tutorial_reconstruction.mq5` — **reconstruction** fidèle de la version
tutoriel, pas le binaire distribué. Chaque écart connu entre cette version simple et
la version distribuée v1.40 est listé en en-tête du fichier, avec les incertitudes.

**Le code distribué (.ex5) n'a pas été téléchargé** : binaire inutilisable pour
extraire des règles, et téléchargement conditionné à l'ouverture d'un compte broker.

## Conséquence pour l'analyse

Les règles EXACTES de la version distribuée sont reconstituées par recoupement de
trois sources, par ordre de fiabilité :
1. Transcript 02 (code dicté — fiabilité maximale sur la version simple)
2. Transcript 01 (revue exhaustive des inputs v1.40 — fiabilité haute sur les options)
3. Transcripts 03/05/06/15 (réglages effectivement tradés par symbole)

Les incertitudes résiduelles sont marquées ⚠️ dans `../SYNTHESE.md` § 2.1.
