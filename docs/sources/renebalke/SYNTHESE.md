# René Balke (BM Trading) — dépouillement des 15 transcripts

> **Objet** : extraire ce qui consolide nos stratégies, notre backtester ou nos
> méthodes, et préparer LA reproduction prioritaire. Rien d'autre.
> **Sources** : `docs/sources/renebalke/*.txt` — 15 transcripts, 232 000 caractères.
> Auteur unique : René Balke, programmeur MQL5 (@ReneBalke), site bmtrading.de.
> **Code** : source non récupérable — voir `code/README.md` ; version tutoriel
> reconstituée dans `code/RangeBreakout_tutorial_reconstruction.mq5`.
> **Date** : 2026-08-17. **Aucun fichier hors ce dossier n'a été modifié.**

---

## 0. Ce qu'il faut savoir avant de lire le détail

**Le modèle économique est le rebate broker, pas la vente d'EA.** Les EA sont
« gratuits » conditionnés à l'ouverture d'un compte IC Markets/IC Trading sous son
referral (`10` : « you support me, I support you »). Chaque vidéo pousse ce lien.
Ce n'est pas disqualifiant — c'est plus transparent que la vente de backtests sur
le MQL5 Market qu'il dénonce lui-même — mais ça oriente le contenu : il a intérêt
à ce que vous tradiez, pas nécessairement à ce que vous gagniez.

**Ce qui le distingue des cinq sources précédentes, vérifié dans les transcripts** :
1. **Il documente ses pertes avec les chiffres** : −8 759 € en mars 2025 détaillés
   strategy par strategy (`13`), −8 778 € cumulés sur GBPUSD en ~360 trades (`15`),
   USDJPY −3 000 € en janvier 2026 (`12`). Personne d'autre dans notre corpus ne
   fait ça.
2. **Il fait le geste que nous appelons R5 (conformance)** : comparaison
   backtest vs live sur la même période (`05`, `14`, `15`) — le seul de nos six
   auteurs à le faire, et c'est le composant qui MANQUE à notre plateforme
   (`core/validation/conformance.py` inexistant).
3. **Notre plateforme exacte** : MQL5/MT5, stop orders, magic numbers, strategy
   tester — transposition directe, pas une traduction depuis QuantConnect ou Python.

**Ce qui doit rester au conditionnel** : le « 50k → 113k » (`12`), le « 50k → 800k
en 10 ans » (`03`), le « +57k live en 16 mois » (`14`) sont des claims. Il cite
Myfxbook et un signal MQL5 public (« all of this is real and verified », `12`) mais
aucun lien vérifiable n'est dans nos transcripts. **Pour vérifier il faudrait** : le
lien Myfxbook du compte avec « track record verified » ET « trading privileges
verified », un historique continu depuis mars 2024, et la correspondance des
retraits déclarés (25 000 € retirés, 15 000 € déposés, `13`). Sans ça : plausible,
étayé par la granularité inhabituelle de ses chiffres perdants, non prouvé.

**L'angle mort structurel de sa méthode** (détail § 4) : il optimise sur 10-15 ans
**en plein échantillon** puis trade l'optimum. Aucun walk-forward, aucun
hors-échantillon, aucun comptage du multiple testing dans 232 000 caractères. Son
« hors-échantillon », c'est son compte live — et sur GBPUSD, ce test-là a rendu son
verdict : −10 000 €.

---

## 1. Tableau récapitulatif — trié par valeur décroissante

