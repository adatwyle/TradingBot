# CLAUDE.md — cc-S093 (alexg_ai_judge)

**Rôle** : Claude Code dédié à la stratégie S093 (AlexG AI Judge, magic `130093`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Prototype `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s93_alexg_ai_judge\` (EN EXPLOITATION — lecture seule stricte), statut manifest `RESEARCH`. Le rejeu à l'aveugle du 2026-08-16 a confirmé la falsification centrale : 191 candidats jugés, paquet à −0,154 R/trade, seule cellule à effectif suffisant (avec COT, seuil 50 %, n=39) à +0,222 R/trade au percentile 88,5 contre un seuil de 95 déclaré d'avance ; F3 falsifiée (monter le seuil de grade dégrade : +0,222 → −0,385 → −0,488). Mais l'univers testé était faux (13 paires manquaient au catalogue interne, pas au broker) : une re-mesure forward est scellée depuis le 2026-08-22 (`studies/alexg_paper`, 26 paires, 4 bras MECH/AI/RND/SHADOW, verdict à ~40 décisions IA ≈ 3,2 mois). **Premier travail attendu** : établir `spec-strategie.md`, suivre le forward sans le perturber, ré-évaluer le verdict sur l'univers réel à mesure des résultats, et explorer les chemins d'amélioration listés dans `input-adrian.md` (élargissement d'échantillon re-falsifié, filtre COT mécanique sans juge).

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S093.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S093_alexg_ai_judge/
├── CLAUDE.md            # ce fichier
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S093
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
