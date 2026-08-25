# CLAUDE.md — cc-S010

**Rôle** : Claude Code dédié à la stratégie S010 (`legacy_meanrev`, magic `130010`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Le prototype (`C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s10_legacy_meanrev\`, lecture seule) a rendu un verdict **PAS D'EDGE** sur 7/8 instruments (NIKKEI non conclusif) : 19 STRICT contre ~43 attendues par hasard, −0,0017 R/trade au spread réel contre +0,0748 à spread nul — le spread consomme exactement l'edge brut, et 0,5 pip de slippage referme la porte. Le filtre S/R n'apporte rien de mesurable ; tous les chiffres antérieurs au 15.08.2026 (dont le +612 CHF/an) sont invalidés (bug `closes[-1]`). Premier travail attendu : re-évaluer ce verdict, puis explorer les pistes d'amélioration ouvertes par le prototype — déclencheur de divergence seul sur timeframe plus élevé et instrument à faible drag de spread, résidu NIKKEI — avant tout constat de non-pérennité ou migration du code.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S010.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S010_legacy_meanrev/
├── CLAUDE.md            # ce fichier
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S010
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
