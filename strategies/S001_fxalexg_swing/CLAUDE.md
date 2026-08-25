# CLAUDE.md — cc-S001

**Rôle** : Claude Code dédié à la stratégie S001 (`fxalexg_swing`, magic `130001`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Le prototype `s01_fxalexg_swing` (`C:\Datas\Projects\TradingBot_9.0.0.x\`, lecture seule) est en statut `BACKTESTED` avec verdict `PAS D'EDGE` : 19 réussites STRICT contre ~45 attendues par hasard sur 896 cellules (5,1 ans MT5), signal indiscernable d'une pièce à spread nul. Sous-verdict séparé : résidu XAUUSD `NON CONCLUSIF` (+3,21 R de moyenne OOS sur la grille, mais 72 % du résultat concentré sur 2022) — à l'origine de l'étude gold. Premier travail attendu : re-évaluer ce verdict et explorer les chemins d'amélioration listés dans `input-adrian.md` (autre formalisation de la structure, test dédié XAUUSD, structure comme filtre plutôt que signal) ; archivage seulement sur constat propre documenté.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S001.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S001_fxalexg_swing/
├── CLAUDE.md            # ce fichier
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S001
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
