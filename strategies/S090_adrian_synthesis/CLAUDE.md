# CLAUDE.md — cc-S090

**Rôle** : Claude Code dédié à la stratégie S090 « Fade de l'échec (synthèse Adrian) » (`adrian_synthesis`, magic `130090`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Le prototype (`C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s90_adrian_synthesis\`, lecture seule) a rendu le 2026-08-17 un verdict **PAS D'EDGE — motif clos**, sous le protocole le plus dur du corpus (HYPOTHESIS.md figé avant backtest, commit `f1e9d0c`) : juge hors découverte −0,1485 R/t net (IC 95 % [−0,2009 ; −0,0962], n = 1 337), négatif même à coût nul (−0,0570), 15/17 instruments négatifs, dose-réponse F8 réfutant le mécanisme causal. Résidu unique consigné comme anecdote : XAUUSD t3_sl1 (+0,0938 R/t × 191, pct 96,5). Statut manifest : `RESEARCH`, non promue.
**Premier travail attendu** : re-évaluer ce verdict à froid, puis identifier des chemins d'amélioration légitimes — donnée ou angle réellement NOUVEAUX (autre période, autre granularité, autres coûts, ou instruction scellée du résidu XAUUSD en test d'hypothèse sans argent) — jamais une cinquième relecture des mêmes barres. Si aucun chemin ne tient : constat de non-pérennité documenté, statut RETIRED.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S090.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S090_adrian_synthesis/
├── CLAUDE.md            # ce fichier
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S090
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
