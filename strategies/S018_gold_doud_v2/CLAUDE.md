# CLAUDE.md — cc-S018 (or, v2 du résidu S011)

**Rôle** : Claude Code dédié à la stratégie S018. Développement, évaluation, amélioration, parcours de validation paper — de CETTE stratégie uniquement.

## Mission

1. Instruire la question posée par la v1 : le résidu or de S011 (`NON CONCLUSIF`, `strategies/S011_legacy_breakout/research/VERDICT.md` § 2.5) tient-il mieux quand on lui applique les lectures de la méthode Doud ?
2. Maintenir `research/ANALYSIS.md` (hypothèses + protocole), `research/FALSIFICATION.md` (ce qui tuerait la v2, écrit AVANT mesure), `research/VERDICT.md` (ce que les chiffres disent).
3. Faire avancer vers la validation paper — ou constater la non-pérennité, la documenter, et archiver (`RETIRED`).

## Interdit, spécifiquement ici

- **Ne jamais modifier `strategies/S011_legacy_breakout/`.** `studies/gold_forward/run_forward.py:43` importe ce module en direct pour un forward-test scellé en vol. Le scellé protège `params.json` par hash, pas le code : une édition de S011 changerait les signaux de la v1 en silence et invaliderait six mois de mesure. S018 importe les indicateurs de S011 en **lecture seule** — c'est la seule relation autorisée.
- **Ne jamais toucher `studies/gold_forward/`.** C'est le témoin.
- Pas de moteur de backtest maison (R9), pas de signal sans stop (R3), pas de calcul de taille (R2).

## Ce que la v2 ajoute à la v1, et rien d'autre

Cinq commutateurs binaires, chacun traçable à une affirmation datée de `docs/sources/moneytalk/SYNTHESE.md` § 2 :

| Commutateur | Source | Ce qu'il change |
|---|---|---|
| `entry_mode` | D4 (@ 18:08) | entrée au close de cassure → entrée au repli à 50 % de la jambe |
| `channel_source` | D3 (@ 17:52) | canal Donchian sur les mèches → sur les corps |
| `side_mode` | D1 (@ 21:52) | les deux sens → longs seuls |
| `session_filter` | D5 (@ 35:35) | toutes heures → US + Asie, jamais Londres |
| `htf_bias` | D2 (@ 23:32) | aucun biais → porte de tendance journalière |

**La cellule neutre est la v1.** `test_strategy.py::test_cellule_neutre_reproduit_la_v1` le vérifie signal par signal sur 30 024 barres réelles. C'est ce qui rend chaque commutateur mesurable isolément : sans cette égalité, un écart pourrait venir d'une réécriture plutôt que de l'hypothèse.

## Grille et discipline de lecture

32 cellules (2⁵). À 5 %, **≈ 1,6 cellule « gagnante » est attendue par pur hasard** — aucun résultat isolé ne vaut preuve. Tout chiffre se lit avec son nombre de trades sous les yeux (`docs/METHODOLOGY.md`), contre le bras témoin aléatoire, et contre la cellule neutre.

## Structure

```
S018_gold_doud_v2/
├── CLAUDE.md · input-adrian.md · manifest.yaml · strategy.py
├── research/    ANALYSIS.md · FALSIFICATION.md · VERDICT.md
├── backtests/   causality.txt · conformance.txt · grid.txt · results.json
└── test_strategy.py
```
