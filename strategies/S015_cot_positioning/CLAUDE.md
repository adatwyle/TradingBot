# CLAUDE.md — cc-S015

**Rôle** : Claude Code dédié à la stratégie S015 (COT Positioning — CFTC, magic `130015`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Prototype `s15_cot_positioning` en statut `RESEARCH` : protocole intégralement gelé le 2026-08-19 (ANALYSIS.md + FALSIFICATION.md), mais **aucun backtest exécuté et pas de strategy.py**. Attente a priori déclarée : edge faible ou nul (Klitgaard & Weir, FRBNY 2004 — le COT est synchrone, pas prédictif). Le protocole a été refusé en review : effectif d'épisodes indépendants au hold-out insuffisant face au plancher dérivé de 12 (FALSIFICATION.md §6) ; recadrage en attente d'Adrian (3 options posées, aucune tranchée). Premier travail attendu : instruire ce recadrage et proposer une recommandation documentée — un protocole recadré et regelé précède tout backtest. Infrastructure réutilisable : `core/data/cot.py` anti-fuite (lecture seule), données COT Legacy depuis 1986.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S015.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.
- Spécifique S015 : la donnée COT ne se lit que via `cot.connu_au()` ; `core/data/cot.py` reste en lecture seule ; le contrôle de fuite (gate F0 du prototype) reste un préalable à toute lecture de résultat.

## Structure du dossier

```
S015_cot_positioning/
├── CLAUDE.md            # ce fichier, adapté
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S015
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
