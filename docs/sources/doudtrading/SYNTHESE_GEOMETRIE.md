# La géométrie Doud — les objets qui manquaient au puzzle

> **Méthode** : recherche **inversée**. Les passes précédentes cherchaient les
> termes que je connaissais déjà ; celle-ci traque le vocabulaire **non
> cartographié** — constructions de nommage (« j'appelle ça… »), collocations
> `zone + X`, et termes repérés mais jamais élucidés.
> **Corpus** : 145 fichiers, 3 244 406 caractères (35 lives + 108 TikTok + 2 podcasts).
> **Date** : 2026-09-06.

**Ce que cette passe change.** Les synthèses précédentes décrivaient sa
*procédure* (biais → zone → balayage → entrée → sortie). Il manquait les
**objets** sur lesquels cette procédure s'applique. Elle les nomme par des
couleurs et des surnoms, et chacun a un rôle fonctionnel distinct. Sans eux, la
procédure flottait ; avec eux, elle devient une géométrie codable.

---

## 1. La zone fatidique — l'objet le plus important, et il manquait entièrement

> *« mes zones fatidiques, vous savez, **c'est les zones que je touche jamais** »* — `EdZNDaz1rkY`
> *« on était venu sur une zone fatidique que j'avais créée, on est venu **breaker la zone**, c'est-à-dire qu'on est venu **la casser deux fois** »* — `EdZNDaz1rkY`
> *« **Si on vient casser mes zones fatidiques**, donc des zones que j'ai créées plus basses, et qu'on passe en tendance baissière, **je vendrai le gold** »* — `_YLBNaigG_w`
> *« quand on fait des ATH, **j'ai pas mes zones fatidiques, j'ai pas de repère** »* — `VgZx8e4k2lE`
> *« Ça, c'est pas des zones fatidiques, **ça c'est des prix qui bougent** »* — `MW1OGBv39dI`

Quatre propriétés, toutes explicites :

1. **Ce sont des niveaux fixes**, pas des moyennes mobiles (« pas des prix qui bougent »).
2. **Elle n'y trade jamais** — c'est une zone d'interdiction, pas d'entrée.
3. **Leur cassure — double — fait basculer son biais directionnel.** C'est le
   commutateur acheteur/vendeur que je cherchais depuis le début du dossier.
4. **Sur territoire vierge (ATH), elles n'existent pas et elle est aveugle.**
   C'est l'aveu le plus utile du corpus : sa méthode est **dépendante de
   l'historique**. Elle le dit sans détour.

**Ce que ça résout.** Le § 1.5 de `SPEC_doud-probabilites-et-angles-morts`
constatait qu'elle refusait d'expliquer ses 65 %. Une partie de la réponse est
ici : le biais n'est pas un calcul continu, c'est un **état binaire piloté par
des niveaux historiques fixes**, qui bascule à la double cassure.

**Codable** : plus-hauts/plus-bas historiques majeurs, non touchés depuis N
périodes, avec règle de bascule à la deuxième clôture au-delà.

---

## 2. Le code couleur — chaque zone a une fonction

| Objet | Occurrences | Ce qu'elle en dit | Fonction |
|---|---:|---|---|
| **zone d'impulsion** | 176 | *« la prise de liquidité, la zone d'impulsion et les zones de retournement »* · *« on va pulser en zone d'impulsion sur les 4500, faut breaker les 4505 en structure pour aller chercher 4530, 4540 »* | où le mouvement **démarre** |
| **zone jaune** | 95 | *« tant qu'il reste **en dessous** de la zone jaune, on a de la liquidité à récupérer »* · *« tant qu'il reste **sur** la zone jaune, votre trade va aller chercher plus haut »* · *« ton **SL** maintenant il va se mettre **sur la zone jaune** »* | **frontière directionnelle ET ancrage du stop suiveur** |
| **zone de retournement** | 46 | *« zone de retournement, **prenez vos gains** »* · *« sécurisez une partie au cas où on est sur une zone de retournement »* | où l'on **sort** |
| **zone blanche** | 23 | *« on est sur **un équilibre** qui est sur la zone blanche des 44937 »* · *« essayer de choper la zone blanche, **c'est les points d'entrée** »* | **l'équilibre = la zone d'entrée** |
| **tête de mort** | 12 | *« je l'ai mise pour qu'on la voie bien, **cette prise de liquidité** »* · *« si on cassait la zone jaune, on venait **récupérer la liquidité** »* · *« on va aller **la récupérer** »* | marqueur d'une **poche de liquidité majeure**, cible du balayage |

**Le point décisif** : la zone jaune est à la fois la frontière du biais **et
l'endroit où va le stop suiveur**. C'est exactement le « stop structurel et non
évident » qu'elle théorise ailleurs (`tiktok/7593786219301997846`) — et c'est ce
que la mesure du 2026-09-06 imposait, puisque notre stop métrique à 1,5 ATR
coupait 40 % de ses entrées.

---

## 3. Le sabre laser — le balayage, nommé et *attendu*

> *« les sabres laser, **c'est fait pour sortir tout le monde à SL** »* — `EdZNDaz1rkY`
> *« l'objectif c'est **qu'on vienne dessus**, qu'on **le traverse tel un sabre laser**, pour après **remonter** »* — `T3GzXZmGhUE`
> *« **j'aimerais vraiment prendre un beau sabre laser** »* — `T3GzXZmGhUE`
> *« quand Jérôme Powell parle, on a **un sabre laser** »* — `VPLmoxOmhDY`
> *« un petit sabre laser là et hop, on va chercher la lune »* — `VgZx8e4k2lE`

Le balayage de liquidité mesuré à **60 % contre 39 % au hasard**
(`studies/meteo_doud/VERDICT_croisement-entrees.md`) n'est donc pas un artefact
statistique : **c'est le setup qu'elle attend explicitement**, avec un nom, et
qu'elle associe aux prises de parole de la Fed. La mesure et le discours se
rejoignent, chacun étant arrivé par un chemin indépendant.

---

## 4. Les autres pièces

**Prix psychologique** — double rôle, aimant *et* piège :
> *« le marché va **réagir** sur des prix psychologiques »* mais *« attention de
> ne pas aller chercher un prix psychologique tout de suite, parce que **c'est là
> où le marché va vous piéger** »* · *« la prise de liquidité qui s'est arrêtée
> au 4029, prix psychologique »*

Les niveaux ronds concentrent les ordres : ils attirent le prix, donc ils sont
des cibles — et pour la même raison ils sont l'endroit où le balayage se produit.

**Mid-asian** — un niveau de référence de session :
> *« on arrive sur un support, donc on attend bien les 2665 […] **midasian** pour
> ceux qui le savent »* — `du7drhC90-o`

Le milieu de la session asiatique sert de support/résistance à la session US.
Cohérent avec les « doudizones » construites session par session
(`SYNTHESE_TIKTOK.md` § 6).

**Salade de doji** — un **état**, pas un signal : *« on n'a pas de décision
claire actuellement »*. Amas de bougies d'indécision = compression, ce qui
rejoint sa définition de l'équilibre (`SYNTHESE_TIKTOK.md` § 3).

---

## 5. Le puzzle, reconstitué

La séquence complète, chaque étage porté par un objet nommé :

```
  ZONES FATIDIQUES          niveaux historiques fixes, jamais tradés
   (biais)                  double cassure  ->  bascule acheteur / vendeur
        |
        v
  TÊTES DE MORT             les poches de liquidité que le prix ira chercher
   (cible du balayage)
        |
        v
  SABRE LASER               le balayage : le prix traverse, sort tout le monde
   (déclencheur)            à SL, puis réintègre
        |
        v
  ZONE BLANCHE              l'équilibre — c'est là qu'elle entre
   (entrée)
        |
        v
  ZONE JAUNE                frontière directionnelle + ancrage du stop suiveur
   (gestion)
        |
        v
  ZONE DE RETOURNEMENT      prise de gains, partielles
  + PRIX PSYCHOLOGIQUES     (cibles rondes)
```

Rapproché des mesures déjà faites, tout se recoupe : le balayage est confirmé à
60 % contre 39 % ; l'entrée se situe à **T+6 min médian après le choc**
d'annonce, c'est-à-dire sur la réintégration post-sabre-laser ; et le stop doit
être structurel — la zone jaune — parce qu'un stop métrique est balayé par
construction.

---

## 6. Ce qui reste hors de portée

- **La construction exacte des zones.** Elle dit d'où elles viennent (trois ans
  d'observation par session) et ce qu'elles font, jamais comment elle les trace.
  C'est à **reconstruire par nos propres moyens** — et c'est faisable, puisque
  chaque objet a maintenant une définition fonctionnelle testable.
- **Le nombre de zones simultanées**, leur durée de vie, leur mise à jour.
- **Le filtre de refus** (angle mort C6) : rien de neuf ici.
- Les surnoms restés opaques — « la bouteille » (motif H2), « la flûte »,
  « bougie sautoir », « effet boomerang » — cités sans jamais être définis.
