# CLAUDE.md — cc-S006

**Rôle** : Claude Code dédié à la stratégie S006 (PBD Impulse-Range — Patrick Nil, slug `nil_pbd`, magic `130006`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Le prototype (`C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s06_nil_pbd\`, lecture seule) a conclu **PAS D'EDGE** : 0 config STRICT sur 224 (≈ 11 attendues par hasard), −0,022 R/trade même à coût nul, 4 falsifications sur 5 déclenchées. Fait notable : win rate et séries de pertes annoncés par la source se reproduisent fidèlement — et le système perd quand même ; la fréquence mesurée est ~10× inférieure à l'annonce (l'écart discrétionnaire non capturé par le code). Premier travail attendu : re-évaluer ce verdict et explorer les pistes ouvertes — combler l'écart de fréquence par une sélection plus fine, exploiter l'effet stop large (+0,05 à +0,15 R/trade), réutiliser la brique de détection impulsion → range — avant toute décision d'archivage (constat propre, documenté).

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S006.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S006_nil_pbd/
├── CLAUDE.md            # ce fichier, adapté
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S006
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
