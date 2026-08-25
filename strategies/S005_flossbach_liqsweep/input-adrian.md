# input-adrian — S005 Flossbach Liquidation Sweep

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S005 · magic `130005`
- **Source** : YouTube — Tim Flossbach (IQ Capital, https://www.youtube.com/watch?v=BewBId1gbqQ)
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s05_flossbach_liqsweep\` (lecture seule)

## Principe (résumé)
Repérer un amas de liquidité (≥ 2 extrêmes de swing non balayés tenant dans une bande de 1 ATR), attendre son balayage, puis n'entrer qu'après formation de la structure de retournement (creux plus haut + cassure nette du sommet intermédiaire). Stop sous l'extrême du balayage ou sous le creux plus haut, cible sur l'amas opposé, R:R ≥ 2 obligatoire. 11 instruments / 4 familles (forex, métaux, indices, énergie), H4 principal, H1 secondaire. La détection propriétaire de la source (X-Ray, carnets crypto agrégés) est indisponible : le prototype teste un proxy structurel dérivé de la description du trader.

## État hérité du prototype
- **Statut manifest** : `RESEARCH`. R1 (causalité) passé, R5 vérifié localement (`core/validation/conformance.py` absent du dépôt — lacune signalée). Moteur commun au commit `66668d1`.
- **Verdict (research/VERDICT.md)** : **PAS D'EDGE.**
  - H4 (principal) : **+0,0057 R/trade sur 2 343 trades**, IC 95 % [−0,065 ; +0,077], t = +0,16 — indistinguable de zéro.
  - H1 (secondaire, effectif 5×) : **−0,1220 R/trade sur 11 557 trades**, t = −7,22 — et **−0,0719 même à spread nul**.
  - Win rate **26,6 %** (H4) et **22,0 %** (H1) contre **70-80 % annoncés** : claim central réfuté d'un facteur trois.
  - Walk-forward ancré : **0 réussite STRICT sur 704 cellules** (H4), 5 (H1), contre ~35 attendues par pur hasard.
  - Falsifications déclarées ex ante : F1 (H1), F2, F4 et F5 déclenchées ; F3 non déclenchée (exiger le balayage ne dégrade jamais le résultat — seul point en faveur de la source).
  - Asymétrie directionnelle massive dont le côté gagnant s'inverse entre H4 et H1 ; 84 % de la contribution positive H4 vient de deux instruments (AUDUSD, USDCHF).
- **Sous-verdict** : **NON CONCLUSIF sur la méthode originale** — le test réfute le proxy structurel, pas la méthode équipée de X-Ray, sur Bitcoin (intestable : absent du catalogue Swissquote), avec sorties partielles. Trois écarts défavorables assumés : pas de filtre news, pas de prises partielles, pas de stop au point mort — le 26,6 % mesuré est un plancher.
- **Transférable identifié (VERDICT §7)** : (1) « attendre la structure de retournement » est le seul écart significatif à 95 % de l'étude sur H4 (A − C, t = +2,03), non répliqué sur H1 ; (2) le contrôle placebo (mêmes géométries, entrée aléatoire) mérite d'être systématisé ; (3) un R:R ≥ 2 mécanique sans gestion partielle détruit l'échantillon.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC, documenté).
- Le verdict hérité est une donnée d'entrée, pas un arrêt de mort : les pistes non explorées par le prototype (proxy de liquidité alternatif, gestion partielle si le moteur l'autorise un jour, réplication multi-timeframes des composants transférables) sont des chemins d'amélioration légitimes à évaluer avant tout constat.
