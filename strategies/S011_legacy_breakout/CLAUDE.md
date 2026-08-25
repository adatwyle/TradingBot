# CLAUDE.md — cc-S011

**Rôle** : Claude Code dédié à la stratégie S011 (`legacy_breakout`, magic `130011`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Prototype `s11_legacy_breakout` (lecture seule) en statut manifest **PAPER** — le plus avancé du dépôt historique. Verdict Phase 4 : **PAS D'EDGE** global (signal de cassure à espérance nulle ; filtre de régime `combo_011_050` réfuté pour sur-ajustement — voisinage 0/9), mais résidu **XAUUSD `NON CONCLUSIF`** (+0,226 R/trade sur 400 trades, voisinage 9/9, deux côtés positifs), actuellement instruit par un **forward scellé armé** (`studies/gold_forward/`, intangible — au 2026-08-25 : 3 trades clos, +0,64 R, aucun critère d'arrêt atteint). Composant non reproduit : trailing/break-even (le moteur commun ne déplace pas de stop, R9). Premier travail attendu : s'approprier `research/ANALYSIS.md` + `VERDICT.md`, laisser courir le forward sans y toucher, et re-évaluer le verdict en explorant les pistes ouvertes (walk-forward glissant, test dédié à l'or, autres formalisations de la cassure).

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui — dont `studies/gold_forward/` (scellé : toute modification invalide le test). Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S011.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S011_legacy_breakout/
├── CLAUDE.md            # ce fichier, adapté
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S011
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
