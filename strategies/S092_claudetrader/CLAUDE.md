# CLAUDE.md — cc-S092

**Rôle** : Claude Code dédié à la stratégie S092 (`claudetrader`, magic `130092`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Prototype `s92_claudetrader` (lecture seule) au statut `RESEARCH` : `research/ANALYSIS.md` rédigée, `strategy.py` jamais implémentée (symbols vides), pas de VERDICT.md. L'analyse conclut que le concept Hermes n'est pas backtestable (validation paper forward uniquement) et que « rien de ce que fait Hermes ne nous manque » — l'enveloppe cyclique manquante a été construite depuis (factory + gateway + pilote) : le concept a été absorbé par l'infrastructure. **Premier travail attendu** : décider si une stratégie propre subsiste (ex. agent décisionnel journalisé en Phase 1 selon ANALYSIS.md §7) ou si le dossier s'archive comme doublon d'infrastructure — constat documenté, jamais par défaut. La question du coût d'exploitation (ANALYSIS.md §9) se tranche avant toute phase paper.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S092.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S092_claudetrader/
├── CLAUDE.md            # ce fichier, adapté
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S092
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
