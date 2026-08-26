# Source — « Fable 5 a gagné 33 029 $ en 24 h », couche de risque et relative value

**Vidéo** : https://www.youtube.com/watch?v=wQaBpb87goc
**Captures** : `/tmp/s08_eventpair/` (table complète des positions à 5:45)
**Nature** : publicité. La vidéo se termine par « send me a message, the links are
down below » pour une offre de gestion — « the sensible version… that trades
inside your own brokerage account ». L'expérience est l'accroche.

---

## 1. Ce que j'ai vérifié plutôt que cru

Il affiche à 5:45 la table des huit positions du 1er juillet 2026. Recalcul ligne
à ligne :

| | | entrée → sortie | qty | P&L recalculé |
|---|---|---|---|---|
| NBIS | short | 240,27 → 229,18 | 940 | +10 425 |
| TEM | long | 57,55 → 61,60 | 2 500 | +10 125 |
| CRWV | short | 88,87 → 85,69 | 2 500 | +7 950 |
| META | long | 607,91 → 612,91 | 600 | +3 000 |
| IREN | short | 44,05 → 43,32 | 2 500 | +1 825 |
| APLD | short | 35,90 → 35,52 | 2 500 | +950 |
| GOOGL | long | 358,37 → 361,21 | 300 | +852 |
| NVDA | long | 196,20 → 197,58 | 500 | +690 |

**Total recalculé 35 817 $** contre 35 770 $ affichés — écart de 47 $, compatible
avec l'arrondi des prix affichés. **Notionnel à l'entrée 1 362 136 $**, cohérent
avec le « about $1.3 million » annoncé. Net après 2 741 $ de frais : 33 076 $
contre 33 029 $ annoncés.

**C'est arithmétiquement cohérent.** Ce n'est pas bricolé. Ça ne prouve pas que
les trades ont eu lieu, mais ça écarte la fabrication négligente.

### Deux réserves factuelles

**Il annonce des horodatages qui ne sont pas là.** À 4:40 : « every entry, exit,
and time stamp », et à 7:00 : « every time stamp is on the screen (…) you can
pull up the July 1st chart and check every price yourself ». La table ne porte
**aucune heure**. Sans horodatage on ne peut vérifier que l'appartenance des prix
au range du jour — un contrôle bien plus faible que celui qu'il propose.

**Il ne donne jamais la taille du compte.** 33 029 $ n'est donc pas un rendement,
c'est un montant. Avec 1,36 M$ de notionnel à effet de levier, le même gain
représente +3 % ou +33 % selon le capital, et il ne le dit pas.

### Le vrai problème statistique

**8 positions, 8 gagnantes, aucune perdante**, alors qu'un stop est attaché
automatiquement à chaque entrée. Il le reconnaît lui-même — « eight trades
without a single loser is not normal, I know that » — ce qui est à son crédit.

Mais la lecture correcte n'est pas « ce jour-là il a eu de la chance ». C'est un
**biais de publication** : on ne filme que la journée qui valait d'être filmée.
Le processus de sélection de l'échantillon est corrélé au résultat. La journée
n'est donc pas informative sur l'espérance, quel que soit son degré de réalité.

Il ajoute « up about 70% since January » sur son système principal — invérifiable,
sans courbe, sans drawdown, sans effectif.

---

## 2. La stratégie : relative value thématique sur événement

Le mécanisme, lui, est réel et connu. Un titre de presse — Meta loue sa capacité
de calcul excédentaire — a des implications **opposées** selon la position dans
la chaîne de valeur :

- bénéficiaire : Meta, dont les dépenses d'infrastructure deviennent une source
  de revenus (long)
- victimes : les loueurs de calcul purs — Nebius, CoreWeave, IREN, Applied
  Digital — qui voient le plus gros acteur du monde entrer sur leur marché (short)

Au lieu de choisir un camp, il joue **les deux côtés de la même histoire**. Le
panier short est traité comme un thème, pas comme des titres : sa propre note dit
que IREN et APLD « n'étaient pas de bons shorts isolément, mais le groupe entier
cotait comme un thème, et le thème baissait ».

C'est une famille légitime : *event-driven relative value*. Elle a l'avantage
d'être partiellement neutre au marché — c'est l'écart entre bénéficiaire et
victimes qui porte le résultat, pas la direction générale.

### Pourquoi nous ne pouvons pas la tester

| Besoin | Chez nous |
|---|---|
| Univers d'actions | **absent** — 22 instruments, tous FX / indices / matières / BTC |
| Flux de news horodaté à la barre | **absent** |
| Capacité de short titre par titre | **absente** |

Ce n'est pas une difficulté de mise en œuvre, c'est un mur. Reproduire cette
stratégie demanderait un autre courtier et un fournisseur de news *point-in-time*
— et sur ce dernier point, toute recherche web rétrospective renvoie des articles
écrits après coup, donc une fuite maximale.

**Conclusion : NON REPRODUCTIBLE dans l'environnement actuel.** À rouvrir si on
ajoute un courtier actions et une archive de news horodatée.

---

## 3. Ce qui est directement réutilisable : la couche de risque

C'est la partie la plus solide de la vidéo, et elle comble notre trou le plus
béant — `core/risk/` est vide à ce jour.

> « Every order it places has to pass through a risk layer **that the model
> literally cannot touch**. There's a hard limit on how big any single position
> can get, and another limit on the whole book combined. A stop-loss gets
> attached to every entry automatically, no exceptions, and there's a daily loss
> number where the entire session just shuts off dead, no matter what the model
> thinks it knows. »

Quatre bornes, et surtout **un principe** : les bornes sont hors d'atteinte du
décideur. C'est exactement notre R2 — la stratégie exprime une intention, la
couche risque décide de l'exposition — et c'est nettement supérieur à la version
Nate Herk, où les garde-fous sont des phrases dans un prompt que le modèle peut
négliger un jour de forte conviction.

| Borne | Nature |
|---|---|
| plafond par position | proportion du capital |
| plafond du livre entier | somme des expositions |
| stop attaché automatiquement | à l'entrée, sans exception |
| perte quotidienne | coupe-circuit, arrêt total de la session |

Sa formule vaut d'être gardée : *« the AI gets to pick the trades, but how much
damage it was even allowed to do was locked in before it started »*.

### Le journal obligatoire

> « After every single trade, it has to write a short journal entry explaining
> why it got in and why it got out. »

Ce n'est pas du confort. C'est ce qui rend l'attribution possible après coup :
sans état de décision enregistré, on ne peut que lire le récit de l'agent, jamais
mesurer quelle famille de décisions a produit quoi. Même besoin identifié pour
`s92`.

### La boucle

scan du marché → **cotation fraîche juste avant d'engager** (« a price from 10
seconds ago is already old ») → ordre via la couche de risque → journal. Toutes
les quelques minutes.

---

## 4. Ce qu'on en fait

| Élément | Décision |
|---|---|
| Couche de risque à 4 bornes, hors d'atteinte du modèle | **implémentée** dans `core/risk/` |
| Journal obligatoire par décision | **repris** pour `s92` |
| Cotation fraîche avant engagement | **repris** |
| Relative value thématique sur événement | **non reproductible** — pas d'actions, pas de news horodatées |
| « 33 029 $ en 24 h » comme preuve | **rejeté** — biais de publication, taille de compte non communiquée, horodatages annoncés mais absents |
| « +70 % depuis janvier » | **rejeté** — invérifiable |
