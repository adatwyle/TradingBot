# Croisement des entrées Doud contre nos barres — résultat

**Date** : 2026-09-06 · **Données** : XAUUSD M1, 702 545 barres, 2024-09 → 2026-09
**Script** : `croisement_entrees.py` (paramètres fixés avant mesure)
**Entrées** : extraites de ses lives publics, horodatées, validées par le prix

---

## 1. La validation préalable — ses prix sont réels

32 entrées candidates extraites des 35 lives. Placement sur la ligne du temps par
`release_timestamp` du stream + offset du sous-titre + décalage serveur (GMT+2).

Le prix qu'elle annonce sert de **somme de contrôle** de l'horodatage :

| | |
|---|---|
| entrées placées | 32 |
| **alignées à moins de 0,3 %** du prix réel | **20** |
| dont **tombant dans la bougie M5** de l'instant cité | **15** |
| meilleures correspondances | 0,01 % (`g0QZlUtQLvM`, `QbkYJMzeodI`) |

Les 12 échecs s'expliquent par la reconnaissance vocale (prix tronqués : « 390 »,
« 4000 ») — pas par un défaut d'alignement.

Deux confirmations tombent gratuitement : les heures d'entrée se groupent sur
**14h07-15h44 heure serveur** plus deux en **session asiatique (00:18, 00:22)**,
exactement les fenêtres qu'elle déclare. Et ses prix ne sont pas inventés.

---

## 2. Le test — ses entrées tombent-elles sur un balayage de liquidité ?

**Définition, fixée avant mesure** : balayage = une barre M1 qui perce le plus-bas
des 60 barres précédentes **et referme au-dessus** de ce plus-bas, dans les
30 barres qui précèdent son entrée. Rejet net = mèche basse ≥ 50 % de l'amplitude.

**Témoin** : 200 instants tirés au hasard dans les **mêmes heures de session**,
sur les autres jours, graine figée.

| | ses entrées | témoin | p unilatéral |
|---|---|---|---|
| **balayage de liquidité** | **12/20 = 60 %** | 78/200 = 39 % | **0,047 — significatif à 5 %** |
| rejet net (mèche ≥ 50 %) | 6/20 = 30 % | 36/200 = 18 % | 0,136 — non significatif |

**Lecture.** Le balayage est confirmé, de justesse et sur 20 observations. Le
raffinement « mèche de rejet » ne l'est pas : il ne distingue pas ses entrées du
hasard, et ne doit donc **pas** entrer dans S019 comme condition.

C'est un résultat exploitable : **son déclencheur est détectable mécaniquement**,
et il l'est par le balayage seul.

---

## 3. Le résultat qui décide de l'architecture

Excursions dans les 60 minutes qui suivent chaque entrée :

| | médiane | moyenne | max |
|---|---|---|---|
| **MAE** (contre elle) | **729 pips** | 1 020 | 3 498 |
| **MFE** (en sa faveur) | **1 315 pips** | 1 297 | 4 243 |

**Rapport MFE/MAE médian : 1,80.** Ses entrées ont donc un profil favorable — le
marché lui donne près du double de ce qu'il lui prend.

Mais :

> **Notre stop = 1,5 × ATR(H1) médiane = 858 pips.**
> **8 entrées sur 20 (40 %) l'auraient franchi dans l'heure** — alors que
> **12 sur 20 (60 %) atteignent +858 pips en sa faveur.**

Autrement dit : **notre stop fixe couperait 40 % de ses trades avant qu'ils ne
travaillent.** Un système qui copierait son entrée en gardant notre géométrie de
sortie détruirait précisément ce qui fait sa performance.

Ce chiffre explique, sans avoir à la croire sur parole, pourquoi son absence de
stop dur n'est pas une coquetterie mais une **nécessité structurelle** de sa
méthode — et pourquoi elle compense par un stop suiveur qui ne se met en place
qu'après coup.

---

## 4. Conséquences pour S019

1. **L'entrée par balayage a un signal.** Elle passe le témoin, de justesse.
   S019 a un objet. Sans cette mesure, on l'aurait construite à l'aveugle.
2. **Le filtre « mèche de rejet » est écarté.** Il n'ajoute rien de démontrable.
3. **La géométrie de sortie n'est pas un détail d'implémentation.** Avec un stop
   à 1,5 ATR, 40 % des entrées sont tuées avant terme. `TCK-014` (sorties
   partielles + suiveur) conditionne la mesure elle-même, pas seulement son
   raffinement.
4. **Le stop de S019 doit être structurel, pas métrique** — cohérent avec ce
   qu'elle dit (« un bon stop est logique par rapport à la structure ; si ton stop
   est évident, il est fragile », `tiktok/7593786219301997846`) et avec ce que la
   mesure montre.

---

## 5. Ce que ce résultat ne dit pas

- **20 observations.** p = 0,047 est un seuil franchi de justesse ; sur un
  échantillon aussi mince, il ne faut pas plus de deux entrées mal alignées pour
  le faire basculer. **Ce résultat oriente la construction de S019 ; il ne la
  justifie pas à lui seul.**
- **Biais de sélection.** Ce sont les entrées qu'elle **annonce à voix haute**
  dans un live public. Rien ne dit qu'elles représentent l'ensemble de ses trades.
- **Ni performance, ni rentabilité.** MFE et MAE décrivent ce que le marché
  offre, pas ce qu'elle en tire — sa gestion de sortie reste hors de portée de
  notre moteur.
- **Aucun coût.** Ces chiffres sont bruts : ni spread (≈ 52 pips réels, `TCK-018`),
  ni slippage.
