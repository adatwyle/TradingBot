---
id: TCK-020
from: cc-support
to: cc-spec
status: open
blocking: false
created: 2026-09-12
---

## Question

Adrian demande de reproduire et de tester la **grille martingale bidirectionnelle** de
René Balke (vidéo « FULL CODE for this 99% WIN Forex Trading Robot », 2025-12-20,
94 min — règle intégralement extraite, horodatée, pseudocode reconstitué). Numéro
réservé : **S021, magic 130021**.

Le moteur commun ne sait pas l'exprimer. Ce n'est pas un détail d'implémentation :
`core/backtest/engine.py` exécute chaque `Signal` **seul**, avec **son** stop et **sa**
cible, en **R**, sans notion de taille ni de panier — et `Signal.__post_init__` lève si
le stop est absent. Or la stratégie est, par construction :

| Ce qu'elle fait (extrait de la vidéo) | Ce que le moteur sait |
|---|---|
| N positions de **même sens** ouvertes en même temps, à des prix différents | une position à la fois (`max_positions=1`, ou positions indépendantes) |
| lot de chaque ajout = lot précédent × `multiplier` (0,05 → 0,15 → 0,45) | aucune taille : P&L en R uniquement (R2 par design) |
| **une seule sortie** : fermeture du panier entier quand le bid dépasse le **prix moyen pondéré par les lots** + `tp_points` | sortie par position (SL/TP/EOD) |
| **aucun stop par position** ; la seule perte possible est le stop-out du courtier | stop obligatoire (`Signal` lève) |
| deux paniers **indépendants en décision, solidaires en équité** (achat et vente simultanés) | pas d'équité, pas de marge |
| coût de bord payé **N fois** par panier, pondéré par les lots | une fois par trade |

**Directive Adrian du 2026-09-12** : *« chaque stratégie porte ses propres règles ; les
règles communes servent à éviter les pertes consécutives ; laisser à chaque stratégie
sa chance de pousser à l'extrême son aventure »*. Un moteur qui ne peut pas rejouer
la règle ne lui laisse pas sa chance. C'est donc une capacité à construire, pas une
raison de refuser.

## Proposition de résolution

Étendre le moteur commun (R9 : pas de moteur parallèle) d'un **mode panier**, inerte
par défaut — une stratégie sans plan de panier garde exactement le comportement actuel,
donc aucun chiffre existant ne bouge (même exigence que TCK-014).

Capacités à spécifier, dans l'ordre où elles se conditionnent :

1. **Positions multiples de même sens**, chacune avec son prix d'ouverture et son
   volume **relatif** (1, m, m², …). La stratégie émet des volumes relatifs ; la couche
   risque fixe l'unité de base et le plafond absolu — c'est la façon de respecter
   l'esprit de R2 sans castrer l'idée.
2. **État de panier** : prix moyen pondéré par les volumes, recalculé à chaque barre ;
   **clôture groupée atomique** au même instant et au même prix ; comptabilisée comme
   UN événement « panier » en plus des N lignes du ledger.
3. **Stop DE PANIER** — perte maximale acceptée ou profondeur maximale, déclarée au
   niveau du panier et non par position. C'est une règle propre à la stratégie au
   sens de la directive ; sans elle le backtest ne peut jamais produire l'événement
   qui définit la stratégie (la ruine), et le résultat serait un mensonge par
   omission. À spécifier aussi : **simulation de la marge et du stop-out** du courtier.
4. **Deux paniers simultanés** partageant une seule équité (comptabilité en devise,
   pas seulement en R) — les simuler séparément puis additionner masquerait
   précisément le mode de mort.
5. **Coût de bord par position** (N fois, pondéré par les lots), et convention
   bid/ask explicite : la vidéo ne lit que le bid des deux côtés, ce qui ampute la
   sortie vendeuse du spread — choix de portage à déclarer, pas à reproduire par
   accident.
6. **Bras témoin adapté** (`anchored_wf._reference_profile` / `_random_signals`
   ignorent aujourd'hui tout plan de panier) : structure gelée, seul l'instant du
   premier ordre est tiré au hasard. Et un **second témoin** obligatoire : la même
   grille à `multiplier = 1`, pour séparer l'effet de la martingale de celui de la
   moyenne à la baisse.
7. **Métriques** adaptées : le taux de réussite est trompeur par construction (un
   panier ne se ferme que gagnant). Ce qui parle : espérance par panier avec IC
   bootstrap, drawdown d'**équité flottante** (jamais de balance), exposition et
   marge maximales, distribution des profondeurs, probabilité de ruine à N ans par
   bootstrap par blocs, temps sous l'eau.

Points à trancher dans la spec :
- contrat distinct « stratégie à panier » ou assouplissement de `Signal` — le second
  a des effets sur toutes les autres stratégies ;
- ordre de visite intrabar (le moteur suppose le pire cas : stop avant cible) ;
- rétrocompatibilité : les dossiers rendus et les forwards scellés ne doivent pas
  changer de valeur (cf. TCK-014, et l'oracle de non-régression qu'il réclame).

Préférence cc-support : **contrat distinct**, inerte par défaut, avec oracle de
non-régression avant la première ligne de moteur — même préalable que TCK-014,
les deux tickets se servent du même.

Ambiguïtés de la vidéo que le portage devra fixer (relevées dans l'extraction) :
portée du plus-haut/plus-bas de référence (latch global depuis le démarrage, jamais
une fenêtre de barres — l'auteur se contredit trois fois sur le reset), contamination
croisée achat/vente au reset des extrêmes, arrondi de lot en dur à 2 décimales,
absence de magic/filtre symbole. Le pseudocode complet et horodaté est disponible
chez cc-support.

## Réponse

<cc-spec>
