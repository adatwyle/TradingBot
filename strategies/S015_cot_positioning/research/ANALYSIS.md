# Analyse — s15_cot_positioning « le positionnement des gros opérateurs a-t-il une valeur prédictive ? »

Source : rapport *Commitments of Traders* de la CFTC, via `core/data/cot.py`.
Mandat : `TODO.md` §3e PILIER (décision Adrian de sceller ou non une étude
« positionnement »). Trader : interne. Magic : **130015**.

**Numérotation** : `s14` est déjà pris par `studies/s14_sentiment/` (étude
scellée sur le sentiment des news, sans trading et sans magic). Le numéro est
sauté pour qu'il n'existe jamais deux objets « s14 » de nature différente dans
le dépôt ; `130014` reste non attribué au registre.

---

## 0. LE FAIT QUI COMMANDE TOUT LE PROTOCOLE

> **Klitgaard, Thomas & Weir, Laura — « Exchange Rate Changes and Net Positions
> of Speculators in the Futures Market » — Federal Reserve Bank of New York,
> *Economic Policy Review*, mai 2004.**
> https://papers.ssrn.com/sol3/papers.cfm?abstract_id=596902

Ce que les auteurs mesurent :

| Résultat | Portée |
|---|---|
| Les **variations hebdomadaires** des positions nettes des spéculateurs expliquent **30 à 45 %** des mouvements de change de **LA MÊME semaine** | corrélation **synchrone**, forte |
| Connaître le positionnement d'une semaine donne **~75 %** de chances de deviner la direction de **cette semaine-là** | corrélation **synchrone**, forte |
| Ces mêmes données **NE PRÉDISENT PAS** la semaine suivante | pouvoir **prédictif** : absent |

Les trois lignes disent la même chose sous trois angles : la relation est
**contemporaine, pas prédictive**. C'est une observation sur ce qui s'est déjà
produit, pas une information sur ce qui va se produire.

### Les deux conséquences, déclarées AVANT toute mesure

**1. L'attente rationnelle a priori de ce dossier est un edge faible ou nul.**
Nous n'ouvrons pas ce dossier parce que nous pensons que le COT prédit. Nous
l'ouvrons parce que la question revient constamment dans le marketing des
brokers, parce que la donnée est gratuite et possède un historique long — donc
falsifiable — et parce qu'un « non » chiffré sur nos instruments et nos coûts
est un livrable de pleine valeur. La conséquence opérationnelle est écrite ici
pour ne pas pouvoir être révisée plus tard :

> **Un résultat positif sera traité avec suspicion, pas avec enthousiasme.**
> Devant un signal fort, la première hypothèse à instruire est un défaut
> d'alignement des dates ; la découverte vient en dernier.

**2. La corrélation synchrone est si forte qu'une erreur d'alignement ne
produit pas un petit biais : elle fabrique un edge spectaculaire et
entièrement faux.** 75 % de réussite directionnelle est un chiffre qu'aucune
stratégie honnête du dépôt n'a jamais approché. Un backtest qui lit la donnée
du mardi dès le mardi — ou pire, qui l'aligne sur la semaine qu'elle décrit —
retrouve mécaniquement une partie de ces 75 % et les présente comme un edge.
D'où le contrôle de fuite du §5, qui est la pièce centrale du protocole.

---

## 1. Ce que le projet sait déjà (état de l'art interne)

| Dossier | Enseignement réutilisé ici |
|---|---|
| s12 / s13 (MACD D1) | Le **terrain D1 est bon** : péage mesuré 0,46 pt de win rate, 1-5 % du R selon la géométrie. Un petit edge peut y survivre. C'est le seul timeframe compatible avec une donnée hebdomadaire. |
| s91 (H1 forex) | Un signal brut réel (+0,05 R/t) **tué par le péage H1**. Confirme qu'on ne descend pas sous D1 pour un signal ténu. |
| s90 (fade de l'échec, CLOS — PAS D'EDGE) | Un motif qui n'existe que sur l'ensemble ayant servi à le découvrir est une **sélection**, pas un phénomène. D'où, ici : hold-out scellé dimensionné, et lecture méfiante de la « cohérence » entre deux instruments qui partagent leur jambe dollar. |
| s93 / rejeu | La gestion fine détruit. → **sorties simples uniquement**, déclarées d'avance, peu nombreuses. |
| `studies/gold_forward` | Le motif du **forward-test scellé zéro argent** : la seule suite légitime d'un EDGE CANDIDAT, jamais une promotion. |
| `studies/s14_sentiment` | Le motif du **protocole scellé sur donnée exogène** : univers, colonnes, seuils et règle de verdict figés avant la première observation. |
| Corpus des verdicts (13+) | Le taux de base du dépôt est **majoritairement négatif**. Ce n'est pas du pessimisme, c'est l'antériorité. |

