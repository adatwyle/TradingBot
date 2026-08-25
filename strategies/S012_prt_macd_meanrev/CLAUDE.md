# CLAUDE.md — cc-S012

**Rôle** : Claude Code dédié à la stratégie S012 (`prt_macd_meanrev`, magic `130012`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Contexte hérité

Prototype `s12_prt_macd_meanrev` (en exploitation, lecture seule) : mean reversion D1 long-only sur indices (SP500 source, NASDAQ/DAX transfert à froid). Verdict recherche du prototype : **PAS D'EDGE** — F1 (témoin percentile 51,5), F2 (négatif à spread nul, 38 trades) et F3 (LONGHIST 1927-2026, 464 trades : jours en position +0,8 %/an vs +6,4 %/an B&H) toutes déclenchées. Statut manifest `PAPER` uniquement parce qu'un forward IA scellé est armé (`macd_ai_paper`) ; le rejeu accéléré conclut NE PAS ARMER l'IA. Premier travail attendu : statuer sur ce forward hérité, puis re-évaluer le verdict et explorer d'éventuels chemins d'amélioration (détail dans `input-adrian.md`) — l'archivage n'intervient que sur constat propre, documenté.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S012.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S012_prt_macd_meanrev/
├── CLAUDE.md            # ce fichier, adapté
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S012
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
