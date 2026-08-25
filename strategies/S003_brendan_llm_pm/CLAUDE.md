# CLAUDE.md — cc-S003

**Rôle** : Claude Code dédié à la stratégie S003 (`brendan_llm_pm`, magic `130003`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Le prototype (`C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s03_brendan_llm_pm\`, lecture seule) est un squelette jamais implémenté : statut `RESEARCH`, `strategy.py` en `NotImplementedError`, `ANALYSIS.md` vide (placeholder), aucun verdict ni backtest. Seul contenu réel : 67 captures d'écran de la vidéo source (dupliquées dans deux sous-dossiers de `research/screenshots/`). Premier travail attendu : réaliser la Phase 1 — reformuler la méthode de Brendan (un LLM en gérant de portefeuille) à partir des captures et de la vidéo, évaluer sa reproductibilité avec nos données, et formuler l'hypothèse testable avant toute ligne de code.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S003.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S003_brendan_llm_pm/
├── CLAUDE.md            # ce fichier
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S003
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