## 2. Périmètre — contrats DIRECTS uniquement, et pourquoi cette frontière

**Cette étude porte sur DEUX instruments et deux seulement :**

| Instrument RobinBot | Contrat CFTC | Code | Nature du lien |
|---|---|---|---|
| **XAUUSD** | GOLD (COMEX) | `088691` | contrat **direct** — le sous-jacent est l'or |
| **EURUSD** | EURO FX (CME) | `099741` | contrat **direct** — le sous-jacent est l'euro contre dollar |

**Sont EXCLUES de ce dossier** : AUDCHF, AUDCAD, EURJPY — les paires sans
contrat propre, que `cot.synthetique()` reconstitue en soustrayant deux jambes
dollar. Elles feront l'objet d'une **étude séparée et scellée à part**.

**Pourquoi cette frontière est structurelle et non cosmétique :**

1. Un synthétique est une **hypothèse de décomposition**, pas une mesure. Rien
   ne garantit que le positionnement sur AUDCHF s'écrive (AUD/USD − CHF/USD) :
   l'essentiel du volume sur ces crosses se traite en spot et en CFD, hors du
   CME. Le collecteur le dit lui-même (`cot.py`, docstring de `synthetique()`).
2. Mélanger les deux dans un seul scellé rendrait toute lecture ambiguë : un
   résultat obtenu sur l'euro **contaminerait** la lecture du proxy, et un
   échec du proxy salirait un résultat direct. Deux questions différentes
   exigent deux protocoles, deux hold-outs, deux verdicts.
3. Le **signe** du lien est trivial pour les directs (long EURO FX = long
   EURUSD ; long GOLD = long XAUUSD) et demande une **inversion** pour les
   synthétiques bâtis sur USDJPY, USDCHF, USDCAD. Une convention de signe qui
   change au sein d'un même run est une source de bug silencieux.

## 3. Timeframe : D1, comme contrainte et non comme choix

Le COT est **hebdomadaire**. Un point de donnée couvre ~5 barres D1 et ~120
barres H1. Il ne porte donc **aucune information de timing horaire** : sur H1,
120 barres consécutives partageraient la même valeur de signal, et tout
« edge » horaire mesuré serait un artefact de la géométrie de sortie, pas du
positionnement.

**D1 uniquement. Aucune variante H4 ou H1 n'est prévue, ni autorisée en cours
de route.** Corollaire assumé : la fréquence de décision est **hebdomadaire**,
soit ~52 opportunités par an et par instrument — c'est peu, et tout le
dimensionnement du protocole (hold-out, effectifs) en découle (§4 de
`FALSIFICATION.md`).

## 4. Données

### 4.1 Prix
`core/data/source.py` — barres D1 MT5 Swissquote, cache
`C:\db\tbot\bars_cache\*_D1_*.pkl`, épinglé par les runners (`max_age_hours`
neutralisé) pour la reproductibilité. Profondeur effective ≈ **20 ans**
(2006-08 → 2026-08) — c'est le **facteur limitant** du dossier.

### 4.2 COT
`core/data/cot.py` — rapport **Legacy** (`6dca-aqww`, historique depuis 1986),
colonne retenue : `pct_noncomm` = (longs non-commerciaux − shorts
non-commerciaux) / open interest. La normalisation par l'open interest n'est
pas cosmétique : l'OI a été multiplié par dix en quarante ans, une position
nette brute n'est pas comparable à travers les décennies.

