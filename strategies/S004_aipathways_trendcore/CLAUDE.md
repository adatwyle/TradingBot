# CLAUDE.md — cc-S004 (aipathways_trendcore)

**Rôle** : Claude Code dédié à la stratégie S004 (magic `130004`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Contexte hérité

Prototype `s04_aipathways_trendcore` (lecture seule : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s04_aipathways_trendcore\`) : bascule d'allocation QQQ/GLD sur MM200 en D1, toujours investie. Verdict Phase 4 : `NON CONCLUSIF` (14 bascules sur 4,31 ans), puis dossier **clos** par l'étude `studies/trend_core_50y` — sur 55,5 ans et 284 bascules, ΔSharpe −0,100 contre le 50/50 naïf, 77,9 % de tirages défavorables. La stratégie a servi de démonstration pour créer le contrat AllocationModule. Premier travail attendu : re-évaluer le double verdict hérité par ton propre constat, puis explorer les seules pistes non réfutées (repli cash au lieu de l'or ; MM200 comme filtre de volatilité/modulation du risque plutôt que règle d'allocation) — ou documenter la non-pérennité et archiver (`RETIRED`). Détail dans `input-adrian.md`.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S004.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S004_aipathways_trendcore/
├── CLAUDE.md            # ce fichier, adapté
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S004
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
