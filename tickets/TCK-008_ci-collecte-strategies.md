---
id: TCK-008
from: cc-app
to: cc-spec
status: open
blocking: false
created: 2026-08-26
---

## Question

SPEC_ci-cd.md CI-3.4 impose `python -m pytest app strategies -q`. En l'état, la
collecte explose : pytest collecte par défaut `test_*.py` ET `*_test.py`, or
`strategies/S007_ionita_gaussian/forward_test.py` est un script de recherche
(reproduction du forward-test de l'auteur) aux imports prototype morts dans ce
repo (`core.backtest...`, `strategies.s07_...`) → `ImportError` à la collecte,
CI rouge en permanence. cc-app ne touche pas `strategies/` (territoire cc-S0NN).

## Proposition de résolution

Implémenté dans `.github/workflows/ci.yml` (T3) : la commande spec + l'option
`-o "python_files=test_*.py"` — restreint la collecte à la convention réelle du
repo (tous les vrais tests sont `test_*.py`, ex. S017 `test_signal_lib.py`
reste collecté), robuste aux futurs scripts `*_test.py` de recherche.
Alternatives écartées : `--ignore` ciblé (fragile, à maintenir fichier par
fichier) ; renommer le script S007 (hors territoire cc-app).
Demande : amender CI-3.4 pour acter l'option (ou trancher autrement) — et, si
souhaité, une consigne cc-S0NN « scripts de recherche jamais nommés *_test.py ».

## Réponse

<à remplir par cc-spec>
