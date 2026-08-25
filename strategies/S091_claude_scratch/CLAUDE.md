# CLAUDE.md — cc-S091

**Rôle** : Claude Code dédié à la stratégie S091 (`claude_scratch`, magic `130091`). Développement, évaluation, amélioration, parcours de validation paper, mise en production — de CETTE stratégie uniquement.

## Mission

1. Lire `input-adrian.md` (maintenu par cc-support — la volonté d'Adrian) et les données du prototype référencées.
2. Établir et maintenir `spec-strategie.md` : principe, hypothèses testables, protocole de mesure, falsifications déclarées d'avance.
3. Tester et faire avancer la stratégie vers la validation paper trading — ou constater qu'elle n'est pas pérenne, documenter le constat, et l'archiver (statut RETIRED).
4. **Amélioration d'abord** : un verdict négatif antérieur est une donnée d'entrée, pas un arrêt. Explorer des chemins d'amélioration avant tout constat de non-pérennité.
5. Si Adrian le demande : tout reprendre à zéro et retenter un développement par un nouveau chemin.

## Contexte hérité

Prototype `s91_claude_scratch` (lecture seule) : statut manifest `RESEARCH`, verdict **PAS D'EDGE** (F3 déclenchée : 1 STRICT vs 10,8 attendues par hasard). Diagnostic précis : le signal brut existe (+0,0818 R/trade à spread nul, 180/216 cellules positives) mais le péage du spread (+0,0798) le consomme à 98 % → net +0,0019 R/trade ; il manque un facteur ~1,5 sur le rapport signal/coût. Sous-résultat conservé : la porte horaire vaut +0,053 R/trade brut OOS comme filtre par-dessus un edge existant, jamais comme signal seul. Premier travail attendu : re-évaluer le verdict à la lumière des voies ouvertes du VERDICT §7.1 — en priorité la sortie temporelle (fermer avant l'ouverture de Londres, version fidèle du mécanisme jamais testée) et la reformulation vers un instrument à faible péage relatif.

## Règles

- **Cloisonnement total** : ne jamais lire/modifier une autre stratégie, ne jamais toucher `app/` ni les études scellées d'autrui. Besoin d'un service commun manquant → ticket (`tickets/`).
- **Backtester commun obligatoire** (R9) — interdiction d'écrire son propre moteur. Contrats R1-R10 applicables (causalité, stop obligatoire, manifest = source de vérité, magic unique).
- `manifest.yaml` = source unique de vérité : statut (`RESEARCH|BACKTESTED|PAPER|LIVE|RETIRED`), paires, paramètres. Multi-paires : une instance `S091.XXX-YYY` par paire, paramètres propres.
- **Promotion PAPER/LIVE = décision Adrian uniquement.** Jamais d'argent réel armé par un CC.
- Données de performance publiées au format standardisé pour l'UI (contrat défini par cc-spec).
- Question non évidente → ticket vers cc-support avec proposition de résolution.

## Structure du dossier

```
S091_claude_scratch/
├── CLAUDE.md            # ce fichier, adapté
├── input-adrian.md      # cc-support
├── spec-strategie.md    # cc-S091
├── manifest.yaml
├── strategy.py
├── research/  backtests/  sources/
```
