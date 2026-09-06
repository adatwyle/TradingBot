# Ses entrées face aux annonces économiques — vérification

**Date** : 2026-09-06 · **Données** : XAUUSD M1 · **Entrées** : les 20 alignées
**Méthode** : sans calendrier externe — les titres de ses lives nomment
l'événement, et le choc de volatilité dans nos propres barres date la publication.

---

## 1. Les événements sont réels, et notre référence horaire est bonne

Référence fixée à **14h30 heure serveur** = 8h30 ET, l'heure standard des chiffres
US. Contrôle : amplitude de la bougie M1 de 14:30 rapportée à la médiane des
bougies M1 de la matinée (10h-13h) du même jour.

| Jour | Événement annoncé | Amplitude 14:30 | × la base |
|---|---|---|---|
| 2026-09-04 | **NFP** | **8 704 pips** | **× 64** |
| 2025-04-10 | jobless claims | 904 | × 6,2 |
| 2025-08-28 | générique | 318 | × 5,1 |
| 2026-07-30 | jobless claims | 970 | × 4,6 |
| 2026-06-11 | jobless claims | 905 | × 4,5 |
| 2026-07-23 | jobless claims | 538 | × 3,4 |

Le NFP du 4 septembre 2026 déplace l'or de **87 $ en une seule minute**. La
référence 14h30 est confirmée par les données, pas supposée.

**Mais 8 entrées sur 17 ont lieu des jours où 14:30 n'a produit aucun choc**
(ratio < 3), malgré des titres de live évoquant les jobless claims. Le cas le
plus net est le **4 juillet 2025** — férié américain, ratio 0,6 : elle tenait un
live « scalping XAUUSD » un jour sans publication. Une part substantielle de son
activité n'est donc pas événementielle.

---

## 2. Ce qu'elle dit, et ce que les données montrent

**Ce qu'elle dit**, répété dans au moins cinq lives :

> *« On attend **28** »* · *« j'attends 28, tant qu'il n'est pas 28 je ne me
> positionne pas »* · *« le point d'entrée ne se fait pas avant 27 »* ·
> *« tu peux trader 5 minutes avant et 5 minutes après, mais **tu ne peux pas
> trader pendant** »*

**Ce que montrent les 9 entrées des jours à publication avérée** :

| Fenêtre | Compte |
|---|---|
| dans les 3 minutes **avant** 14:30 — *sa règle* | **0/9** |
| avant 14:30 (toutes) | 1/9 (à −4 min) |
| **pendant** le choc (14:30 → 14:35) | 3/9 |
| après 14:35 | 5/9 |
| **écart médian** | **+6 minutes après la publication** |

Elle n'entre pas deux minutes avant. Elle entre **après**, médiane +6 min, et
trois fois sur neuf pendant les cinq minutes du choc — la fenêtre qu'elle déclare
justement interdite.

### La limite qu'il faut poser avant de conclure

Les sous-titres disent « **je suis rentrée** au 4492 » — au passé. L'horodatage
capture donc le moment où elle **annonce**, pas nécessairement celui où elle
**exécute**.

Ce décalage est cependant **borné par la mesure elle-même** : dans 15 cas sur 20,
le prix qu'elle cite tombe **dans la bougie M5 de l'instant où elle parle**. Si
l'exécution précédait l'annonce de plus de quelques minutes, le prix cité ne
collerait plus au prix courant. Le décalage annonce/exécution est donc de l'ordre
de quelques minutes — pas des dizaines.

**Conclusion prudente** : l'écart entre « on attend 28 » et une entrée médiane à
+6 min est trop grand pour être expliqué par le seul délai de parole. Il reste
une lecture possible que les données ne tranchent pas : elle prépare son ordre à
14:28 et n'est servie qu'après le choc.

---

## 3. Ce que ça apporte à S019 — les deux mesures se recoupent

Le test précédent (`VERDICT_croisement-entrees.md`) montrait que **60 % de ses
entrées suivent un balayage de liquidité** (contre 39 % au hasard, p = 0,047).
Celui-ci montre qu'elle entre **après** le choc d'annonce, pas avant.

**Les deux disent la même chose.** Le choc de publication *est* le balayage : le
mouvement violent va chercher les stops de part et d'autre, puis le prix
réintègre. Elle n'essaie pas de prendre le choc — elle prend **la réintégration
qui le suit**.

Conséquences directes pour la construction :

1. **La fenêtre d'entrée n'est pas T−2 min, c'est T+5 à T+20 min.** C'est
   mesurable, c'est codable, et c'est l'inverse de ce que le podcast laissait
   croire — la traduction D9 (« entrée 2 min avant ») est à écarter.
2. **Les jours d'annonce, un stop métrique est balayé par construction** : une
   bougie M1 à 64× la volatilité normale traverse n'importe quelle distance
   ATR. Cela renforce la conclusion de la mesure précédente — le stop doit être
   structurel, et la sortie gérée, pas fixe.
3. **Le calendrier économique reste nécessaire** (`TCK-016`) — mais pour une
   raison inversée : non pas pour entrer avant l'annonce, mais pour **savoir
   qu'il faut attendre le retracement**, et pour distinguer les jours à choc des
   jours ordinaires, qui représentent la moitié de son activité.

---

## 4. Ce que cette mesure ne dit pas

- **9 observations** sur les jours à publication avérée. C'est peu, et l'écart
  médian de +6 min repose dessus.
- **Biais de sélection** inchangé : ce sont les entrées qu'elle annonce à voix
  haute et dont le prix survit à la reconnaissance vocale.
- **Rien sur la performance** : on mesure *quand* elle entre, pas ce que ça
  rapporte.
- **Le décalage annonce/exécution** est borné mais non nul (§ 2).