**Asymétrie de profondeur, déclarée** : la série COT (GOLD depuis 1986, EURO
depuis la fin des années 1990) est **plus longue que l'historique de prix**.
Conséquence utile : la fenêtre glissante du percentile se calcule sur la série
COT seule et **précède** le premier prix — aucun signal n'est perdu au
démarrage de l'exploration, même pour la fenêtre de 260 semaines. Conséquence
subie : ~20 ans de COT or sont inutilisables faute de prix, et ne seront pas
récupérés.

### 4.3 Le rapport TFF est explicitement HORS de ce scellé
Le rapport TFF (`gpe5-46if`, depuis 2006) sépare *Leveraged Funds* (tactique)
d'*Asset Manager* (structurel) ; la littérature désigne les Leveraged Funds
comme la sous-catégorie informative et l'agrégat « non-commercial » comme
faiblement informatif. Ce dossier est néanmoins scellé sur **Legacy /
`pct_noncomm` uniquement**.

**Pourquoi** : (a) ajouter un second rapport doublerait la largeur de la
recherche sans qu'aucune prédiction chiffrée le distingue a priori ;
(b) le cache TFF n'est pas constitué (`TODO.md` : « à collecter avant de
sceller ») ; (c) surtout, TFF est précisément la **donnée nouvelle** qui
justifierait un second dossier scellé si celui-ci conclut PAS D'EDGE — au lieu
d'une énième relecture des mêmes barres (la règle de clôture de s90).

## 5. La chaîne de lecture causale — et le contrôle de fuite

### 5.1 Le problème
Le jeu de données CFTC ne porte **que la date du MARDI** (le snapshot). La
publication a lieu le **VENDREDI à 15h30 ET**. La date de publication ne figure
nulle part dans les données ; `cot.publication()` la reconstruit.

### 5.2 La règle de lecture, tranchée et figée : LUNDI

Toute lecture passe par `cot.connu_au(df, date_de_la_barre)`, et une entrée
n'est autorisée que sur la **première barre D1 de la semaine** (lundi, ou la
première barre effectivement cotée si lundi est férié).

**Pourquoi lundi et non vendredi soir** — le module autorise les deux
(« vendredi soir, voire le lundi suivant ») ; nous tranchons **lundi** :

| Raison | Détail |
|---|---|
| Marge temporelle | 15h30 ET ≈ 19h30-20h30 UTC ; la barre D1 du vendredi clôture à minuit heure serveur (≈ 21h-22h UTC). La marge est de **une à deux heures**, en fin de semaine, sur la liquidité la plus mince. |
| Fragilité de l'horodatage | L'offset serveur est **calibré empiriquement** (`source.py`, ±1 h). Une dérive du broker suffirait à faire basculer une entrée « vendredi » du bon côté au mauvais côté de la publication. Une fuite d'une heure sur une donnée à 75 % de corrélation synchrone n'est pas un détail. |
| R5 — cohérence backtest/live | En réel, viser une exécution dans une fenêtre de 90 minutes le vendredi soir est un dispositif fragile ; une entrée au close du lundi est trivialement exécutable. Un backtest doit refléter ce qu'on saurait faire. |
| Coût | Un jour de retard sur un signal dont la thèse porte sur la **semaine** suivante. Négligeable au regard du risque. |

Cette règle a une forme **machine-vérifiable** : pour chaque trade,
`date_barre_entrée >= publication(snapshot_utilisé) + 3 jours`. C'est
l'assertion **F0.1** de `FALSIFICATION.md` — une seule violation arrête tout.

### 5.3 Le contrôle de fuite — DEUX versions de chaque mesure

Toute mesure du dossier est produite en version **HONNÊTE** et en version
**FUITÉE**. La version fuitée est un **contrôle positif délibéré** : elle
mesure le dispositif, jamais l'hypothèse.

| Version | Lecture | Ce qu'elle représente |
|---|---|---|
| **HONNÊTE** | `connu_au()`, entrée au close du lundi suivant la publication | la seule mesure dont un chiffre puisse être lu comme un résultat |
| **FUITÉE-3J** | la ligne du mardi lue **dès le mardi**, entrée au close de ce mardi | l'erreur réaliste : appeler `serie()` sans passer par `connu_au()`. Fuite = 3 jours |
| **FUITÉE-CONTEMPORAINE** | le snapshot du mardi *t* lu dès le **mercredi *t−6*** (entrée au close, horizon 5 barres) | l'alignement **synchrone exact** que mesurent Klitgaard & Weir : le signal couvre la semaine qu'il décrit. C'est le **contrôle positif étalonné** — c'est là que les 30-45 % / 75 % DOIVENT réapparaître |

