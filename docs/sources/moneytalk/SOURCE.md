# moneytalk — provenance des sources

Deux épisodes du podcast **MoneyTalk** (chaîne YouTube *Chris Dienda — Moneytalk*,
`@ChrisDiendaMoneytalk`), apportés par Adrian le 2026-09-06 pour instruire la v2
de la stratégie or.

| Fichier | Épisode | Invité·e | Publication | Durée | Sous-titres |
|---|---|---|---|---|---|
| `01_doud_gold_sans_stoploss.txt` | MoneyTalk #29 — « Elle trade le gold sans stop loss… et gagne plus de 50 000 €/mois ? » | **Cindy, alias Doud Trading** — scalpeuse XAUUSD | 2026-06-13 | 80 min | `fr` (auto) |
| `02_rababian_carnet_ordre.txt` | MoneyTalk #30 — « Il révèle comment le carnet d'ordre marche et devenir rentable » | **Karen Rababian** — trader indépendant, carnet d'ordre / futures | 2026-06-19 | 77 min | `fr` (auto) |

URLs : <https://www.youtube.com/watch?v=hpFOfjPNMVU> (#29) et
<https://www.youtube.com/watch?v=GiYOYyJZKio> (#30).

## Comment ces transcripts ont été obtenus

`youtube_transcript_api` (piste `fr`, sous-titres **générés automatiquement** —
aucune piste manuelle n'existe), un segment par ligne, horodatage `[mm:ss]` en
tête. Aucune retouche : ce qui est écrit est ce que la reconnaissance vocale a
produit.

**Conséquence à garder en tête pour toute citation.** La transcription
automatique déforme les noms propres et la ponctuation : « Do Trading » /
« doute trading » pour *Doud Trading*, « Poel » pour *Powell*, « propre firme »
pour *prop firm*, « l'eau » pour *lot*, « fond propre » pour *fonds propres*,
« TP de Lego » pour *TP de l'ego*, « SL suiveur » parfois coupé. Les citations
reprises dans `SYNTHESE.md` sont **normalisées à la lecture** (orthographe des
termes techniques rétablie) mais jamais reformulées : le fond, l'ordre des mots
et l'horodatage renvoient au fichier brut, vérifiables ligne à ligne.

## Sources web complémentaires (consultées le 2026-09-06)

- <https://doudtrading.fr> — offre commerciale : lives quotidiens **39,99 €/mois**
  (« 3 à 5 sessions par semaine, dès 14h », sessions US + « open asian certains
  soirs »), accompagnement VIP sur candidature, « +3000 traders dans la
  communauté ».
- <https://doudtrading.fr/pamm> — page de sondage pour un **compte PAMM** chez
  « AGBK (broker régulé) » : *+145 % rendement 24/25*, *28 % drawdown max*,
  *Sharpe 5,6*, *89 % de taux de réussite*, investissement minimum 1 000 €.
  La même page affiche plus bas *« +127 % en 2024 »*.
- <https://doudtrading.fr/lives> — cadence et horaires des lives.

Aucun relevé de courtier, aucun lien Myfxbook/FXBlue public, aucune piste
auditable n'accompagne ces chiffres. Ils sont **enregistrés comme déclarations
commerciales**, pas comme données. Voir `SYNTHESE.md` § 4.

## Ce que ces sources ont produit dans le dépôt

`strategies/S018_gold_doud_v2/` — v2 du résidu or de `S011_legacy_breakout`.
La lignée, les hypothèses retenues et celles refusées sont dans
`strategies/S018_gold_doud_v2/research/ANALYSIS.md`.
