# CLAUDE.md — cc-S013

**Rôle** : Claude Code dédié à la stratégie S013 (`macd_fx`, magic `130013`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Prototype `s13_macd_fx` (lecture seule) : verdict **EDGE CANDIDAT (faible)** — la seule candidate positive du dépôt. Survivante AUDCAD ext-long D1 (MACD/ATR sous 10e percentile 252 j, ±1,5 ATR), hold-out scellé +0,58 R/t × 11 trades (percentile 96) ; EURJPY jumelle en observation (n'a pas battu son beta au hold-out). Statut manifest `PAPER`, forward scellé zéro argent armé (`studies/s13_forward`, 0 trade clos, ~7 trades/an). Premier travail attendu : re-évaluer le dossier, laisser courir le forward sans toucher à la config figée, et explorer des chemins d'amélioration à côté (ex. extension au panier des 9 paires — espérance poolée +0,020 R/t, plus mince mais plus fréquente).

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S013.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S013_macd_fx/
├── CLAUDE.md            # ce fichier
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S013
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
