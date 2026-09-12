# CLAUDE.md — cc-S024 (Go Long, René Balke)

**Stratégie** : `S024_balke_go_long` · magic `130024` · statut **BACKTESTED**
**Manifeste** : `manifest.yaml` — source unique de vérité (R7)
**Intentions d'Adrian** : `input-adrian.md` (reformulées par cc-support)

## Ce que cette stratégie est

Un achat d'indice **tous les jours à heure fixe**, revendu le soir à heure fixe.
Aucun filtre, aucune analyse, ni stop ni cible chez l'auteur. DAX, NASDAQ, US30 en
H1. C'est la stratégie qui porte plus de la moitié de son profit live déclaré, et
c'est **du bêta indiciel assumé** : lui-même ne prétend à aucun signal.

Reproduite telle quelle, puis mesurée — dans cet ordre, et sans avis intermédiaire.

## Doctrine (Adrian, 2026-09-12)

**Chaque stratégie porte ses propres règles.** Aucune règle générale de trading ne
la veto. Les règles communes (refroidissement, coupe-circuit) protègent le
portefeuille des pertes consécutives ; elles sont ici **mesurées en second bras,
jamais imposées au bras fidèle** — et le chiffre justifie la doctrine : elles
ramènent l'US30 de +49,2 % à +2,2 %.

**Pas d'avis avant d'avoir essayé.** `research/FALSIFICATION.md` est écrit avant le
harnais ; le scepticisme s'exprime là, pas dans un paragraphe de position.

## Où en est le dossier

`research/VERDICT.md` : **réussite en tant que bêta indiciel, pas d'edge de timing**
— formulation imposée d'avance par la falsification. Positive sur les trois indices
au spread mesuré (**+47,9 % DAX, +71,4 % NASDAQ, +43,5 % US30** sur 5,07 ans),
fidèle au live de l'auteur sur les quatre repères F1-F4, mais l'heure d'entrée ne bat
pas les autres heures sur les indices américains (percentile 31,8 et 63,6 sur 23).

**La trouvaille** : ce qui paie n'est pas l'heure, c'est d'être à plat hors séance.
Sur la population comparable (journées réellement tradées), la jambe overnight est
**négative sur les trois indices** (−11,4 / −4,8 / −11,2 % composés) et la jambe
intraday seule bat l'acheter-et-tenir **partout**.

**Le dossier a été corrigé après revue** (ADDENDUM A1-A6 de `FALSIFICATION.md`) :
les % étaient surévalués d'un tiers sur DAX, et le « contre-exemple NASDAQ » du
premier rapport était un artefact d'étalon. Lire l'addendum avant de citer un
chiffre d'une version antérieure.

**Réserve n°1, décisive** : le swap n'est pas modélisé. Il le chiffre à ≈ 6 %/an sur
le DE40, soit ≈ 30 points sur notre période — face à ça, la comparaison du verdict
est défavorable à la stratégie. Le mesurer chez Swissquote est la prochaine mesure
qui compte, et c'est de la donnée, pas du réglage.

## Frontières

| Fait | Ne fait JAMAIS |
|---|---|
| Modifie `strategies/S024_balke_go_long/` | Touche une autre stratégie, `app/`, ou une étude scellée |
| Instruit ses pistes une par une, falsification écrite d'avance | Ajoute une cellule après avoir vu les résultats |
| Mesure, publie le verdict | Promeut en PAPER ou LIVE — décision Adrian seule (R10) |

## Où sont les choses

```
strategy.py                la règle, et rien d'autre (un horaire, pas un indicateur)
manifest.yaml              6 cellules, cellule de fidélité garde 5 % / offset 0
test_s024_strategy.py      27 tests — calendrier, séances, trous, géométrie, R1/R5, bornes
backtests/run_wf.py        harnais 3 indices (séance dérivée des barres, étalons, WF, témoins)
backtests/results.json     la mesure du 2026-09-12
backtests/run_all.log      le journal complet du run
research/FALSIFICATION.md  critères, écrits avant
research/VERDICT.md        ce que la mesure a rendu
input-adrian.md            intentions d'Adrian
```

## Quatre pièges de ce dossier, à ne pas redécouvrir

0. **Le % ne se calcule PAS sur `exit_price − entry_price`.** Le moteur replie le
   coût de bord d'ENTRÉE dans `entry_price` mais stocke `exit_price` BRUT et ne
   déduit le coût de SORTIE que dans `pnl_r` : cette formule ne paie que la MOITIÉ
   du spread. Utiliser `pnl_r × risk_distance / entry_price` (helper `trade_pct`).
   Ce bug a surévalué le dossier de 4 à 9 points de % avant correction.
1. **Le R n'est pas comparable entre gardes.** `pnl_r = gross / (entrée × guard_pct)` :
   la garde 3 % affiche deux fois le R de la garde 10 % pour le même %. **Seul le %
   du prix d'entrée a un sens transversal ici.**
2. **Le bras témoin commun ne mesure rien sur cette stratégie.**
   `anchored_wf._allowed_positions` recopie le filtre horaire quand la stratégie
   couvre moins de 80 % des heures — c'est notre cas (une seule heure d'entrée), donc
   le témoin tire ses entrées à la même heure. Le **balayage horaire exhaustif** de
   `run_wf.py` le remplace. Ne pas « corriger » le module commun pour ça.
3. **Le balayage horaire est confondu avec l'overnight sur un marché à séance.**
   À nombre de barres constant, entrer plus tard fait déborder la fenêtre hors
   séance : sur DAX, 23 h d'horloge contre 13 h à l'heure de fidélité. La colonne
   `duree_horloge_h` existe pour rendre ce biais visible — la lire avant de conclure
   quoi que ce soit d'un rang.

## Avant de toucher au code

1. `python -m pytest strategies/S024_balke_go_long -q` doit être vert.
2. Toute nouvelle piste = nouvelle section dans `FALSIFICATION.md` **avant** de la
   mesurer, avec ses seuils.
3. Le nom des fichiers de test doit rester unique dans le dépôt (`test_s024_*`) —
   deux `test_strategy.py` ont déjà cassé la collecte pytest une fois.
4. `run_wf.py` **dérive la séance des barres** (`session_profile`) : ne jamais coder
   en dur 23 ou 14 barres. Si le courtier change ses horaires, le harnais doit le
   montrer, pas le masquer.
5. La **porte R1/R5** du § 1 arrête le run et n'écrit aucun `results.json` si un
   contrôle tombe (`DispositifEnDefaut`, code de sortie 2). Ne pas la contourner :
   elle existe pour qu'un bug de dispositif ne devienne jamais un résultat publié.
