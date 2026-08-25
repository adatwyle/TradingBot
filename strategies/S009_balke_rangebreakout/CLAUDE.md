# CLAUDE.md — cc-S009

**Rôle** : Claude Code dédié à la stratégie S009 (Session Range Breakout — René Balke, magic `130009`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Le prototype (`C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s09_balke_rangebreakout\`, lecture seule) a conclu **PAS D'EDGE** en statut `RESEARCH` : config live USDJPY −7,01 R OOS (511 trades, percentile témoin 66,5), GBPUSD −17,10 R OOS (428 trades), le péage spread consommant 100 % du signal brut (brut/péage 0,82, seuil 1,5) et le positif USDJPY expliqué par le beta yen. La source publie elle-même une perte live GBPUSD de −8 778 €. Premier travail attendu : re-évaluer ce verdict et instruire les pistes documentées — en priorité le résidu « trade #2 retournement » des configs 2-breakouts (+0,0888 R/trade × 367 trades, non concluant faute de témoin à effectif corrigé) — avant tout constat de non-pérennité ou migration du code.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S009.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S009_balke_rangebreakout/
├── CLAUDE.md            # ce fichier
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S009
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
