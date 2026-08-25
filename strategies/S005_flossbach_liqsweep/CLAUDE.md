# CLAUDE.md — cc-S005

**Rôle** : Claude Code dédié à la stratégie S005 (`flossbach_liqsweep`, magic `130005`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Le prototype (`C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s05_flossbach_liqsweep\`, lecture seule) a conclu **PAS D'EDGE** sur son proxy de la méthode : H4 +0,0057 R/trade (2 343 trades, indistinguable de zéro), H1 −0,122 R/trade (11 557 trades, négatif même à spread nul), WR 26,6 % contre 70-80 % annoncés, 0 réussite STRICT sur 704 cellules de walk-forward H4. Sous-verdict NON CONCLUSIF sur la méthode originale : le proxy de liquidité (extrêmes de swing) remplace un indicateur propriétaire indisponible, la crypto est intestable, et trois écarts défavorables (news, prises partielles, stop au point mort) font du WR mesuré un plancher. Premier travail attendu : re-évaluer le verdict à la lumière de ces limites et explorer les chemins d'amélioration listés dans `input-adrian.md` (proxy alternatif, réplication des composants transférables) avant tout constat de non-pérennité.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S005.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S005_flossbach_liqsweep/
├── CLAUDE.md            # ce fichier
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S005
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