**Pourquoi deux versions fuitées et pas une** : la fuite « réaliste » (lire dès
le mardi) déplace l'entrée de 3 jours mais ne récupère pas la semaine décrite
par le snapshot — elle ne garantit donc pas de faire apparaître l'effet connu.
La fuite contemporaine, elle, reproduit exactement l'alignement de la
littérature : si elle ne s'allume pas, ce n'est pas une nouvelle sur le monde,
c'est un branchement faux. Sans elle, l'absence de signal fuité serait
ininterprétable.

Les trois règles de lecture (alignement cassé / dispositif sain / bug de
pipeline) sont chiffrées et figées en **F0** de `FALSIFICATION.md`.

> **Ce contrôle ne sert JAMAIS à valider l'hypothèse.** Aucun chiffre issu
> d'une version fuitée n'entre dans une candidate, ne passe au hold-out, ni
> n'apparaît au verdict autrement que comme mesure de l'instrument. Un
> résultat fuité spectaculaire vaut exactement zéro comme évidence sur
> l'avenir — c'est même son rôle de l'être.

## 6. L'espace de conception — trois familles, pas de cellules infinies

Constantes hors grille, déclarées avant toute mesure : ATR 14 sur D1, warmup
60 barres, entrée au close de la barre de décision, stop TOUJOURS renseigné
(R3), une position à la fois par instrument.

### 6.1 Famille A — **extrême de positionnement** (contrarien) — l'hypothèse

État : percentile glissant de `pct_noncomm` sur les `lookback` dernières
observations **publiées**, calculé causalement.
- `pct ≤ q` (« état BAS », les non-commerciaux sont anormalement vendeurs)
  → **LONG**
- `pct ≥ 1 − q` (« état HAUT », anormalement acheteurs) → **SHORT**

**Pourquoi cette famille en premier** : c'est la seule dont le mécanisme est
compatible avec l'edge que le projet a effectivement rencontré (mean reversion
D1, s12/s13). Le récit est celui de l'encombrement : quand une position
directionnelle est saturée, le flux marginal capable de la pousser plus loin
est épuisé, et le déséquilibre se dénoue. Il ne contredit pas Klitgaard & Weir
— qui testent la variation, pas le niveau extrême.

### 6.2 Famille B — **impulsion de positionnement** — la famille de la littérature

État : percentile glissant de **Δ`pct_noncomm`** sur une semaine (variation
d'un snapshot au suivant), même `lookback`, mêmes queues `q`.
- Δ dans la queue haute (achat massif) → **LONG**
- Δ dans la queue basse (vente massive) → **SHORT**

**Pourquoi** : c'est exactement l'objet mesuré par Klitgaard & Weir. Ils
trouvent l'effet **synchrone** fort et l'effet **prédictif** nul. Cette famille
est donc le test direct de leur conclusion sur nos instruments, nos coûts et
notre géométrie — et c'est aussi le support naturel du contrôle positif
FUITÉE-CONTEMPORAINE.

### 6.3 Famille C — **témoin inverse (suiveur)** — étalon interne, pas candidate

Famille C = **la lecture inverse des mêmes états** : état BAS → SHORT, état
HAUT → LONG (et symétriquement pour B).

**Elle n'ajoute AUCUNE cellule d'exploration** : la dimension `sens` de la
grille est déjà {long, short} sur chaque état, si bien que C sort du même run
sans un seul backtest supplémentaire. C'est délibéré, et c'est la différence
avec la famille B de s13 (qui, elle, coûtait des cellules) : un étalon interne
ne doit pas élargir la recherche.

**À quoi elle sert** : toute candidate contrarienne doit **dominer** sa lecture
suiveuse. Si le suiveur domine, ce n'est pas une bonne nouvelle déguisée —
c'est l'indication que le résultat vit dans la géométrie de sortie ou dans une
dérive de l'instrument (l'or monte sur la période), pas dans le positionnement.

### 6.4 Sorties — deux, déclarées d'avance

