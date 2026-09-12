# input-adrian — S020 MACD cross + filtre zéro, SL/TP en % (René Balke)

*Maintenu par cc-support. Réécrit en place, pas d'historique (git porte la traçabilité).*

## Identité
- **Numéro** : S020 · magic `130020`
- **Source** : YouTube — René Balke (BM Trading, @ReneBalke), « Use AI to Automate ANY
  MT5 Indicator with one Prompt », 2026-08-23, https://www.youtube.com/watch?v=-9HUV9I_s-c
- **Auteur déjà connu du dépôt** : S009 (Session Range Breakout) ; corpus
  `docs/sources/renebalke/` (15 vidéos dépouillées en août, channel complet en cours de
  récupération — 773 éléments).

## La demande d'Adrian (2026-09-12)
> « passe au crible fin et reproduit cette stratégie MACD »

Et, le même jour, la doctrine qui gouverne toutes les stratégies désormais :
> « les règles générales ne sont plus valables — chaque stratégie porte ses propres
> règles — bien entendu elles auront des règles communes pour éviter les pertes
> consécutives — laisser les chances à chaque stratégie pour qu'elle puisse pousser à
> l'extrême son aventure de mise en place et son auto-amélioration pour tenter de rendre
> rentable l'idée de la stratégie. »

Et la correction de méthode qui va avec : **aucun avis avant d'avoir essayé** — on
construit, on mesure, puis on rend compte de ce que disent les chiffres.

## La règle, telle que dictée dans la vidéo
Croisement de la ligne MACD(12,26) et de sa ligne de signal (9) : hausse → achat,
baisse → vente. Filtre optionnel : achat seulement si la MACD est sous zéro au
croisement, vente seulement si elle est au-dessus. Stop et cible en **pourcentage du
prix d'entrée** (démo 2 % / 2 %). Une position par symbole. Unité de temps libre.
L'auteur : *« this is not like a money printing machine »* [19:30].

## État (2026-09-12)
- Reproduite telle quelle, 11 tests verts, R1/R5 passés sur 7 instruments.
- **Mesurée** (18 cellules, walk-forward ancré 4 fenêtres, témoin aléatoire, spread
  catalogue et mesuré), critères écrits avant : `research/FALSIFICATION.md`.
- **Verdict** (`research/VERDICT.md`) : **réussite sur EURUSD H1** au sens des critères
  — cellule stop 1 % / cible 2 % / filtre zéro : +0,155 R/trade sur 129 trades,
  percentile témoin 98,0, cinq années positives sur six, positive sur USDJPY. Échec sur
  les six autres instruments (aucune cellule STRICT). Indices mesurés en **D1
  seulement** (MT5 hors ligne) : conclusion « indices » ouverte.

## Ce qui attend Adrian
| Sujet | Décision |
|---|---|
| **Forward scellé EURUSD H1** sur la cellule retenue, protocole écrit avant le premier signal (modèle `studies/gold_forward/`) | GO / pas GO — R10 |
| Intraday indices (NASDAQ/SP500/DAX en H1 et M15) — la démo de l'auteur était en intraday | relancer la fabrique (MT5 en ligne) |
| Auto-amélioration (la « suite de l'aventure ») : pistes non explorées, à instruire une par une avec falsification écrite d'avance — filtre de tendance, stop/cible en ATR plutôt qu'en %, horaires de session, sens unique par instrument | ordre de priorité |

## Ce que S020 ne fait pas, et pourquoi
- Pas de réglage après lecture des résultats : la grille de 18 cellules est celle du
  manifeste, figée avant la mesure.
- Pas de promotion : aucun statut ne change sans décision d'Adrian.
- Pas de prétention sur les indices intraday tant qu'ils ne sont pas mesurés.
