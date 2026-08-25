# CLAUDE.md — cc-S007

**Rôle** : Claude Code dédié à la stratégie S007 (`ionita_gaussian`, magic `130007`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Prototype `s07_ionita_gaussian` en statut `RESEARCH`, verdict PAS D'EDGE global (786 % contre 1 141 % pour l'équipondéré naïf BTC/ETH 2018-2026, Sharpe inférieur), mais protection bear-market réelle et mesurée (fenêtres OOS baissières +22,7 %/−17,3 % contre −3,6 %/−39,2 % pour BTC). La jambe short dégrade tout ; un bug `allocation_engine` (décalage d'une barre) est documenté et contourné localement. Premier travail attendu : re-dérouler le verdict sur des bases propres (le `VERDICT.md` du prototype n'a jamais été rédigé), puis explorer l'exploitation du mécanisme de protection baissière en long-only — en clarifiant d'abord le statut du bug core pour ne pas backtester sur un moteur biaisé.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique). Particularité S007 : contrat `allocation` (`AllocationModule`) — R1 et walk-forward passent par les points d'entrée dédiés du prototype, pas par les CLI épisodiques standard.
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S007.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S007_ionita_gaussian/
├── CLAUDE.md            # ce fichier, adapté
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S007
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
