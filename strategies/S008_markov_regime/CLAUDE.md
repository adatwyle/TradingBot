# CLAUDE.md — cc-S008

**Rôle** : Claude Code dédié à la stratégie S008 (Markov Regime Switching, magic `130008`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Prototype `s08_markov_regime` (lecture seule, `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s08_markov_regime\`) : statut `RESEARCH`, verdict **PAS D'EDGE** (2026-08-16) — 0 victoire contre le buy & hold sur 6 instruments D1 et 10-12 ans, écarts de 2,1 à 36 points de CAGR, 4 falsifications sur 5 déclenchées, R1/R5 passés. La reproduction est propre : c'est la méthode qui ne rend rien, pas le test. Premier travail attendu : re-évaluer le verdict et cadrer dans `spec-strategie.md` un chemin d'amélioration réellement nouveau (variante non couverte par la grille du prototype, ou réorientation en outil de mesure de persistance de régime identifiée par le prototype) — sinon documenter la non-pérennité et archiver.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S008.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S008_markov_regime/
├── CLAUDE.md            # ce fichier, adapté
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S008
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
