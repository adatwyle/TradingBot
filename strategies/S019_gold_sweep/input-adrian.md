# input-adrian — S019 (or, balayage de liquidité)

> Reformulation par cc-support des intentions d'Adrian. Adrian n'écrit pas ici
> directement ; git porte la traçabilité, ce fichier porte l'état courant.

## La demande

Reproduire dans le bot la méthode d'une scalpeuse XAUUSD suivie sur ses lives
publics, en substituant la personne qui décide. Formulée le 2026-09-06 :

> « repasse à travers les vidéos et cible les moments où elle parle des éléments
> qui te sont inconnus de sa stratégie d'entrée et de sa stratégie de prédiction.
> À force tu vas trouver les informations et pouvoir reconstituer le puzzle.
> Ensuite à toi de voir comment substituer la personne qui décide et réussir à
> reproduire l'entier de sa stratégie dans un bot. »

puis : « lance S019 ».

## Ce qui a été décidé en amont, et qui tient

1. **La v1 reste scellée.** L'étude `studies/gold_forward/` est en cours de
   validation ; on ne touche pas à S011. Tout travail neuf vit dans le worktree
   `v2/gold`. Éditer S011 invaliderait silencieusement le test forward — c'est ce
   risque qui a produit toute l'architecture S018/S019.
2. **Une stratégie par déclencheur.** S018 mesure la cassure plus l'entrée à
   l'équilibre ; S019 mesure le balayage. Les mélanger empêcherait de savoir
   lequel porte.
3. **Promotion PAPER/LIVE = Adrian seul.** Aucun dispositif n'arme un trade réel.

## Ce que S019 code, et pourquoi seulement ça

On code ce qui a été **mesuré**, pas ce qui a été **dit**. Sur 20 entrées réelles
alignées sur nos barres :

- balayage présent dans 60 % des entrées contre 39 % au hasard (p = 0,047) → **codé** ;
- mèche de rejet : p = 0,136, non significatif → **volontairement absent** ;
- un stop métrique de 1,5 × ATR aurait coupé 40 % de ses entrées → **stop
  structurel**, sous l'extrême du balayage.

## Ce qui reste ouvert, et qui attend Adrian

| Sujet | État | Ce qui est demandé |
|---|---|---|
| **TCK-014** — clôtures partielles et stop suiveur | ouvert, chez cc-spec | Arbitrage. Sans ça, S019 mesure son entrée avec une sortie inférieure à la sienne. C'est la limite qui conditionne la lecture de tout résultat. |
| **TCK-018** — spread réel 52 pips contre 25 au catalogue | ouvert | Validation. Bénéfice pour tout le projet, pas seulement pour l'or. |
| **TCK-016** — calendrier économique | ouvert | Ses entrées tombent à T+6 min médian après le choc d'annonce. Sans calendrier, ce filtre reste inaccessible. |
| Historique météo Discord | bloqué | Compte vérifié par téléphone requis — action Adrian. Le scoreur `studies/meteo_doud/score_meteo.py` est prêt à le consommer. |
| Poussée de `v2/gold` | non fait | La CI ne se déclenche que sur `dev`, la poussée est sans risque : `git -C C:/projects/tradingBot-v2 push -u origin v2/gold` |

## Ce qu'il faudra construire nous-mêmes

Ses « zones fatidiques » — les niveaux historiques fixes dont la double cassure
fait basculer son biais directionnel — sont le commutateur acheteur/vendeur qui
manquait au dossier. Elle dit ce qu'ils font, jamais comment elle les trace.
C'est reconstructible : chaque objet de sa géométrie a maintenant une définition
fonctionnelle testable (`docs/sources/doudtrading/SYNTHESE_GEOMETRIE.md`). S019
ne le fait pas — il mesure d'abord le déclencheur seul.
