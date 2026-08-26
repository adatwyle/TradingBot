# Source — Tim Flossbach, « liquidation sweep »

**Vidéo** : https://www.youtube.com/watch?v=BewBId1gbqQ (IQ Capital, entretien ~64 min)
**Transcript** : fourni par Adrian, intégral dans `SOURCE_transcript.txt`
**Trader** : Tim Flossbach, 26 ans, allemand/Dubaï, trade en direct devant audience.

---

## 1. Ce qu'il dit faire — extraits littéraux

Sur la sélectivité :
> « I skip more than 90% of the trades I see in the chart and just focusing like
> on the very good conditions »

Sur le cœur de la méthode :
> « 80% liquidation sweep to liquidation sweep pullback to support »

Sur l'erreur qu'il a corrigée :
> « the biggest problem I did in my past years was to enter way too fast. The
> liquidation hunt is happening. I go into a trade but after time I learned ah
> maybe it's better to wait the one or other minute and I'm waiting for the
> reversal structures and when I see yes the reversal is fine then I'm entering »

Sur la détection d'une zone chargée :
> « if you see that in one specific zone there's not one liquidity (…) but there
> is like a lot a lot a lot of combined liquidity then it's definitely a very
> big alert that the liquidation sweep can be happening. The market always is
> going very slow to these zones (…) but then with one candle out of nowhere »

Sur la sortie :
> « for my stop loss I made it directly under the situation where the first
> liquidation grabbed » ; « I'm taking a look from the last top where are the
> liquidations in this zone (…) this is why I figured out to make my take profit »

Sur le R:R :
> « I would never ever [go] in a risk-to-reward ratio below one (…) 95% of my
> trades are minimum 2:1 »

Sur les filtres de rejet :
> « if the liquidity is like shaking too much, high candles up, high candles
> down, then I will skip it all the time »
> « news which are more than liquidation (…) I will always always skip »
> « always respect the higher time frame. If the higher time frame tells you
> something else than the [15] minute time frame there's no point where you
> should go with the [15] minute time frame »

Structure de tendance, méthode déclarée triviale :
> « I'm just taking a look. It's a lower high structure. So we are obviously in
> a downtrend » — plus EMA 200 (« below the 200 day average, obviously downtrend »),
> EMA 50, EMA 30 optionnelle.

Sur la direction autorisée :
> « I don't think that you only have to focus on short trades (…) you should
> always be open for both sides »

Timeframes cités : analyse top-down weekly → daily → **H4 (« my most favorite
time frame to enter big positions »)** → M15 pour l'exécution.

---

## 2. Le problème central à résoudre pour tester 1:1

Sa détection de liquidité repose sur **deux indicateurs propriétaires**
(« X-Ray », « X-Ray Pro ») qui affichent les volumes de liquidation agrégés des
carnets d'ordres des grandes bourses crypto. Ils ne sont **pas disponibles** :

> « It's like a let's say top secret indicator. You can't just find it like out
> of my platform. »

**Il dit lui-même qu'ils ne sont pas nécessaires** :
> « I can also be profitable without this indicator but it makes my life so much
> easier (…) I don't think that you need at least one indicator to be a
> profitable trader »

Et il décrit ce que l'indicateur révèle en des termes qui, eux, sont
reproductibles à partir du prix seul :

> « this is not random. This is of course because the market shows us also
> without indicator (…) you will see the top of the last structure here (…) and
> just randomly the liquidation is directly in these zones »

C'est le point d'appui du test : les zones de liquidation qu'il montre coïncident
avec des **extrêmes de structure** (sommets/creux précédents, bornes de range,
égalités de hauts/bas). Le proxy n'est donc pas une invention de notre part,
c'est sa propre description.

**Ce que ce proxy ne capture pas** : la magnitude en dollars, et la distinction
« déjà balayée » (lignes pleines) / « pas encore balayée » (pointillés). La
seconde est reproductible — un extrême est « non balayé » tant que le prix ne
l'a pas dépassé depuis sa formation. La première ne l'est pas ; le nombre
d'extrêmes agglomérés dans une bande étroite en est le substitut naturel, et
c'est exactement le critère qu'il énonce (« a lot a lot of combined liquidity »).

**À écrire dans le verdict** : cette substitution est la limite principale du
test. Un échec ne réfute pas sa méthode, il réfute *notre proxy de sa méthode*.
Un succès, en revanche, est informatif : il signifierait que l'edge tient sans
l'indicateur propriétaire — ce qu'il affirme lui-même.

---

## 3. Séquence à reproduire

Telle qu'il la déroule sur son exemple Bitcoin, dans l'ordre :

1. **Contexte HTF** — tendance weekly/daily (structure de hauts/bas + EMA 200).
2. **Zone chargée** — amas d'extrêmes non balayés dans une bande étroite.
3. **Approche lente** puis **sweep** : le prix pénètre la zone, prend les stops,
   souvent sur une bougie rapide et isolée.
4. **NE PAS ENTRER** sur le sweep. C'est l'erreur qu'il dit avoir corrigée.
5. **Attendre la structure de retournement** : après un sweep de bas, un creux
   plus haut se forme et un sommet intermédiaire est cassé.
6. **Entrée** sur cette cassure. Sur son exemple, il exige une cassure *nette*
   et renonce quand de la liquidité reste disponible en dessous.
7. **Stop** sous l'extrême du sweep / sous le creux plus haut.
8. **Cible** = amas de liquidité opposé. Si R:R < 2, il ne prend pas.
9. **Sorties partielles** aux amas intermédiaires.

## 4. Ce qui est hors périmètre du backtest

- « feeling for the chart » (il y revient plusieurs fois) — non testable, et il
  faut l'écrire dans le verdict plutôt que de prétendre l'avoir modélisé.
- Le DCA long terme crypto : c'est sa *seconde* activité, pas cette stratégie.
- Le filtre news : testable seulement via un calendrier économique. À défaut,
  un proxy horaire est acceptable **s'il est déclaré comme tel**.