| Nom | Géométrie | Pourquoi |
|---|---|---|
| `hold5` | sortie temporelle à **5 barres D1** (une semaine), stop **3 ATR**, pas de cible | C'est LA géométrie de la question posée : le positionnement d'une semaine dit-il quelque chose de la semaine suivante ? Le stop large existe pour satisfaire R3 sans piloter le résultat, et il chiffre le risque de queue au lieu de l'ignorer. |
| `atr_2_2` | cible **2 ATR** / stop **2 ATR**, RR 1:1, `max_hold_bars=25` (5 semaines) | Géométrie symétrique honnête, déjà employée par le dépôt. Sert de contrôle : si un résultat n'existe que sous `hold5`, il est un artefact d'horizon ; s'il n'existe que sous `atr_2_2`, il est un artefact de géométrie. |

**PAS de gestion fine** (trailing, break-even, pyramidage, sortie partielle) :
s93 et le rejeu ont montré qu'elle détruit. Aucune ne sera ajoutée en cours de
route ; une idée née des chiffres est consignée comme piste post-hoc pour un
dossier futur, pas testée ici.

La grille exacte (valeurs de `lookback`, de `q`, nombre de cellules) est figée
au §Grille de `FALSIFICATION.md`.

## 7. Hypothèse testable — H15, une conjonction de clauses

> **H15** — Sur XAUUSD et EURUSD en D1, un état de positionnement extrême des
> non-commerciaux (famille A) précède un mouvement de retour vers l'équilibre
> **suffisant pour payer le péage**, à horizon d'une à cinq semaines, dans au
> moins un sens, de façon stable à travers les fenêtres, supérieure au hasard
> à dispositif de risque identique, et confirmée UNE fois sur un hold-out
> scellé de cinq ans.

H15 n'est vraie que si **TOUTES** les clauses suivantes le sont. Chacune est
rattachée à un falsifieur chiffré de `FALSIFICATION.md` :

| # | Clause | Falsifieur |
|---|---|---|
| **C0** | *Le dispositif de mesure est valide* : la version honnête ne lit rien qui ne fût public, et la version fuitée retrouve l'effet synchrone connu. | **F0** (gate — aucun verdict sans elle) |
| **C1** | *L'effet existe avant le péage* : l'espérance est positive à coût nul. | **F1** |
| **C2** | *L'effet est du timing, pas du profil de risque* : la règle bat des entrées aléatoires à dispositif identique. | **F2** + **F3** (multi-graines) |
| **C3** | *L'effet repose sur assez d'observations INDÉPENDANTES* : pas seulement assez de trades. | **F4** |
| **C4** | *L'effet n'est pas une cellule isolée* : le voisinage de paramètres tient. | **F5** |
| **C5** | *L'effet tient dans au moins un sens pris séparément*, et **domine sa lecture suiveuse** (famille C). | **F6** + **F7** |
| **C6** | *L'effet survit hors de la fenêtre qui l'a sélectionné* : hold-out scellé, ouvert une fois. | **F9** |

La cohérence entre les deux instruments (**F8**) est **informative et faible**,
pas décisive : XAUUSD et EURUSD partagent la jambe dollar, un régime de dollar
les déplace tous les deux. Deux instruments corrélés ne font pas une
réplication indépendante — c'est déclaré ici pour ne pas être plaidé plus tard.

## 8. Reproductibilité et dégradations assumées

| Composant | Réalisable ? | Dégradation |
|---|---|---|
| Positionnement net normalisé (`pct_noncomm`) | **Oui** — donnée réelle, cache local | aucune |
| Date de publication | **Oui** — `cot.publication()` reconstruit la règle du vendredi | reconstruction par règle, pas par donnée observée : une publication exceptionnellement décalée hors du gel 2025 ne serait pas vue |
| Percentile glissant causal | **Oui** — sur la série publiée uniquement | aucune |
| ATR 14, stops, cibles | **Oui** — barres OHLC | remplissage de cible au toucher intrabar (dégradation héritée du moteur, déclarée) |
| Positionnement du **spot** OTC | **Non** | le COT ne couvre que les futures listés aux États-Unis. Substitut assumé : le positionnement futures comme **proxy** du positionnement global (§9.4) |
| Positionnement **retail** | **Non** | aucune source avec historique téléchargeable (cf. `TODO.md`). Hors périmètre. |
| Granularité intra-hebdomadaire | **Non** | la donnée est hebdomadaire. Contrainte, pas dégradation (§3) |