| # | Élément | Case | Source | Valeur |
|---|---|---|---|---|
| T1 | **Range breakout de session** (range horaire fixe 3h-6h, cassure, SL = range opposé, pas de TP, sortie 18h) | **À TESTER — reproduction prioritaire** | `01-06`, `15` | ★★★★★ |
| A1 | Protocole de conformance backtest ↔ live sur période identique | **À ADOPTER** | `05`, `14`, `15` | ★★★★☆ |
| A2 | Leçon « stop garanti en OHLC = auto-illusion » + suivi manuel SL/TP + filtre de spread à l'entrée | **À ADOPTER** (côté EA MQL5) / DÉJÀ FAIT (côté moteur) | `09` | ★★★★☆ |
| T2 | 1 vs 2 cassures par jour (la 2e cassure ajoute ~20 % de profit, PF plus faible) | **À TESTER** (dans la grille de T1) | `04` | ★★★☆☆ |
| T3 | Turnaround Tuesday (indices sous MA40 D1, achat lundi, sortie mardi soir) | **À TESTER** (2e priorité, D1, péage faible) | `07`, `11`, `13` | ★★★☆☆ |
| T4 | Filtre de taille de range (min/max en % du prix) | **À TESTER** (drapeau dans la grille de T1) | `05`, `06` | ★★☆☆☆ |
| D1 | Sortie par le temps plutôt que par le prix (« la sortie est l'heure ») | DÉJÀ IDENTIFIÉ — c'est la limite s91 §7.1, jamais testable chez nous | `01-03` | — |
| D2 | Magic number unique par EA, reprise après crash via magic | DÉJÀ FAIT (`MAGIC_REGISTRY.md`) | `01`, `02` | — |
| D3 | Sizing par risque fixe (% ou montant) hors de la logique de signal | DÉJÀ FAIT (R2) | `01`, `02` | — |
| D4 | « Un jour est aléatoire, seule la moyenne longue compte » | DÉJÀ FAIT (effectifs, IC) — et nous allons plus loin | `03`, `05` | — |
| R1 | GoLong (acheter les indices le matin, vendre le soir, levier) | **À REJETER** | `08`, `11`, `12`, `13` | — |
| R2 | « Trading is not about hit rate, not about risk reward, it's about making money » | **À REJETER** tel quel | `03` | — |
| R3 | Optimiser 10-15 ans plein échantillon puis trader l'optimum | **À REJETER** — c'est le sur-ajustement que notre harnais existe pour attraper | `15` | — |
| R4 | « Sideways de 5 mois = normal, ne rien changer » sans règle d'arrêt chiffrée | **À REJETER** en l'état (nous : règles d'arrêt écrites avant le live) | `11`, `13`, `15` | — |
| R5 | Comparaison visuelle des courbes comme preuve de conformance | **À REJETER** comme méthode (le principe, lui, est A1) | `14` | — |

**Écartés du top 5, et pourquoi** :
- **GoLong** (`08`) : long-only indices intraday avec levier. C'est du beta
  déguisé — exactement le motif que notre contrôle long/short a été conçu pour
  attraper (s01/USDJPY : +69,7 R long / −10,0 R short). Il l'admet lui-même :
  « yes it would probably make more sense to hold a ETF » (`08`). 33 000 € de ses
  60 000 € de profits viennent de cette stratégie (`11`) — dit autrement, **plus de
  la moitié de son track record est du levier sur le bull market indices
  2024-2025**, pas de l'edge. Son argument « free money » sur les gaps est en plus
  economiquement inversé : être flat la nuit, c'est renoncer à la prime overnight
  des indices, pas la capturer.
- **Stock gap** (`08` ne contient pas de stratégie gap actions exploitable — c'est
  un plaidoyer pour GoLong un jour de gap). Rien à extraire.
- **Vidéos 10-11** (logistique de téléchargement + bilan mensuel) : pas de contenu
  stratégique — mais elles établissent le modèle économique (§ 0) et les chiffres
  par stratégie (§ 3).
- **Bilan janvier 2026** (`12`) : utile comme donnée (USDJPY −3k le mois AVANT la
  vidéo « This EA is all you need »), pas comme méthode.

---

## 2. Le top 5, creusé

### 2.1 T1 — Le range breakout de session ★★★★★ (la reproduction prioritaire)

#### Le mécanisme exact, reconstitué code + transcripts

Par ordre de fiabilité : code dicté (`02`) > revue des inputs v1.40 (`01`) >
réglages tradés par symbole (`03/05/06/15`).

| Composant | Règle exacte | Source |
|---|---|---|
| Range | high/low des bougies **M1** entre deux horaires fixes (heure serveur broker, GMT+2/3 — `06` : « usually GMT+2 with my brokers ») | `02` code |
| Entrée | v1.40 : **deux stop orders** aux bords du range à la fin du range (buy stop au high, sell stop au low), buffer optionnel en points (0 chez lui). Version tutoriel : entrée marché au premier tick au-delà | `01`, `02` |
| Fréquence | **1er breakout seulement** : l'ordre opposé est supprimé dès exécution du premier (son réglage live actuel). Variante : 2 breakouts (§ 2.4) | `03`, `04` |
| Stop loss | Deux variantes selon le symbole : **SL factor 1** = autre côté du range (USDJPY `03`, GBPUSD `15`) ; **SL 1 %** du prix (USDJPY variante `05`, or `06`) ⚠️ base de calcul ambiguë chez l'auteur lui-même : « position open price » (`05`, `06`) vs range high/low (« I would just leave it as it is », `01`) |
| Take profit | **AUCUN**. « we do not have a take profit... there can be losses, but there can also be extremely high profits » (`03`) |
| Sortie | **Clôture forcée à heure fixe** (18:00 ; 18:55 pour l'or) + suppression des ordres non exécutés à une heure « delete » | `01-03`, `06` |
| Filtre | Taille de range min/max en % du prix : 0,2-0,4 % (USDJPY `05`), 0,15-0,85 % puis retiré (or `06`), aucun (GBPUSD `15`) | `05`, `06`, `15` |
| Sizing | risque fixe (1 % ou montant fixe €250-500), lots = risque / (distance SL en ticks × tick value) | `02`, `03` |

**Réglages tradés par symbole** (ses comptes live) :

| Symbole | Range | SL | Filtre | Clôture | Résultat live déclaré |
|---|---|---|---|---|---|
| USDJPY | 3:00-6:00 | autre côté du range | aucun | 18:00 | ~+10k € à déc 2025 (`11`), puis −3k en janv 2026 (`12`) |
| USDJPY (variante) | 3:00-4:30 | 1 % | 0,2-0,4 % | 18:00 | +1,5k € sur ~1 an (`05`) |
| XAUUSD | 3:05-6:05 | 1 % | 0,15-0,85 % puis retiré | 18:55 | « +15k € en 1 an » (`06`) ⚠️ contradiction § 4.6 |
| GBPUSD | 4:00-11:30 | autre côté | aucun | 18:00 | **−8,8k € sur ~360 trades** (`15`) |
| EURUSD | non détaillé | — | — | — | +1,5k € (`11`) |
| EURJPY | non détaillé | — | — | — | −2,5k € en 2 mois (`11`) |
| US30 / DE40 | non détaillé | — | — | — | +285 € / +460 € — « the worst performing... I could consider taking out » (`14`) |

#### Ses résultats annoncés ET ses pertes, sur la même stratégie

- **Claim phare** (`03`, USDJPY 10 ans, Dukascopy « 100 % quality », 1 %/trade,
  compounding) : 50k → 800k+. PF 1,27, WR < 50 %, gain moyen 2 888 vs perte
  moyenne 1 800. **Ces trois chiffres impliquent WR ≈ 44 % et une espérance
  ≈ +0,15 R/trade net** — c'est LE chiffre falsifiable à confronter à notre mesure.
- **Meilleurs jours** : « five to 10 times the risk » (`03`) — distribution à
  queue droite, cohérente avec « pas de TP + sortie à heure fixe ».
- **Pertes documentées sur la même famille** : GBPUSD −8,8k sur ~2 ans (`15`) ;
  EURJPY −2,5k (`11`) ; USDJPY −3k en janvier 2026, publié 3 jours avant la vidéo
  « This Range Breakout EA Is All You Need » (`12` du 08.02, `03` du 11.02) ;
  US30/DE40 ≈ zéro depuis le début (`14`). **Sur 7 symboles tradés, 2 portent
  l'essentiel du positif (USDJPY, or), 2 sont négatifs, 3 sont ≈ nuls.** Notre
  garde-fou de concentration s'applique à son book comme aux nôtres.
- **Aveu méthodologique** (`15`, GBPUSD) : « I tested I figured out what settings
  worked very very good in the last 10 years... and then I just started at an
  unlucky time » + « trading has a lot of components or aspects of gambling ».
  C'est la description exacte du sur-ajustement in-sample suivi de son
  échantillon hors-échantillon involontaire.

#### Vérifiable vs invérifiable

| Vérifiable par nous | Invérifiable |
|---|---|
| Le backtest 10 ans USDJPY (règles complètes, données Dukascopy publiques, notre cache MT5 couvre 5,1 ans) | Le live 50k→113k (Myfxbook cité, lien absent) |
| L'espérance implicite +0,15 R/trade | Ses fills réels, son spread IC Trading |
| La dégradation GBPUSD post-2024 (test de conformité inverse — voir § 6) | Le « live légèrement meilleur que le backtest » (`05`) |

#### Le lien avec s91 et s11 — la question centrale de la mission

**Ce n'est PAS le breakout que nous avons tué.** s11 (mort) : canal Donchian
**glissant**, déclencheur permanent, aucune structure horaire, TP à multiple
d'ATR. Lui : range ancré sur **l'horloge de session** (fin de nuit / matin
européen), un seul déclencheur par jour, sortie par le temps. Les deux partagent
le mot « breakout », pas la structure.

**C'est structurellement le jumeau inversé de s91.** s91 a mesuré que la fenêtre
22h-06h (faible liquidité) contient le seul signal brut jamais détecté sur ce
projet : la porte horaire apporte +0,05 R/trade OOS brut, tué par un péage 1,5×
supérieur. René trade la **cassure du range formé pendant cette même fenêtre**, au
moment où le vrai flux revient (3-6h ≈ fin de Tokyo / pré-Londres en heure serveur
GMT+2). s91 fade l'extension PENDANT la fenêtre mince ; René suit le mouvement qui
en SORT. Les deux exploitent la même structure d'information : l'heure.

**Pourquoi son package pourrait survivre au péage là où s91 est mort** — trois
mécanismes, tous mesurables :
1. **Distance de risque plus grande** : son SL = le range complet (3h de M1) ou
   1 % du prix (~150 pips USDJPY), contre 2-3 ATR H1 pour s91. Le drag
   `spread / distance_SL` chute mécaniquement — c'est la « seule voie ouverte »
   identifiée par s91 § 5.1 (attaquer le rapport signal/coût), appliquée sans le
   savoir.
2. **Pas de TP** : s91 plafonnait à 1,5 R ; lui laisse courir la queue droite
   jusqu'à 18h (5-10 R déclarés les meilleurs jours). Un péage fixe pèse moins
   sur une distribution à queue droite.
3. **1 trade/jour épisodique** : ~250 trades/an, contre la sur-fréquence qui a
   tué S5.

**Le confondant à déclarer d'avance** : USDJPY 2021-2024 = +4 932 pips de carry
(s91 § 2.6, fait #7 du projet). Une stratégie sans TP qui tient jusqu'au soir sur
une paire en tendance violente capture la tendance côté long. Son equity 10 ans
USDJPY peut être en partie du beta yen. **Le contrôle long/short est LE test**, et
il est non négociable avant tout verdict.

### 2.2 A1 — Le protocole de conformance backtest ↔ live ★★★★☆

> `05` : « I usually like to compare the performance in the strategy tester with
> the performance in the life account for the same period... what I don't want to
> see is that my strategy performs a lot worse in the life account than it does in
> the tester. »
> `14` : backtest 10 ans du portefeuille (363 558 €), « what-if » restreint à la
> période live (mars 2024 →), superposition avec les 57k € du live : « the graphs
> are so similar. It's actually shocking. »

**Pourquoi c'est le deuxième élément le plus précieux du corpus** : c'est
exactement notre R5 (`core/validation/conformance.py`), **qui n'existe pas dans le
dépôt** — la limite est déclarée dans les VERDICT de s11 (§ 6.8) et s91 (§ 6.8).
Lui le fait, systématiquement, et il en tire des décisions (garder USDJPY malgré
un an de sideways parce que le live colle au backtest, `05` ; envisager de retirer
US30/DE40, `14`).

**Ce qu'il faut adopter** : le principe — rejouer le backtest sur la période live
exacte et confronter. **Ce qu'il ne faut PAS copier** : sa méthode de comparaison,
purement visuelle (« the same development in the equity graph »). Aucune métrique,
aucun seuil, aucun test. La version rigoureuse : appariement trade par trade
(même jour, même sens), distribution des écarts de fill, et un seuil de
divergence déclaré d'avance. C'est le chaînon entre notre backtest et le
déploiement pulse/MQL5 — fichier visé : `core/validation/conformance.py` (R5),
enfin spécifiable sur un cas concret.

**Nuance d'honnêteté qu'il fournit lui-même** (`05`) : son live bat légèrement son
backtest, attribué au spread Dukascopy > spread IC Trading. C'est la direction
d'écart attendue quand les données de test sont plus chères que l'exécution
réelle — l'inverse serait un signal d'alarme. Transposé chez nous : notre spread
catalogue fixe vs le spread Swissquote réel, même logique de contrôle.

### 2.3 A2 — « Don't be an idiot » : l'illusion du stop garanti ★★★★☆

> `09` : optimisation en « 1 minute OHLC » avec SL serré → +700k fictifs ; le même
> réglage en « every tick based on real ticks » → **perte**. Cause : « it will
> give you the stop-loss price even if the price jumped below this stop-loss
> level... the only one you are fooling is yourself. »

Sa règle : en mode OHLC, ne PAS placer de SL/TP dur dans le marché — les suivre
**manuellement** dans le code et sortir au prix de marché ; et filtrer le spread à
l'entrée (`ask − bid < 0,5 %` du prix) pour éviter les entrées/sorties parasites
sur données à spread aberrant. Après ces deux corrections, son OHLC ≈ son
real-tick.

**Ce que ça vaut chez nous** :
- **Côté moteur de recherche : DÉJÀ FAIT, et notre audit est allé plus loin.**
  Notre moteur est pessimiste (stop prioritaire sur cible dans la même barre), et
  le bug de la même famille — mais de sens inverse — a été trouvé chez nous : le
  stop DANS un gap jamais rempli (s11 § 2.0, −210 R fantômes sur DAX). Sa leçon
  et la nôtre disent la même chose : **le modèle de remplissage du stop dans la
  barre décide du verdict**, dans les deux sens.
- **Côté EA MQL5 de déploiement : À ADOPTER.** Le filtre de spread maximal à
  l'entrée est une garde d'exécution réelle que notre EA Swissquote devrait
  porter (news, rollover, dimanche soir). Coût : cinq lignes dans l'EA.
- Sa hiérarchie des modes du strategy tester MT5 (OHLC pour dégrossir → real
  ticks pour valider) est directement réutilisable le jour où nous validons
  l'EA MQL5 dans le tester — c'est le praticien MT5 qui parle, et c'est notre
  plateforme.

### 2.4 T2 — 1 vs 2 cassures par jour ★★★☆☆

> `04` : environnement strictement identique (mêmes données Dukascopy, 1 lot fixe,
> mêmes 10 ans, USDJPY) ; seule la fréquence change. Résultat : 2 cassures =
> **+8 000 € (~+20 %) de profit total**, PF légèrement plus faible, recovery
> factor meilleur. « for the first five years or so... I always traded the first
> two breakouts. »

C'est le seul endroit du corpus où il fait une **ablation contrôlée à un facteur**
— méthodologiquement propre (une variable, environnement figé). L'intérêt pour
nous : la 2e cassure est un trade de **renversement** (le range a cassé d'un côté,
échoué, et casse de l'autre) — économiquement différent du 1er breakout. Si le 1er
breakout porte l'edge de session et le 2e est un coin flip qui ajoute du volume,
le R/trade doit chuter entre les deux configurations (notre règle : jamais juger
un filtre au PnL total — son +20 % de profit total avec PF en baisse est
exactement le piège que cette règle attrape). Coût d'inclusion : un booléen dans
la grille de T1.

### 2.5 T3 — Turnaround Tuesday ★★★☆☆

> `07` : indices (DE40, US30, UStech). Filtre : prix sous la **MA 40 jours** (sa
> valeur courante ; « can be of any periods »). Entrée lundi (à heure fixe, ex.
> 9:05, ou sur nouveau plus-haut du jour), sortie fin de mardi. Options : SL/TP
> off/percent/points, trailing — lui n'utilise pas de trailing.
> Résultats live (`11`, déc 2025) : +7 300 € cumulés, 113 trades, PF 1,44 sur
> US30. Pertes documentées (`13`, mars 2025) : −1 140 € US30 et −1 500 € UStech
> en un mois, et il identifie lui-même la vraie faiblesse : contrairement à
> GoLong, une perte du lundi-mardi **n'est pas récupérée** si l'indice remonte
> mercredi-vendredi.

**Pourquoi ça passe le premier filtre** : anomalie calendaire ancienne, simple,
publiée (littérature « Monday effect / turnaround Tuesday » des années 80) — nos
trois vérifications § 1 de METHODOLOGY. D1 → péage 0,46 point de WR (vs 2,14 en
H1) : l'économie du trade est viable avant même de coder. Effectif faible
(~1 signal/semaine max, conditionné à « sous MA40 ») : c'est le vrai risque —
sur 5,1 ans, peut-être 40-80 trades par indice, à la limite de nos seuils.
**2e priorité, après T1** ; verdict probablement « effectif insuffisant » mais le
test est bon marché et la famille (dip-buy conditionnel sur indices) est
orthogonale à tout ce que nous avons testé.

### 2.6 R3/R4 — Ses échecs comme données : GBPUSD et la discipline d'arrêt

Le transcript `15` est le document le plus précieux du corpus après `03`, parce
qu'il montre **le cycle complet du sur-ajustement vécu en argent réel** :
1. Optimisation 10-15 ans plein échantillon → réglages 4:00-11:30 (« I figured
   out what settings worked very very good in the last 10 years »).
2. Mise en live fin mars 2024 → « one of the worst periods we've ever seen in the
   last 10 years » : −8,8k € sur ~360 trades.
3. Ré-optimisation depuis le drawdown (balayage des heures 1h-5h30 × fins
   jusqu'à 11h30) → il constate que ses réglages ne sont plus optimaux → il
   décide de **ne rien changer**, au motif que le backtest 10 ans reste positif
   (PF 1,15) et que « there have been times like this before ».
4. Aucune règle d'arrêt : « it could be negative for the next 3 years and if
   this happens then of course I will be worried » — le seuil est une émotion
   future, pas un critère écrit.

**Valeur pour nous** : c'est un jeu de données de falsification gratuit. Nous
avons ses réglages exacts (range 4:00-11:30, SL = range opposé, pas de filtre,
clôture 18h), sa date de mise en live (fin mars 2024) et son résultat live
(−8,8k). **Si notre harnais, appliqué à ces réglages, montre un backtest 10 ans
positif MAIS un walk-forward qui échoue sur les tranches récentes, alors notre
méthodologie détecte ex ante ce que son compte a payé pour apprendre.** C'est le
test de validation de NOTRE outillage le moins cher du corpus (§ 6, F5).

À l'inverse, sa gestion du drawdown contient une vraie qualité à ne pas caricaturer :
il ne touche pas au levier, il ne martingale pas, il ne « rattrape » pas — la
discipline de non-intervention est réelle. Ce qui manque est la règle d'arrêt
chiffrée écrite avant (notre METHODOLOGY § 8).

---

## 3. Contradictions et concordances avec nos mesures

### C1 — Son +0,15 R/trade USDJPY vs notre +0,05 R brut d'effet de session

| | Lui (`03`) | Nous (s91) |
|---|---|---|
| Mesure | PF 1,27, WR ≈ 44 %, gain moyen 1,6× perte → ≈ +0,15 R/trade net, 10 ans | Effet de porte horaire : +0,05 R/trade OOS **brut**, net négatif (péage 1,5×) |
| Structure | Cassure du range de la fenêtre 3-6h, SL = range, pas de TP, sortie 18h | Fade de l'extension DANS la fenêtre 22-06h, RR ≤ 1,5 |
| Méthode | In-sample 10 ans, une config | Walk-forward ancré, 324 cellules, falsifications ex ante |

**Nature du désaccord** : pas une contradiction — deux exploitations différentes
de la même structure horaire, l'une mesurée proprement et morte au péage, l'autre
mesurée salement et déclarée vivante. Le facteur 3 d'écart (0,15 vs 0,05) peut
venir : (a) du package (queue droite sans TP, distance de risque large — § 2.1) ;
(b) du beta yen non contrôlé chez lui ; (c) du sur-ajustement in-sample. **Le test
qui départage est exactement la reproduction § 6** : contrôle long/short pour (b),
walk-forward + témoin mesuré pour (c), et ce qui reste est (a).

### C2 — « Breakout » : concordance avec la mort de s11, pas contradiction

s11 a tué la cassure Donchian glissante H1 (signal ≈ 0, +0,013 R/trade à spread
réel). Sa version est ancrée sur l'horloge et sortie par le temps. Si la
reproduction § 6 échoue aussi, la conclusion « toute la famille breakout est morte
chez nous, ancrée ou glissante » devient forte. Si elle réussit, la différence
structurelle (ancrage session) est démontrée porteuse — cohérent avec le
sous-verdict s91 (b) « la réversibilité/le régime dépend de la session ».

### C3 — Son testing MT5 vs notre moteur : même classe de bugs, sens opposés

Sa leçon `09` (stop garanti en OHLC = résultats fictifs favorables) et notre
artefact s11 § 2.0 (stop dans le gap jamais rempli = −210 R fictifs défavorables)
sont les deux faces du même défaut : **la sémantique du stop dans la barre**. Sa
règle pratique (suivre le stop manuellement, sortir au marché) est celle que notre
moteur applique déjà ; son cas renforce la priorité du « R1 côté exécution »
réclamé par s11 § 6.9 et l'audit § 5.3.

### C4 — Concentration par instrument : il illustre notre règle

Son book range breakout : USDJPY + or portent tout, GBPUSD/EURJPY détruisent,
US30/DE40 ≈ 0 (`11`, `14`). Notre règle « un book dont l'essentiel vient d'un
instrument est un pari » s'applique — et rejoint le motif or-comme-résidu :
**l'or apparaît encore une fois comme le survivant** (chez lui comme dans s01,
s11, et AI Pathways). Troisième source indépendante, même résidu.

### C5 — GoLong contredit frontalement notre contrôle directionnel

Il assume : long-only, « very similar to ETF investing », justifié par le levier
(`11`). Nous avons mesuré ce que vaut ce raisonnement (s01/USDJPY long +69,7 R /
short −10,0 R : un pari, pas un système). Pas de test à faire — c'est un
désaccord de doctrine, et notre position est mesurée. À noter honnêtement : sur
2024-2025, son pari a payé (33k €). Un pari qui paie reste un pari.

---

## 4. Les angles morts de la source — nos risques si on copie

1. **Aucun hors-échantillon dans 232 000 caractères.** Pas de walk-forward, pas de
   hold-out, pas de train/test. L'optimisation est plein échantillon, la
   sélection des réglages aussi (`15`). Risque si on copie : reproduire GBPUSD.
2. **Le multiple testing n'existe pas.** 200+ EA codés (site), 7+ symboles tradés,
   balayages d'heures (`15`) — et les vidéos montrent les survivants. USDJPY et
   l'or ont leurs vidéos « best strategy » ; EURJPY et GBPUSD n'ont que des
   post-mortems. C'est du data snooping via le présentateur, version honnête
   (il montre aussi les échecs) mais snooping quand même : **le dénominateur est
   inconnu**.
3. **Le survivorship de compte est réel** : les titres du canal (hors corpus)
   documentent des comptes FTMO et the5ers perdus. Le compte streamé est celui
   qui a marché. La granularité de ses pertes le distingue, mais un compte unique
   sur 2 ans reste n = 1.
4. **La conformance est visuelle** (§ 2.2) : « the graphs are so similar » n'est
   pas une métrique. Adopter le principe, pas la méthode.
5. **Aucun intervalle de confiance, aucun effectif critique.** « one or two days
   or even weeks is not interesting » (`04`) est juste, mais il n'a pas de seuil
   au-delà. 113 trades de Turnaround Tuesday sont déclarés « quite a good
   addition » sans IC (`11`).
6. **Incohérence interne non expliquée sur l'or** : +14,5k cumulés en avril 2025
   (`13`), « +15k live en un an » en mai 2025 (`06`), puis « €1,600 profit in
   this one single chart » en décembre 2025 (`11`). Soit un giveback de ~13k
   jamais commenté, soit une erreur de transcription (« 16,600 » ?), soit des
   comptes/charts différents. **Non résolu — à vérifier sur le Myfxbook si un
   jour accessible.** En l'état, ça affaiblit la traçabilité de tous les chiffres
   par symbole.
7. **L'heure serveur est un paramètre caché.** Ses 3h-6h sont en GMT+2/3 (heure
   broker, DST inclus). Transposer les bornes telles quelles sur Swissquote sans
   vérifier le fuseau ET le DST fabriquerait une stratégie différente. s91 § 6.6
   a documenté le même piège.

---

## 5. Ce qui est déjà chez nous — références

| Élément de la source | Chez nous |
|---|---|
| Stop suivi manuellement, remplissage pessimiste | `core/backtest/engine.py` (stop prioritaire sur cible) ; audit § 5.3 pour le résiduel |
| Risque fixe par trade, sizing hors stratégie | R2, `core/contracts/STRATEGY_RULES.md` |
| Magic number unique, reprise après crash | `core/contracts/MAGIC_REGISTRY.md` |
| « Un jour est du bruit, la moyenne longue compte » | Effectifs + IC, `METHODOLOGY` § 6 — en plus chiffré |
| Données de qualité pour le test (Dukascopy chez lui) | Cache MT5 Swissquote + garde R1 — et nous testons la causalité, lui non |
| Ne pas sur-leverager, ne rien changer en drawdown | `core/risk/guards.py` — en plus dur : règles d'arrêt ÉCRITES avant le live (METHODOLOGY § 8), ce que lui n'a pas |
| Sortie temporelle comme composant de stratégie | Identifié comme LA limite du harnais (s91 § 7.1) — voir § 6, prérequis |

---

## 6. Recommandation finale — la reproduction

**LA stratégie à reproduire en premier : le range breakout de session USDJPY
(réglages `03`), avec GBPUSD (réglages `15`) embarqué comme cas de falsification
inverse.** C'est un livrable d'analyse — Adrian arbitre ; rien n'est implémenté.

### Le contrat

- **Épisodique** (stops présents, 1-2 trades/jour, position unique) — moteur
  commun `core/backtest/engine.py`, R9.
- **Prérequis à arbitrer AVANT d'ouvrir le dossier** : la sortie à heure fixe
  (18h) est **la moitié du contrat** (pas de TP — sans sortie temporelle, la
  position sans TP ne se ferme jamais). Or `run_walk_forward` ne transmet pas
  `max_hold_bars` et une stratégie n'émet que entry/stop/target (limite s91
  § 7.1, jamais levée). Deux options : (a) petite évolution `core/` — transmettre
  `max_hold_bars` ou un `time_exit_hour` (décision Adrian, hors périmètre
  stratégie) ; (b) approximation `max_hold_bars` fixe ≈ 12-15 barres H1 — dégradée
  (l'heure de sortie dérive avec l'heure d'entrée) mais testable aujourd'hui.
  **Reco : (a)** — c'est la deuxième stratégie consécutive que ce mur bloque, et
  s91 § 7.1 désignait déjà ce test comme « celui qui aurait le plus de valeur ».
- **Timeframe H1** (range = high/low des barres 03:00-05:59 serveur), dégradation
  déclarée : lui construit sur M1 et entre en stop order intrabar ; nous
  détecterons la cassure à la clôture H1 → entrée retardée jusqu'à 1h et range
  légèrement différent. Notre M1 n'existe pas, notre M5 ne couvre que ~16 mois
  (METHODOLOGY § 9). L'entrée stop-level intrabar dépend de ce que le moteur
  permet — à établir en Phase 1, pas à contourner en douce.
- **Mapping horaire** : établir en Phase 1 la correspondance heure serveur
  Swissquote ↔ GMT+2/3 broker IC, DST inclus, AVANT de figer les bornes.
- **Instruments** : USDJPY (claim phare), XAUUSD (2e claim + résidu or récurrent
  du projet), GBPUSD (falsification inverse). EURJPY en témoin optionnel (son
  échec documenté).

### La grille (petite, délibérément)

| Paramètre | Valeurs | Justification |
|---|---|---|
| Fenêtre de range | {3-6h} (+ {3-4h30} USDJPY, {4-11h30} GBPUSD) | ses réglages tradés, pas un balayage |
| SL | {autre côté du range, 1 % du prix} | ses deux variantes |
| Breakouts/jour | {1, 2} | son ablation `04` |
| Filtre de range | {off, 0,2-0,4 %} | son filtre `05` |
| Sortie | 18h fixe | non balayée — c'est le contrat |

≈ 16 cellules par instrument — enregistrées au registre des essais si A7
(aipathways) est implémenté d'ici là.

### Falsifications ex ante (à figer dans ANALYSIS.md avant tout backtest)

1. **F1 — Témoin mesuré** (`attach_control_arm`, la référence depuis l'audit — la
   convention « X STRICT vs Y attendues » est ininterprétable, audit D2) : la
   config par défaut USDJPY doit dépasser le **p95** de 200 tirages aléatoires à
   dispositif de risque identique (mêmes heures autorisées, mêmes distances de
   stop, même effectif). Sinon : PAS D'EDGE.
2. **F2 — Contrôle long/short** : si le côté short USDJPY est ≤ 0 et que le long
   porte tout, avec asymétrie alignée sur la dérive yen → beta, pas edge
   (confondant déclaré § 2.1).
3. **F3 — Permutation horaire** (à instrument constant, comme s91 § 2.4) : le même
   contrat avec un range décalé (ex. 9-12h, sortie 24h plus tard équivalente) ne
   doit pas faire aussi bien. Si l'ancrage 3-6h n'apporte rien, la thèse de
   session tombe.
4. **F4 — Ablation du spread** : edge brut ≥ 1,5× le péage mesuré (la marge que
   s91 n'avait pas). Chiffrer le péage AVANT d'implémenter (METHODOLOGY § 2) :
   avec SL = range (~30-60 pips USDJPY) ou 1 % (~150 pips), le drag attendu est
   de l'ordre de 1-5 % de la distance de risque — à confirmer sur nos spreads.
5. **F5 — Conformité inverse GBPUSD** : réglages `15` figés, backtest 5,1 ans.
   Attendu si notre harnais vaut quelque chose : plein échantillon flatteur MAIS
   tranches OOS récentes (post-mars 2024) négatives, reproduisant ses −8,8k live.
   Si notre walk-forward déclare GBPUSD robuste, c'est NOTRE méthode qui a un
   problème — dans les deux sens, ce test est gagnant.
6. **F6 — Effectif** : ≥ 20 trades OOS médians par instrument, sinon NON CONCLUSIF
   sans négociation.

### Ce que le test tranchera

Si ça survit (F1-F4) : premier package exécutable construit sur l'effet de session
que s91 a mesuré brut — la réponse à la question centrale de la mission est OUI,
et la voie « distance de risque large + queue droite + épisodique » devient un
patron pour s90_adrian_synthesis. Si ça meurt au péage : l'effet de session reste
réel mais non packageable en H1 forex chez Swissquote, et la famille breakout est
close sous ses deux formes (glissante ET ancrée). Si ça meurt au témoin ou au
long/short : son 10 ans USDJPY était du beta plus du sur-ajustement, et le corpus
Balke se referme sur ses deux seuls legs durables — le protocole de conformance
(A1) et la leçon d'exécution (A2).
