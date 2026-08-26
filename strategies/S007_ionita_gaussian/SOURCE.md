# Source — Michael Ionita (« Michael Automates »), canal gaussien

**Chaîne** : https://www.youtube.com/@michaelionita — 287 000 abonnés
**Vidéo pointée par Adrian** : https://www.youtube.com/watch?v=fdGCGXcDByk
**Autres sources récupérées** : `sources/*.txt` (sous-titres dédupliqués)
**Captures du prompt** : `frames_prompt/*.png` (recadrées, lisibles)

---

## 0. Avertissement de lecture — ce que la vidéo pointée est réellement

La vidéo `fdGCGXcDByk` est **une publicité pour un produit** (Signum + une
masterclass payante). Elle vend la *plomberie* : comment brancher Claude sur
Signum sur Hyperliquid. Le contenu stratégique y est réduit à des chiffres de
vitrine invérifiables :

> « 7 492 % de profit, 35,6 % de drawdown max depuis le 1er janvier 2018, sur
> 2 689 trades » — et, pour la masterclass : 12 226 %, 8 417 %, etc.

**Ces chiffres ne sont pas notre cible.** Ce sont des courbes d'équité optimisées
sur l'historique complet, affichées sans walk-forward. C'est exactement l'objet
que notre propre diagnostic d'illusion in-sample est fait pour désamorcer : sur
`s91`, 75 % à 229 % du rendement apparent disparaissait une fois l'optimisation
retirée.

**Ce qui est réellement testable se trouve ailleurs sur la chaîne.** J'ai
récupéré six vidéos, dont trois portent de la substance :

| Fichier | Vidéo | Pourquoi c'est utile |
|---|---|---|
| `01_gaussian_long_short.txt` | Gaussian Channel long & short | les règles d'entrée/sortie |
| `02_gaussian_automate.txt` | Automatiser le canal gaussien | la version d'origine, long seul |
| **`03_gaussian_10months_forward.txt`** | **« Decoding 10 Months of Gaussian Channel Trades »** | **un vrai forward-test publié** |
| `04_repainting.txt` | détecter le repainting | c'est notre problème R1, vu de l'autre côté |
| `05_what_makes_good_strategy.txt` | DD, profit factor, win rate | ses critères d'évaluation |
| `06_low_timeframes_suck.txt` | pourquoi M5/M15/H1 perdent | recoupe notre péage de spread mesuré |

### Le chiffre qui compte vraiment

Dans `03_gaussian_10months_forward.txt`, il revient **dix mois après** la
publication de la stratégie et mesure ce qu'elle a réellement fait depuis :

> « 51.74% profit » — avec, plus loin : « the gaussian channel strategy made 51%
> profit with 8.5% max drawdown »

**C'est une donnée hors échantillon, publiée par l'auteur, contre lui-même s'il
le fallait.** C'est infiniment plus informatif que le 7 492 % de la publicité, et
c'est ce contre quoi notre reproduction doit être comparée. Note d'ailleurs
qu'il compare ensuite avec une variante à lui (« fast re-entry », 67 % / 6,5 %) —
donc il optimise après coup, ce qui rouvre la question du sur-ajustement sur la
variante, mais pas sur le chiffre de base.

---

## 1. Le canal gaussien — ce que c'est vraiment

Le « Gaussian Channel » est un indicateur public, pas une invention de l'auteur :
filtre gaussien de John Ehlers à N pôles, appliqué au prix, entouré de bandes
construites sur le true range filtré de la même façon.

- `gc.filter` — la ligne centrale, sortie du filtre
- `gc.upper` / `gc.lower` — bandes = filtre ± multiplicateur × true range filtré
- `gc.trend` — vert si le filtre monte, rouge s'il descend

**Point d'attention majeur, propre à notre projet.** Un filtre d'Ehlers est un
IIR récursif. Implémenté causalement (type `lfilter`), il est légitime.
Implémenté en aller-retour (type `filtfilt`), il **regarde le futur** — et c'est
précisément le bug que notre gardien R1 a fini par attraper sur ce projet, après
l'avoir manqué une première fois. L'auteur consacre lui-même une vidéo au
repainting (`04_repainting.txt`) : le sujet est connu de lui. **Notre
implémentation doit être causale et le prouver, pas l'affirmer.**

---

## 2. Le prompt = la stratégie, transcrit depuis les captures

Transcription des captures `frames_prompt/t12m04s.png` et `t12m12s.png`
(instructions de la routine, référence interne `TR-GC-Crypto-LS-2`) :

