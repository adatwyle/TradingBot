# input-adrian — S024 « Go Long » (René Balke)

*Maintenu par cc-support. Réécrit en place, pas d'historique (git porte la traçabilité).*

## Identité
- **Numéro** : S024 · magic `130024`
- **Source** : YouTube — René Balke (BM Trading, @ReneBalke), « In 48 Minutes I show
  you how I made €100,000 Trading Forex »,
  https://www.youtube.com/watch?v=qgsi-u0kOVw — règle dictée à [05:24]-[09:00],
  réglages live montrés à l'écran à [24:30]-[27:26].
- **EA gratuit + guide d'entrées** : https://bmtrading.de/en/expert-advisors/ ·
  `docs/sources/renebalke/ea_inputs/Go Long EA Inputs.pdf`
- **Synthèse du corpus** : `docs/sources/renebalke/EA_inputs_et_reglages-live_2026-09-12.md` §2.1
- **Auteur déjà connu du dépôt** : S009 (Range Breakout), S020 (MACD cross),
  S022 (ATR Candle Breakout).

## La demande d'Adrian (2026-09-12)
> « reproduis Go Long de Balke tel quel, mesure contre acheter-et-tenir, rapporte ;
> GO 2026-09-12 »

Et la doctrine qui gouverne toutes les stratégies depuis ce jour : chaque stratégie
porte ses propres règles, aucune règle générale ne la veto, les règles communes ne
servent qu'à éviter les pertes consécutives au niveau du portefeuille. Et la méthode :
**aucun avis avant d'avoir essayé** — on construit, on mesure, puis on rend compte de
ce que disent les chiffres.

## La règle, telle qu'elle est dictée
Tous les jours, un **achat** de l'indice à heure fixe ; clôture à heure fixe le même
soir. Aucun filtre, aucune analyse, **ni stop ni take profit**, pas de trailing, option
« wait for new day high » désactivée. US30 et US Tech : 01:05 → 23:50 (heure serveur).
DE40 : 09:05 → 22:55, parce que le spread nocturne du DAX est « four times or even
more » plus cher chez son courtier. Motif de la réouverture quotidienne : le swap long
coûterait ≈ 6 %/an sur le DE40, et être à plat la nuit et le week-end évite les gaps.

Son « risque 50 000 € » est un **notionnel**, pas un stop : la perte si l'indice
tombait à zéro. C'est de la couche risque (R2), pas de la stratégie.

## État (2026-09-12)
- Reproduite telle quelle, **30 tests verts**, R1/R5 passés sur les trois indices.
- **Mesurée** sur 5,07 ans de H1 (2021-08-16 → 2026-09-11) : 6 cellules, walk-forward
  ancré, spread catalogue et mesuré, étalons acheter-et-tenir + décomposition
  intraday/overnight, balayage horaire exhaustif. Critères écrits avant :
  `research/FALSIFICATION.md`.
- **Verdict** (`research/VERDICT.md`) : **« réussite en tant que bêta indiciel, pas
  d'edge de timing »** — la formulation était imposée d'avance pour ce cas.
  Positive sur les trois indices au spread mesuré (**+47,9 % DAX, +71,4 % NASDAQ,
  +43,5 % US30**, soit +0,034 à +0,056 % par trade sur ~1 270 trades chacun), fidèle
  à son live sur les quatre repères (≈ 250 trades/an, +0,02-0,06 %/trade, 2022
  négative partout, creux des droits de douane visible : NASDAQ −22,3 pts du 17.02 au
  04.04.2025). Mais son heure d'entrée ne bat pas les autres heures de séance sur les
  indices américains (rang 16/23 et 9/23).
- **La trouvaille** : ce qui paie n'est pas l'heure, c'est d'**être à plat hors
  séance**. Sur la population comparable (journées réellement tradées), la jambe
  overnight est **négative sur les trois indices** (−11,4 / −4,8 / −11,2 % composés)
  et la jambe intraday seule bat l'acheter-et-tenir partout (+81,6 vs +60,9 ;
  +104,0 vs +94,2 ; +66,9 vs +48,3).
- **Corrigé après revue qualité** (ADDENDUM A1-A6 de `research/FALSIFICATION.md`) :
  le calcul du % ne payait que la moitié du spread (surévaluation d'un tiers sur
  DAX), et le « contre-exemple NASDAQ » du premier rapport était un artefact
  d'étalon (46 chevauchements + 38 journées sautées non comparables). Les critères
  pré-inscrits n'ont pas été touchés.

## Ce qui attend Adrian

| Sujet | Décision |
|---|---|
| **Mesurer le swap réel Swissquote** sur DAX / NASDAQ / US30. Il chiffre le sien à ≈ 6 %/an sur DE40 ; sur 5 ans cela vaut ≈ 30 points de notionnel. C'est **le** chiffre qui décide si cette stratégie bat un acheter-et-tenir en CFD, et il nous manque. | lancer la mesure (données, pas réglage) |
| **Forward scellé** sur la cellule de fidélité (garde 5 %, offset 0), protocole écrit avant le premier signal (modèle `studies/gold_forward/`) — en sachant que ce serait un forward de **bêta**, pas de signal | GO / pas GO — R10 |
| **Turnaround Tuesday** (`S023`, déjà en cours) : même horaire, même absence de stop. Trois constats de S024 lui sont opposables — profil de séance, R non comparable entre gardes, témoin commun aveugle sur une stratégie mono-horaire | rien à décider, transmission |
| **NASDAQ** : la mesure dit que sortir le soir y coûte du bêta, alors que c'est son plus gros contributeur déclaré. Régime 2021-2026 ou propriété durable ? | arbitrage |

## Ce que S024 ne fait pas, et pourquoi
- Pas de réglage après lecture des résultats : les 6 cellules sont celles du manifeste,
  figées avant la mesure. Elles disent d'ailleurs toutes la même chose.
- Pas de « wait for new day high », pas de trailing, pas de break-even : il les a tous
  désactivés, on ne les réintroduit pas pour sauver un chiffre.
- Pas de règles communes dans le bras fidèle — et le chiffre justifie la doctrine :
  le coupe-circuit ramènerait l'US30 de +43,5 % à **−0,8 %**, seul résultat négatif
  de tout le dossier.
- Pas de promotion : aucun statut ne change sans décision d'Adrian.
