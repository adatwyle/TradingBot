# Source — Patrick Nil, modèle « PBD » (impulsion + range)

**Vidéo** : https://www.youtube.com/watch?v=2ZmIn274eds (IQ Capital, entretien ~42 min)
**Transcript** : fourni par Adrian, intégral dans `SOURCE_transcript.txt`
**Trader** : Patrick Nil, classé cinq années consécutives au Robbins World Cup
Trading Championship. Trade le DAX et le pétrole.

Point notable : contrairement à la plupart des sources, celle-ci a un **palmarès
vérifiable et externe** (classement de compétition). Ça ne valide pas la méthode
telle que nous allons la coder, mais ça écarte l'hypothèse « le trader n'existe
pas ».

---

## 1. Le modèle, littéralement

> « if you have a big P (…) you have a big impulse up and then you have a range
> and that's what I am looking and if this is at good zones then I trade. And
> the B is you have impulse down and the range »

Ce qu'il trade, précisément :
> « No, I trade **after** the impulse. You have the impulse and the range, and
> there I wait to if it goes further up or down (…) or I trade the range. If the
> range is good you can always play ping pong in the range till it goes out »

Deux modes distincts, à tester **séparément** :
- **(A) range fade** — vendre le haut du range, acheter le bas, tant qu'il tient.
- **(B) cassure** — jouer la sortie du range.

Le filtre qui les qualifie :
> « if the impulse and the range is on the same level as the market profile,
> it's even better (…) it's the right level to the value area high »

## 2. Le second ingrédient : profil de volume hebdomadaire

> « I have the market profile volume based from the weekly and there you can see
> on the value area highs and lows — **they are so important** »

Ce qu'il en tire, dans ses mots :
> « you can see where all is in freedom, all are satisfied, and where not »
> — c'est-à-dire : dans la value area, le prix bouge lentement (volume accepté) ;
> en dehors, il accélère (volume rejeté).

> « if we are here between these areas (…) here are all in freedom, there is
> nothing. But if we go down here it goes faster »

Reproductible sans indicateur propriétaire : profil de volume sur fenêtre
hebdomadaire, POC + value area 70 %. C'est un calcul standard. **Réserve
importante** : MT5 ne fournit pas le volume réel (`real_volume = 0` — voir
`core/data/source.py`). Le profil devra être bâti sur le **tick volume**, qui
compte les changements de prix, pas les contrats. Ce n'est pas la même chose,
et cet écart doit figurer dans le verdict.

## 3. Sorties

Cible :
> « if you have impulse like that, normally the profit target is under the
> impulse — most time it goes back to the beginning »

Donc : **retour au point de départ de l'impulsion**. C'est mécanique et testable.

Stop — il refuse explicitement une règle unique :
> « sometimes I do it over the zone or over the top or in the middle or I look
> where the volume was in the last candles. There are different things but you
> must be clear »

À traiter comme un **paramètre à balayer** (au-dessus du range / au-dessus de
l'extrême de l'impulsion / milieu du range), pas comme un choix arbitraire.

Gestion :
> « the best results I have when I don't manage the trade and let it like in the
> beginning » — donc tester d'abord **sans** gestion active.

## 4. Cadre chiffré, explicite

- Timeframe d'exécution : **M15** (« for the trade I take the 15 minutes chart »)
- Durée de détention : **4 heures à 3 jours**
- Fréquence : ~3 à 5 trades par jour
- **Win rate annoncé : 50-60 %**
- **Séries perdantes annoncées : 10 à 20 pertes consécutives**
- Risque par trade : **0,2 % à 1 %** sur son compte propre (2-3 % en compétition)
- Drawdown acceptable : **< 10 % souhaité, 20 % maximum**

Ces chiffres sont un cadeau méthodologique : ils donnent des **critères de
réfutation ex ante**. Un backtest qui rend 75 % de win rate n'a pas reproduit sa
stratégie — il a trouvé autre chose, ou il a une fuite.

## 5. Ce qu'il dit du backtesting lui-même

> « I want to see if it works five years ago because there are so many strategies
> they work for some month and then they are crashed »
> « I want consistency (…) not the result if it's better or not »

Et sur le drawdown, il donne l'arithmétique exacte :
> « if you have a drawdown from 20% you need profit of 25% to be on zero, and if
> you have a drawdown from 50% you need 100% »

C'est cohérent avec `docs/METHODOLOGY.md`. À prendre au mot : la mesure
principale de cette stratégie est la **stabilité inter-fenêtres**, pas le R total.

## 6. Ce qui est hors périmètre

- « you must feel the market a little bit » — il se déclare **totalement
  discrétionnaire**. Le modèle codé sera donc nécessairement plus pauvre que ce
  qu'il fait. À écrire dans le verdict, pas à masquer.
- Footprint / order flow pour affiner l'entrée : données non disponibles.
  Il précise lui-même ne pas s'en servir systématiquement (« not every time
  because I'm often not in front of the screens »), ce qui rend le test sans
  footprint défendable — mais c'est une amputation, pas une équivalence.
- Éviter le marché sur news majeures : même traitement que s05.
