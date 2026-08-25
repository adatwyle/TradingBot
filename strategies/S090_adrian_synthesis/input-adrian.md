# input-adrian — S090 Fade de l'échec (synthèse Adrian)

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S090 · magic `130090`
- **Source** : Idée Adrian — synthèse d'un motif observé 4× indépendamment dans le corpus du prototype (s91 fade asiatique, s09 §2.7 retournement, s10 résidu NIKKEI, `studies/grid_per_entry`)
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s90_adrian_synthesis\` (lecture seule)

## Principe (résumé)
Dans une tendance H1 (SuperTrend 10/3.0, ADX14 > 20), une excursion adverse profonde (≥ 3 ATR depuis l'extrême de la jambe, sans flip de tendance) est lue comme du flux forcé qui s'épuise. On entre au close dans le sens de la tendance, contre l'excursion, à chaque palier entier d'ATR au-delà du seuil : cible 1 ATR (rétraction partielle), stop 1-2 ATR, pas de sortie temporelle. Univers déclaré : 17 instruments H1 — EURUSD/XAUUSD/DAX = ensemble de DÉCOUVERTE, les 14 autres = mesure décisive.

## État hérité du prototype
- **Statut manifest** : `RESEARCH` — non promue, verdict référencé dans le manifest lui-même (« Ne pas promouvoir »).
- **Verdict 2026-08-17** (`research/VERDICT.md`) : **PAS D'EDGE — motif « fade de l'échec » CLOS.**
  - Juge (F2, pool des 8 instruments hors découverte économiquement viables, cellule primaire t3/tp1/sl1, walk-forward ancré, coûts réels) : **−0,1485 R/t net, IC 95 % [−0,2009 ; −0,0962], n = 1 337** — et **−0,0570 même à coût nul** : le péage n'explique pas l'échec, le signal est absent hors découverte.
  - **15 instruments négatifs sur 17** en cellule primaire réelle.
  - **F8 (dose-réponse) déclenchée** : plus profond n'est PAS meilleur (sl 1 : t2 −0,125 / t3 −0,131 / t4 −0,134) — le mécanisme causal « sur-extension qui se rétracte » (H90) est réfuté.
  - F3a déclenchée : 0 instrument hors découverte ne passe le témoin sur une cellule de seuil ≥ 3.
- **Résidu unique, consigné comme anecdote (pas revendiqué)** : XAUUSD t3_sl1 = **+0,0938 R/t × 191 trades, percentile 96,5** (5/5 graines ; seule cellule du dossier à battre aussi le témoin conditionné à l'état, pct méd 98,5 — avec réserve d'effectif). Règle figée : un seul instrument = anecdote ; XAUUSD appartient de plus à l'ensemble de découverte.
- **Rigueur du prototype** : protocole `research/HYPOTHESIS.md` **figé et commité (`f1e9d0c`) AVANT tout backtest** (grille 6 cellules, falsifications F1-F8, règles de verdict écrites d'avance) ; R1 causalité PASSÉ, R5 conformité CONFORME ; snapshot H1 figé 2021-07 → 2026-08-14.
- Le verdict prototype exclut toute cinquième relecture des MÊMES barres : une réouverture exige une donnée nouvelle (autre broker/coûts, autre granularité, autre période).

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC, documenté).
- Le verdict négatif hérité est une donnée d'entrée, pas un arrêt de mort : le protocole prototype était volontairement le plus dur du corpus. Toute tentative d'amélioration doit néanmoins respecter sa leçon centrale (pas de re-sélection post-hoc sur les mêmes barres ; toute nouvelle mesure exige une donnée ou un angle réellement nouveaux, falsifications déclarées d'avance).
- Le résidu XAUUSD t3_sl1 est la seule piste chiffrée héritée ; s'il est instruit, ce ne peut être qu'en test d'hypothèse scellé (type forward sans argent), jamais comme candidat production direct.
