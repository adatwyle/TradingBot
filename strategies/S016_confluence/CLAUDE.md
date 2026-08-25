# CLAUDE.md — cc-S016 (confluence)

**Rôle** : Claude Code dédié à la stratégie S016 (`confluence`, magic `130016`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Le prototype (`C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s16_confluence\`, lecture seule) est au statut `RESEARCH` : cadrage seul (`research/ANALYSIS.md`), aucun code, aucun protocole scellé. La stratégie est bloquée par construction : 3 des 4 entrées sont sans valeur connue (sentiment : verdict mi-octobre 2026 ; COT : s15 en suspens ; avis de Claude : mesuré NE PAS ARMER), et la condition de scellement est écrite d'avance — au moins 2 des 3 conseils avec un verdict rendu. Avertissement inscrit : le swing sur tendances générales est le régime réfuté 4× dans le dépôt ; les seules poches positives mesurées sont des retours à la moyenne. Premier travail attendu : re-évaluer l'état des piliers et le cadrage hérité, identifier ce qui est mesurable dès maintenant (l'architecture de bras parallèles A0-A5 + SHADOW l'est), et proposer un chemin — sans sceller ni coder la combinaison tant que la condition héritée n'est pas remplie ou explicitement révisée par Adrian.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S016.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S016_confluence/
├── CLAUDE.md            # ce fichier
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S016
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