```
1) Récupérer les positions du bot, convertir en USD pour obtenir la NAV totale.
   Si le compte n'est pas "perpetual", arrêter : les shorts sont impossibles.

2) Récupérer le Trend Radar quotidien crypto avec includeindicators=true.
   Chaque actif porte indicators.data[] : les dernières bougies CLÔTURÉES avec
   ohlc.h, ohlc.c, et un bloc gc : gc.trend ("Green"/"Red"/"Grey"),
   gc.upper (bande haute), gc.filter (ligne centrale). Plus breakoutDate.
   Le radar ne renvoie que des non-stablecoins.

3) RÉGIME BTC (nécessaire pour les shorts en étape 7) : trouver Bitcoin dans le
   radar, regarder sa dernière bougie CLÔTURÉE. BTC est en DOWNTREND si son
   CLOSE est SOUS son gc.filter. Sinon non. Garder ce booléen.

4) SORTIES LONGUES : pour chaque position LONGUE, sortir à 100 % quand le CLOSE
   de la dernière bougie clôturée est SOUS la bande haute (gc.upper), ou quand
   l'actif n'est plus dans le Trend Radar.

5) SORTIES COURTES : sortir à 100 % si l'une de ces conditions est vraie :
   - STOP : le CLOSE de la dernière bougie clôturée est AU-DESSUS de gc.filter
   - TAKE PROFIT : prix d'entrée moyen dérivé du collatéral ; sortir quand le
     close est à 0,65 fois ce prix ou moins (short ~35 % en notre faveur)
   - l'actif n'est plus dans le Trend Radar

6) ENTRÉES LONGUES : parcourir les actifs du Trend Radar triés par rang de
   marché croissant, prendre les 50 premiers. ENTRER LONG quand le CLOSE de
   l'actif a croisé AU-DESSUS de la bande haute gc.upper sur la dernière bougie
   CLÔTURÉE (close au-dessus de la bande ET close de la bougie précédente au
   niveau ou en dessous).
   Ne jamais réentrer sur un actif déjà sorti dans la même exécution.
   Ignorer un actif déjà détenu (une position par pièce).
   TAILLE selon la fraîcheur de la cassure :
     - breakoutDate dans les 25 derniers jours calendaires -> 8 % de la NAV
     - cassure plus ancienne, ou aucune                    -> 2 % de la NAV
   Une cassure n'est PAS requise pour entrer — elle ne fixe que la taille.
   Levier 1x. Si la donnée manque pour évaluer le croisement, ignorer l'actif.

7) ENTRÉES COURTES : parcourir le radar (50 premiers), pour les actifs non
   détenus :
   a) HEDGE short : si gc.trend est "Red" ET que le CLOSE a croisé À LA BAISSE
      gc.filter sur la dernière bougie clôturée -> SHORT de 3 % de la NAV
   b) sinon BEAR short : si BTC est en DOWNTREND (étape 3) ET gc.trend est "Red"
      ET le HIGH de la dernière bougie clôturée a atteint le filtre
      (ohlc.h >= 0,98 × gc.filter) ET son CLOSE est SOUS le filtre
      (rebond rejeté) -> SHORT de 5 % de la NAV
   Ne jamais reshorter un actif déjà sorti dans la même exécution. Levier 1x.
   Shorter est plus risqué et coûte du financement — en cas de doute, s'abstenir.

8) Revérifier les positions et corriger si le résultat ne correspond pas.
```

Contrainte opérationnelle citée dans la vidéo : ordre minimum > 10 $, donc
**200 USDC minimum** pour que le sizing à 5 % passe.

---

## 3. Ce qui est reproductible et ce qui ne l'est pas

| Composant | Reproductible ? | Commentaire |
|---|---|---|
| Canal gaussien (filtre + bandes + trend) | **Oui** | indicateur public, à implémenter causalement |
| Entrée longue = croisement au-dessus de `gc.upper` | **Oui** | purement prix |
| Sortie longue = close sous `gc.upper` | **Oui** | purement prix |
| Short hedge / bear + régime BTC | **Oui** | purement prix |
| Take profit short à −35 % | **Oui** | purement prix |
| Sizing 8 % / 2 % selon fraîcheur de cassure | **Partiellement** | `breakoutDate` vient du radar propriétaire ; dérivable d'une définition de cassure explicite, à déclarer |
| **Univers = « Trend Radar », 50 premiers par rang de marché** | **Non tel quel** | c'est le produit propriétaire de Signum. Substitution obligatoire. |
| « drifted out of the Trend Radar » comme condition de sortie | **Non tel quel** | même raison |

**La substitution de l'univers est le point dur, et il est structurel.** Le
Trend Radar fait deux choses : il sélectionne (quelles pièces) et il classe (rang
de marché). Une partie de la performance annoncée peut venir de cette sélection,
pas du canal gaussien. Il faudra donc **isoler les deux** : le canal gaussien
sur un univers fixe et déclaré d'un côté, et l'effet de sélection de l'autre.
Sans cette séparation, un bon résultat serait inattribuable.

---

## 4. Nature de la stratégie — attention au contrat

C'est une stratégie **de portefeuille multi-actifs à poids** : N positions
simultanées, dimensionnées en pourcentage de NAV, sans stop au sens de notre
contrat épisodique. Les sorties sont des conditions d'indicateur, pas des stops
de prix.

Elle relève donc probablement du **contrat d'allocation**
(`core/contracts/allocation.py`, `core/backtest/allocation_engine.py`), pas du
contrat épisodique `Signal(entry, stop, target)`. C'est exactement le cas de
figure qui avait produit « 1 trade sur 5 ans » quand on a voulu forcer une
stratégie d'allocation dans le moule épisodique.

À noter : le harnais d'allocation rend **systématiquement** le buy & hold de
chaque constituant. Or l'auteur compare lui-même au S&P 500 et affirme battre le
buy & hold. Notre harnais répond nativement à cette question.

---

## 5. Ce qu'il dit du backtesting — à recouper avec notre méthodologie

`05_what_makes_good_strategy.txt` et `04_repainting.txt` donnent ses critères.
`06_low_timeframes_suck.txt` défend que M5/M15/H1 perdent de l'argent — ce qui
recoupe notre propre mesure du péage de spread (H1 = 2,14 points de win rate,
D1 = 0,46). Sa stratégie tourne en **daily**, cohérent avec son propre argument.

Ces trois vidéos sont à lire : elles disent contre quoi il pense se protéger, ce
qui indique où chercher ce qu'il a manqué.