## 9. Réserves du collecteur — reprises de `core/data/cot.py`, déclarées ici

Ce sont des limites **connues avant la mesure**. Aucune n'est un motif
d'abandon ; toutes changent la lecture d'un résultat.

### 9.1 L'API sert la version RÉVISÉE
La CFTC corrige et republie silencieusement (transferts de comptes, erreurs de
déclarants). `rafraichir()` est incrémental et conserve la **première version
reçue** — mais l'historique initial téléchargé **est déjà la version révisée**.

**Ce que ça implique concrètement** : la totalité de notre échantillon,
exploration ET hold-out, est de la donnée révisée. Notre backtest voit une
série plus propre que celle qui était visible le jour même. Un edge marginal
pourrait donc être en partie « emprunté » aux révisions. **Aucun falsifieur de
ce dossier ne peut attraper ça** — c'est un angle mort structurel, et c'est un
argument de plus pour que la seule suite d'un EDGE CANDIDAT soit un forward
scellé, où la donnée est vue telle qu'elle arrive. Seule parade prospective :
nos propres instantanés datés, à partir de maintenant.

### 9.2 La suspension de publication de 2025
Arrêt budgétaire fédéral : **aucune publication du 30 septembre 2025 au 29
décembre 2025** (`GEL_2025` dans `cot.py` — suspension à partir du 30 septembre,
rattrapage achevé le 29 décembre). Les lignes existent dans l'historique mais
n'étaient pas publiques. `publication()` repousse toute publication tombant
dans cette fenêtre au 29 décembre — la retenir à sa date théorique serait
exactement la fuite combattue.

Deux conséquences : (a) l'épisode tombe **dans le hold-out** (§Hold-out de
`FALSIFICATION.md`), ce qui est souhaitable — le scellé contient le pire cas ;
(b) c'est un **risque opérationnel en live** documenté d'avance : le flux peut
s'arrêter trois mois, et une stratégie qui en dépend est alors aveugle.

### 9.3 La reclassification des catégories de traders
La CFTC a modifié au fil des décennies la définition et l'affectation des
catégories. La série « non-commercial » **n'a pas une définition constante sur
quarante ans** ; elle mélange des acteurs qui n'étaient pas classés pareil en
1990 et en 2020.

**Mitigation a priori, intégrée à la conception** : le signal n'utilise jamais
un niveau absolu, seulement un **percentile glissant** (104 ou 260 semaines).
Une dérive lente de définition est absorbée par le fait que la distribution de
référence est locale. **Limite de cette mitigation** : un changement en marche
d'escalier n'est pas absorbé — il crée un faux extrême pendant toute la durée
de la fenêtre glissante. Déclaré, non corrigé.

### 9.4 Futures ≠ spot
Le COT porte sur des **futures listés aux États-Unis** (COMEX gold, CME euro FX)
— pas sur le spot/CFD que trade Swissquote. Les deux marchés sont arbitrés et
très corrélés, mais ce sont deux populations d'acteurs différentes : le
positionnement futures est un **proxy** du positionnement global, et il ignore
par construction le spot OTC, qui est la part dominante du change.

C'est la substitution centrale du dossier. Elle est assumée : elle est bien
plus tenue que celle des synthétiques (§2), et elle est la seule disponible.

### 9.5 Ce que le COT ne couvrira jamais
DAX et FTSE n'ont **aucun** rapport COT (la CFTC ne couvre que les bourses
américaines). Toute extension future de ce motif aux indices européens est
impossible par absence de donnée, pas par manque de travail.

## 10. Ce qui est figé où

Le protocole complet — hold-out scellé, contrôle de fuite chiffré, grille
exacte, définition des épisodes indépendants, règle de sélection des
candidates, falsifications F0-F9, règles de verdict — est dans
**`research/FALSIFICATION.md`**, gelé et commité **AVANT le premier backtest**.

Le présent document ne sera plus modifié après le gel, hormis une éventuelle
section de verdict croisé dans `VERDICT.md`. Aucun chiffre de résultat n'existe
au moment où ces deux fichiers sont écrits.
