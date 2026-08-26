# PROTOCOLE — étude scellée s14 « sentiment des news forex » (collecteur + juges, zéro trading)

> **Ce fichier est un scellé.** Il est écrit **avant** la première news collectée
> et avant le premier verdict rendu, et ne doit plus être modifié ensuite. Il
> fixe l'univers, les colonnes du journal, les seuils et la façon dont le
> verdict sera rendu. Toute conclusion future se lit contre ce qui est écrit
> ici, et nulle part ailleurs. Motif repris de `studies/gold_forward/PROTOCOL.md`
> — la valeur entière du dispositif tient à l'impossibilité de tricher
> rétroactivement.

**Date de scellement** : 2026-08-17
**RE-SCELLÉ le 2026-08-18** (amendement n° 1, voir ci-dessous)
**Dépôt au scellement** : le commit qui introduit ce fichier et `params.json`
(couche git du § 3, intégrité)

> ### Amendement n° 1 — 2026-08-18 : source des news
>
> **Ce qui change** : `collect.category` passe de `forex` à `general`.
> Le hash de `params.json` change donc aussi (§ 1.1).
>
> **Pourquoi** : le premier passage réel, le 2026-08-18 à 20:42 UTC, a révélé
> que l'endpoint `category=forex` de Finnhub ne renvoie **qu'un seul article
> par appel** — un calendrier économique publié par une source unique
> (Forexlive). Mesure faite le même jour sur les quatre catégories :
> `forex` 1 article, `general` 100 (Reuters 72, CNBC 21, Bloomberg 7),
> `crypto` 99, `merger` 58. Faire juger six mois de calendriers aurait produit
> un « NON CONCLUSIF, matière insuffisante » connu d'avance. Ce qui meut les
> paires de l'univers — Fed, BCE, inflation, emploi — est précisément le
> contenu de `general`.
>
> **Pourquoi c'est légitime malgré le scellé** : au moment de l'amendement, le
> corpus contenait **0 news et 0 verdict** — journal en-tête seule, aucune
> mesure d'aucune sorte. On ne modifie donc PAS une règle après avoir vu des
> résultats (ce que le scellé interdit) : on corrige une source d'entrée avant
> d'en avoir lu le premier. Les seuils, l'univers, les falsifications, les
> colonnes du journal et les règles de verdict sont **inchangés**. Les données
> de l'étude ont été remises à zéro et le scellé reposé.
>
> **Faute reconnue** : la catégorie avait été figée sans qu'on ait jamais
> regardé ce que l'endpoint renvoyait. C'est l'erreur exacte que cette
> discipline est censée empêcher ; elle est consignée ici plutôt que corrigée
> en silence, et la leçon vaut pour toute étude future — **mesurer une source
> avant de la sceller**.
>
> **Conséquence sur l'angle mort déclaré au § 4** : la couverture n'est plus
> « USD/EUR-centrique via un flux forex », mais « macro généraliste, dominée
> par Reuters ». XAUUSD, AUDCHF et AUDCAD restent les moins bien couverts —
> l'angle mort demeure, sa cause change.
**Origine** : mandat Adrian, inspiré du MLTradingBot de Nicholas Renotte
(FinBERT sur headlines, action seulement si probabilité > 0,999). La source ne
publie aucune mesure de valeur informationnelle de ce seuil — c'est précisément
ce que cette étude mesure, avant tout usage.
**Décision de lancer** : Adrian.

---

## 0. Ce que l'étude mesure — et ce qu'elle ne mesure pas

**Cette étude ne trade pas.** Aucun ordre, aucun compte virtuel, aucun R. Elle
constitue un **corpus de verdicts de sentiment horodatés**, scellé au fil de
l'eau, pour instruire — plus tard, et uniquement sur les règles écrites ici —
la question : le sentiment des news forex a-t-il une valeur informationnelle
mesurable sur nos instruments ?

**L'hypothèse testable** : un juge LLM (Claude CLI headless) lisant les
headlines forex des dernières heures peut produire, par instrument, un verdict
directionnel (`positive`/`negative`/`neutral` + confiance 0..1) qui, aux
confiances élevées (≥ 0,8), prédit le signe du rendement de la barre D1
suivante de l'instrument **mieux que le hasard ET mieux que le témoin FinBERT
local**.

**Le corollaire falsifiable, assumé d'avance** : FinBERT est gratuit (local,
zéro token). Si Claude ne le bat pas sur le même corpus, les tokens ne sont pas
justifiés — l'étude continue en FinBERT seul et le résultat est un livrable de
pleine valeur (F3, § 5).

**Ce que l'étude ne mesure pas** : la rentabilité d'un usage trading (aucune
exécution, aucun coût modélisé au-delà du plancher § 5/F2), la valeur du
sentiment en intra-journalier, la qualité du flux Finnhub lui-même, et la
causalité (un hit-rate élevé peut refléter du momentum déjà dans les prix).
Quel que soit le verdict, **aucune promotion trading directe** — décision
Adrian (règle R10 du projet).

---

## 1. Configuration FIGÉE

Source unique : `studies/s14_sentiment/params.json`.

### 1.1 Le scellé cryptographique

```
SHA-256(params.json) = 31023cf9ab977374bf9de539a908cd0cfdedce46a3acad42c4adfc19ff20bfab
```

Ce hash sera répliqué dans la constante `PARAMS_SHA256` du code livré avec
l'étude (`run_sentiment.py`), qui refusera de tourner si le fichier ne
correspond plus (exit 3), et dans le test
`test_hash_du_vrai_fichier_scelle_correspond` qui casse à la moindre
divergence. Triple consignation : protocole, constante, test — motif commun
aux études scellées du dépôt.

### 1.2 Univers FIGÉ — cinq instruments, justifiés

| Symbole | POURQUOI il est là |
|---|---|
| AUDCAD | bras principal du forward scellé s13 (`studies/s13_forward/`) |
| EURJPY | bras d'observation du même forward |
| XAUUSD | instrument du forward `studies/gold_forward/` |
| AUDCHF | survivante S1 (EA MQL5 en production papier) |
| EURUSD | survivante S1, et l'instrument le plus couvert par les news forex |

Le corpus est construit là où le projet a déjà des signaux vivants : si le
sentiment a une valeur, c'est comme **filtre sur ces flux-là** qu'elle
s'exploiterait (§ 6) — pas sur un univers abstrait.

### 1.3 Contenu (copie de lecture — `params.json` fait foi)

| Élément | Valeur |
|---|---|
| Worker | **un seul** : `s14_sentiment`, passage toutes les 1800 s (`collect.interval_s`) — collecte puis jugement, dans cet ordre (§ 2.1) |
| Collecteur | Finnhub `GET https://finnhub.io/api/v1/news?category=general`, dedup par id Finnhub, headline tronqué à 300 chars |
| Péremption | `collect.max_news_age_h` = **6 h** : une news plus vieille (âge contre `published_at_utc`) au moment du jugement est consommée sans être jugée (`STALE`, § 3) |
| Juge | `claude-cli` : CLI `claude -p --output-format json`, prompt par STDIN, timeout 180 s, 1 relance, lot ≤ 40 news — jugement à chaque passage où des news non jugées non périmées existent |
| Témoin | `finbert` : ProsusAI/finbert local, zéro token |
| Seuil de confiance « élevée » | **0,8** (`falsification.confidence_threshold_high` — commun à TOUT juge) : seul un dernier verdict directionnel à confiance ≥ 0,8 est comptable (§ 4) |
| Heure serveur ↔ UTC | serveur Swissquote = UTC+2 (hiver US) / UTC+3 (été US), bascule au DST américain (`bar_mapping`, § 4) |
| Falsifications | N ≥ 150 comptables ET ≥ 60 jours (F1) ; fermeture F2 seulement si borne haute IC 95 % unilatéral < 0,52 ; delta témoin ≤ 0 sur cellules appariées (F3) ; deux moitiés > 0,50 chacune (F5) ; borne basse IC 95 % unilatéral > 0,52 exigée pour toute valeur |
| Intervalle de confiance | 95 %, **unilatéral**, **Wilson** — partout (`ci_level`, `ci_method`, `ci_sided`) |
| Durée maximale | 6 mois |
| Graine | 20260817 — scellée par précaution : aucune procédure de lecture définie par ce protocole n'est aléatoire (IC de Wilson et coupe des moitiés sont déterministes) ; tout tirage auxiliaire d'une lecture secondaire devra l'utiliser et se documenter |

---

## 2. Le dispositif

### 2.1 Un seul worker, un seul écrivain (`s14_sentiment`)

Un unique worker séquentiel `s14_sentiment` exécute un passage toutes les
1800 s. Chaque passage, dans cet ordre : (1) vérification du scellé et de la
chaîne du journal (§ 7), (2) **collecte** Finnhub, (3) **jugement** des news
non jugées s'il y en a — les deux juges, dans le même passage. POURQUOI un
seul écrivain : le journal est chaîné par hachage (§ 3) ; deux écrivains
concurrents pourraient entrelacer leurs appends et casser la chaîne — un
écrivain unique rend la collision impossible par construction, sans verrou.

Le jugement n'a **pas de cadence propre** : il a lieu à chaque passage où des
news non jugées et non périmées existent — lecture « moment opportun » ; rien
à juger → no-op. L'échec de la collecte (clé absente, Finnhub injoignable)
n'empêche pas la phase de jugement du même passage — les news déjà collectées
ne l'attendent pas ; le passage rend alors exit 2 (§ 7).

### 2.2 Collecte (phase 1)

- Appel `GET https://finnhub.io/api/v1/news?category=general&token=<KEY>` à
  chaque passage. Clé : variable d'environnement `FINNHUB_API_KEY`, sinon
  fichier `C:\db\tbot\s14_sentiment\finnhub_key.txt` (hors dépôt, jamais
  commité). Clé absente ou service injoignable → **exit 2** (§ 2.1 — le
  jugement du passage a quand même lieu), journal intact, réessai au passage
  suivant.
- **Dedup par id Finnhub** : une news = au plus une ligne `NEWS` au journal, à
  vie. Deux passages sur le même flux n'ajoutent rien (idempotence).
- **Sanitisation avant écriture** : retours à la ligne strippés (la chaîne du
  journal repose sur le découpage par lignes — un `\n` dans un champ casserait
  la vérification), headline tronqué à 300 chars. POURQUOI 300 : assez pour un
  titre complet, assez court pour borner le prompt du juge et la taille du
  journal.

### 2.3 Juge Claude (`claude-cli`) — phase 2

- Invocation : `claude -p --output-format json`, **prompt par STDIN, jamais en
  argv** — plafond Windows de 32k sur la ligne de commande, leçon payée par
  `studies/macd_ai_paper/`. Environnement nettoyé avant l'appel
  (`CLAUDE_*`, `CLAUDECODE*`, `ANTHROPIC_BASE_URL` retirés) pour que le CLI
  headless ne soit contaminé par aucune session parente.
- Timeout 180 s, **une** relance. Panne persistante (`is_error`, timeout, JSON
  illisible, 401) → verdicts `na` journalisés pour le lot, **jamais de crash,
  jamais de blocage du témoin** : les curseurs des juges sont indépendants.
- **Péremption avant tout jugement** : pour chaque juge (curseur propre), les
  news en attente plus vieilles que `collect.max_news_age_h` = **6 h** — âge
  mesuré entre `published_at_utc` et l'instant du passage — sont **consommées
  sans être jugées** : le curseur avance, une ligne `STALE` est journalisée
  (§ 3). Jamais jugées, jamais comptables. POURQUOI : un verdict n'a de sens
  que proche de sa news (même logique que les `na`, § 3) — juger une news de
  la veille mesurerait le prix déjà réalisé, pas le sentiment.
- **Jugement PAR LOT** : à chaque passage, le juge prend les news non encore
  jugées par lui et non périmées (curseur propre), au plus 40, dans l'ordre du
  journal ; le reste attend le passage suivant. Rien de nouveau → no-op
  (« moment opportun »), exit 0. Un lot consommé ne l'est qu'une fois : les
  curseurs garantissent qu'on **ne rappelle jamais le juge** sur les mêmes
  news.
- Sortie exigée : JSON strict `{"verdicts": [...]}` avec, pour **chaque**
  instrument de l'univers :
  `{"symbol": ..., "sentiment": "positive"|"negative"|"neutral", "confidence": 0..1, "reason": "<une phrase>"}`.
  Le clamp force les bornes côté code (confiance ramenée dans [0;1], sentiment
  hors vocabulaire → `na`, symbole manquant → `na`, symbole hors univers →
  ignoré). Le prompt n'est jamais la seule barrière.
- Le texte du prompt est figé au premier passage de mesure ; il relève de
  l'invariance § 5.

### 2.4 Témoin FinBERT (`finbert`) — phase 2

- ProsusAI/finbert **local** (import paresseux ; bibliothèque ou modèle
  indisponible → verdicts `na`, l'étude continue). Zéro token. Mêmes règles de
  curseur, de lot et de péremption que le juge Claude (§ 2.3).
- Score par headline, agrégé par lot par **softmax de la somme des logits** —
  le motif exact du MLTradingBot source, répliqué à l'identique pour que le
  témoin soit bien « la méthode de la vidéo » et pas une variante flatteuse.
  La confiance journalisée est la probabilité de la classe majoritaire.
- Le verdict de lot est **mappé uniformément sur les cinq instruments** :
  FinBERT ne connaît pas les paires. C'est une différence assumée avec Claude
  (qui peut différencier par instrument) et un **angle mort déclaré** : le
  témoin mesure le sentiment du flux, pas celui d'un instrument.

### 2.5 Multi-juges — la frontière du scellé, déclarée d'avance

La colonne `judge` vaut aujourd'hui `claude-cli` ou `finbert` ; les valeurs
`gpt-*` sont **réservées** pour des juges futurs. **Ajouter un juge n'est PAS
une violation du scellé.** POURQUOI cette frontière : le scellé porte sur la
**règle de mesure** — univers, colonnes, seuils, falsifications, tous dans
`params.json` — pas sur le recensement des mesureurs. Un juge ajouté écrit des
lignes nouvelles dans un journal append-only : il ne peut ni altérer un verdict
passé ni déplacer un seuil, et il est évalué contre les mêmes falsifications,
avec son propre compteur F1 démarrant à son arrivée. Conditions d'ajout :
entrée datée en annexe de ce protocole (ajout, jamais modification du corps),
configuration du nouveau juge scellée dans son propre fichier
`params_<judge>.json` avec hash consigné dans la même annexe, `params.json`
intact. Symétriquement, **couper un juge au fichier juges** (§ 8) est un acte
opérationnel, pas une violation.

---

## 3. Journal — colonnes FIGÉES et conventions

**Emplacement** (jamais dans l'arborescence de code — convention projet) :

```
C:\db\tbot\s14_sentiment\
├── journal.csv        # append-only, chaîné — LA pièce du dossier
├── state.json         # curseurs (collecteur + un par juge), empreinte journal
├── status.json        # dernière lecture (effectifs, distance à F1)
├── run.log            # sorties des passages
├── judges.txt         # interrupteur par juge (opérateur, optionnel — § 8)
└── finnhub_key.txt    # clé API (hors dépôt, jamais commitée)
```

**Colonnes, dans cet ordre, figées** :

```
measured_at_utc, event, news_id, published_at_utc, source, headline,
judge, symbol, sentiment, confidence, reason, chain
```

**Événement `NEWS`** (une ligne par news dédupliquée) : `measured_at_utc` =
instant de collecte ; `news_id` = id Finnhub ; `published_at_utc`, `source`,
`headline` = champs Finnhub sanitisés ; `judge`/`symbol`/`sentiment`/
`confidence`/`reason` vides.

**Événement `VERDICT`** (cinq lignes par lot et par juge — une par instrument) :
`measured_at_utc` = instant du jugement ; `judge` ∈ {`claude-cli`, `finbert`} ;
`symbol` ∈ univers ; `sentiment` ∈ {`positive`, `negative`, `neutral`, `na`} ;
`confidence` ∈ [0;1], vide si `na` ; `reason` = une phrase sanitisée (≤ 300
chars, retours à la ligne strippés — pour `na` : la cause courte, ex.
`timeout`, `json illisible`) ; `published_at_utc`/`source`/`headline` vides.

**Événement `STALE`** (péremption § 2.3 — une ligne par juge et par segment
contigu de news périmées) : `measured_at_utc` = instant du passage ; `judge` =
le juge dont le curseur avance ; `news_id` = plage `"<id_première>..<id_dernière>"`
du segment consommé sans jugement (même convention que les lots) ; tous les
autres champs vides. Aucune colonne nouvelle. POURQUOI ce marquage : le curseur
de chaque juge doit rester reconstructible depuis le journal seul — sans trace
de péremption, un trou dans les jugements serait indistinguable d'une perte de
données.

**Convention de lot, tranchée ici** : un verdict couvre PLUSIEURS news. Son
`news_id` est la plage `"<id_première>..<id_dernière>"` — les ids Finnhub de la
première et de la dernière ligne `NEWS` du lot **dans l'ordre du journal**. Le
lot est par construction un segment contigu de lignes `NEWS` du journal (le
juge consomme depuis son curseur, dans l'ordre d'écriture) : la reconstruction
du lot ne suppose **aucune** monotonie des ids Finnhub, seulement l'ordre du
journal, qui est append-only. Un lot d'une seule news s'écrit `"<id>..<id>"`.

**Verdicts `na`** : journalisés, le curseur du juge **avance** (le lot est
consommé). POURQUOI : rejuger des news des heures plus tard produirait des
verdicts contaminés par le prix déjà réalisé — un verdict de sentiment n'a de
sens que proche de sa news. Les `na` n'entrent dans aucun effectif, aucune
mesure ; une panne d'un juge ne fausse jamais l'autre.

**Intégrité — trois couches** (motif commun aux études scellées) :
1. `journal.csv` est **append-only à chaîne de hachage** : chaque ligne porte
   dans `chain` le SHA-256 du fichier tel qu'il était avant elle. Modifier,
   insérer ou supprimer une ligne passée casse tous les maillons suivants et le
   passage suivant refuse de tourner (exit 4).
2. Chaque ligne porte l'horodatage de **mesure** (`measured_at_utc`) en regard
   des horodatages de contenu (`published_at_utc`) : un verdict antérieur à ses
   news, ou des mesures non monotones, sont un antidatage visible.
3. La couche externe est **git** : protocole, hash et code committés avant la
   première news. Un falsificateur qui réécrit journal + état + git réécrit
   l'histoire d'un dépôt — détectable par les remotes, hors du modèle de menace
   d'une étude qu'on se fait à soi-même.

---

## 4. La mesure de valeur — définitions figées d'avance

Ces définitions sont celles que le script de lecture appliquera. Elles ne se
renégocient pas à la lecture.

- **Heure serveur ↔ UTC, figé** : le serveur MT5 Swissquote est à **UTC+2
  quand les États-Unis sont à l'heure d'hiver, UTC+3 quand ils sont à l'heure
  d'été** — la bascule suit le DST américain (2e dimanche de mars → 1er
  dimanche de novembre). Table ancrée dans `params.json`
  (`bar_mapping.server_utc_offset_winter` = 2,
  `bar_mapping.server_utc_offset_summer` = 3, `bar_mapping.dst_rule` = "US").
  L'**ouverture d'une barre D1** est son **timestamp nominal** (00:00 heure
  serveur du jour de la barre) converti en UTC via cette table : la barre du
  lundi ouvre dimanche 22:00 UTC (hiver US) ou 21:00 UTC (été US). Ambiguïté
  XAUUSD, tranchée ici : l'or peut n'avoir son premier tick qu'après 00:00
  serveur (pause du sous-jacent) — c'est le **timestamp nominal qui fait
  foi**, pas le premier tick.
- **Barre cible** d'un verdict : la première barre D1 de l'instrument dont
  l'ouverture (définie ci-dessus, en UTC) est **strictement postérieure** à
  `measured_at_utc` du verdict. Week-end : la barre D1 du lundi OUVRE dimanche
  ~21 h/22 h UTC (selon DST) — un verdict émis samedi ou dimanche **avant**
  l'ouverture serveur vise la barre du lundi ; émis **après** l'ouverture, il
  vise la barre du mardi. Zéro lookahead, même le dimanche soir.
- **Rendement** : `close/open − 1` de la barre cible. Un rendement exactement
  nul compte comme **échec** (convention conservatrice).
- **Succès** : `positive` et rendement > 0, ou `negative` et rendement < 0.
  Les `neutral` ne font aucune revendication directionnelle : exclus du
  hit-rate, leur part est documentée à la lecture.
- **Verdict comptable** : par cellule (juge, symbole, barre cible), le
  **DERNIER verdict du juge avant l'ouverture de la barre fait foi** ; il
  n'est comptable que s'il est **directionnel à confiance ≥ 0,8**. Un
  `neutral` (ou une confiance < 0,8) tardif **annule** donc un `positive`
  antérieur : la cellule n'est pas comptable. POURQUOI : plusieurs lots dans
  la même journée partagent la même barre cible ; les compter tous serait de
  la pseudo-réplication — l'effectif N de F1 est l'effectif de la mesure, pas
  celui des lignes. Et retenir un verdict directionnel antérieur alors que le
  juge s'est rétracté depuis serait un biais de rétention.
- **Hit-rate** (par juge) : succès / verdicts comptables.
- **Angle mort déclaré — corrélation** : les cinq instruments partagent le
  flux macro — les verdicts comptables d'une même barre calendaire sont
  corrélés entre symboles. L'IC binomial surestime donc l'indépendance ; la
  lecture rapportera le découpage par symbole en lecture secondaire, sans
  correction prétendue.
- **Angle mort déclaré — couverture** : le flux Finnhub `category=forex` est
  USD/EUR-centrique ; XAUUSD, AUDCHF et AUDCAD seront peu couverts — les
  cellules par-instrument de ces symboles risquent d'être affamées, et la
  lecture secondaire par symbole d'autant moins puissante.

---

## 5. FALSIFICATIONS — chiffrées d'avance, c'est le cœur

Tous les seuils vivent dans `params.json` (§ 1.1) et sont identiques ici.
Tout intervalle de confiance de l'étude est un **IC 95 % unilatéral de
Wilson** (`ci_level` = 0,95, `ci_method` = "wilson", `ci_sided` = "one").

| # | Condition | Seuil | Si déclenchée |
|---|---|---|---|
| **F1** | Effectif minimal, par juge : verdicts comptables ET durée de collecte | **N < 150** OU **< 60 jours** calendaires | aucune lecture de valeur — le corpus n'a pas le droit de parler |
| **F2** | Fermeture pour absence de valeur, par juge : borne **haute** de l'IC 95 % unilatéral du hit-rate des verdicts comptables, évaluée aux lectures mensuelles post-F1 | **< 0,52** | **PAS DE VALEUR** pour ce juge — définitif. Sinon la question reste ouverte jusqu'à la lecture finale |
| **F3** | Témoin : hit-rate Claude − hit-rate FinBERT, sur le **corpus commun apparié par cellule** (symbole, barre cible) : les cellules où **les deux** juges ont un verdict comptable | **≤ 0** | les tokens ne sont pas justifiés — l'étude continue en FinBERT seul |
| **F4** | Concordance inter-juges : kappa de Cohen (3 classes) apparié par cellule (symbole, barre cible), sur les cellules où les deux juges ont un dernier verdict non-`na` avant l'ouverture (toutes confiances) | — | **informatif** — documenté et pesé au verdict, jamais éliminatoire |
| **F5** | Stabilité temporelle, par juge : hit-rate sur chacune des deux moitiés chronologiques des verdicts comptables (coupe à la médiane des horodatages) | **≤ 0,50 sur une moitié** | **NON CONCLUSIF** pour ce juge — une valeur qui ne tient que sur une moitié est un artefact de régime |

**POURQUOI ces seuils** :

- **F1, N = 150** : l'erreur-type binomiale à p ≈ 0,5 et n = 150 est ≈ 4 pts.
  Pour dégager un plancher à 52 % par borne basse d'IC 95 % unilatéral
  (Wilson), il faut observer ≈ 58-59 % — en dessous de 150, même un vrai
  avantage de 8 pts est indiscernable du bruit. 150 est le minimum auquel
  l'étude a le droit de conclure, pas un chiffre de confort.
- **F1, M = 60 jours** : au moins deux cycles complets de banques centrales
  (FOMC, BCE), pour qu'aucun événement macro unique n'écrive le verdict ;
  et ≈ 43 barres D1 par instrument, soit ≈ 215 créneaux comptables — le
  plancher qui rend N = 150 atteignable sans le garantir.
- **F2, plancher 0,52 et pas 0,50** : une pièce équilibrée fait 50 % ; toute
  exploitation paie le péage du spread, chiffré sur ce dépôt à ~1,85 % du R en
  D1 (0,46 pt de win-rate — `TODO.md`, mesure S5). Le plancher à 52 exige une
  marge ≈ 4× ce péage : un signal sous 52 % n'a aucune marge exploitable.
- **F2, fermeture sur borne HAUTE < 0,52 — pas sur le point** : la lecture est
  répétée mensuellement ; fermer un juge dès qu'un point passe sous 0,52
  multiplierait les occasions de fausse exécution sur du bruit. La fermeture
  exige l'évidence forte d'absence de valeur : borne haute de l'IC 95 %
  unilatéral sous le plancher, soit un hit-rate observé ≈ ≤ 0,45 à n = 150.
  Chiffrage : pour un juge à 55 % vrai, P(borne haute < 0,52) ≈ 1 % par
  lecture (Z ≈ −2,4), décroissant quand N grossit — quelques % cumulés sur
  les lectures mensuelles. La répétition séquentielle ne fabrique donc pas la
  fermeture d'un juge qui a de la valeur ; en revanche un juge vraiment sans
  valeur finit dessous. Un point faible sans cette évidence laisse la question
  ouverte jusqu'à la lecture finale.
- **F3, delta ≤ 0** : FinBERT coûte zéro. Le juge payant doit battre le juge
  gratuit **sur le même corpus**. Le corpus commun est **apparié par
  cellule** (symbole, barre cible) — les cellules où les deux juges ont un
  verdict comptable — et delta comme kappa se calculent sur ces observations
  appariées uniquement. POURQUOI par cellule et jamais « par lot » : les
  curseurs des juges sont indépendants et peuvent se désynchroniser après une
  panne partielle (l'un juge un lot que l'autre marque `na` ou périmé) — tout
  appariement par lot serait alors faux ; l'appariement par cellule ne dépend
  d'aucun alignement des lots. F3 ne se lit qu'après F1 atteint par les deux
  juges ; si le témoin n'atteint jamais F1, F3 est non évaluable et c'est
  documenté. Conséquence opérationnelle : juge Claude coupé au fichier juges
  (§ 8) — un acte d'exploitation, pas une violation.
- **F4 informatif seulement** : deux juges qui s'accordent sur du bruit
  s'accordent quand même — la concordance borne le signal partagé mais ne
  prouve aucune valeur. L'en faire un critère serait de la fausse rigueur.
  L'appariement est par cellule (mêmes raisons que F3) mais sans filtre de
  confiance, pour préserver les 3 classes du kappa.
- **F5, moitiés > 0,50 et pas 0,52** : la leçon constante du dépôt (s13, gold)
  — un effet qui n'existe que sur une sous-période est un artefact de régime.
  Mais chaque moitié n'a que n ≈ 75 : à un vrai 58 %, l'erreur-type y est
  ≈ 5,7 pts. Exiger 0,52 par moitié déclencherait à faux ≈ 15 % par moitié
  (≈ 27 % qu'au moins une échoue) ; à 0,50, le faux déclenchement tombe à
  ≈ 8 % par moitié, ≈ 15 % sur les deux. La règle teste l'**effondrement**
  d'une moitié, pas sa précision — l'exigence de marge reste portée par l'IC
  global sur l'effectif complet.

**Exigence supplémentaire pour toute revendication de valeur** (dans
`params.json` : `value_requires_ci95_low_above_floor`, avec
`f2_requires_ci95_high_below_floor` pour le miroir F2) : la borne basse de
l'IC 95 % unilatéral (Wilson) du hit-rate doit dépasser 0,52. Un point
au-dessus du plancher avec un IC qui le chevauche ne vaut rien.

### Invariance

**Aucun paramètre ne peut changer en cours de route.** Toute modification de
`params.json`, de l'univers, des colonnes du journal, du prompt du juge, des
définitions § 4 ou des seuils ci-dessus **invalide l'étude** : redémarrage à
zéro, nouveau scellé, nouveau journal. Le hash § 1.1 rend l'événement visible ;
ce paragraphe le rend inexcusable. (Exception unique : bug démontré du code de
mesure — invalidation déclarée, pas contournée.) L'ajout d'un juge suit la
frontière § 2.5 ; il ne touche à rien de ce qui précède.

---

## 6. Verdict — règles d'issue, écrites d'avance

Lues **par juge** (Claude et FinBERT chacun contre les mêmes règles), trois
issues possibles :

- **VALEUR CANDIDATE** : F1 atteint, borne basse de l'IC 95 % unilatéral
  (Wilson) du hit-rate > 0,52, F5 tient ; pour Claude s'ajoute F3 (delta > 0 —
  sinon la valeur éventuelle est portée par le témoin gratuit). Livrable :
  proposition d'une étude d'intégration du sentiment comme **FILTRE sur les
  signaux existants** (S1, s13) — **jamais comme signal autonome**. Et la
  leçon d'avril 2026 sera citée en tête de cette proposition : le filtre de
  régime HALT, testé sur 5 ans, n'a apporté qu'une amélioration marginale
  (~+700 CHF sur −5303 — `SPEC.md` §22, `RAPPORT_FINAL_2026-04-10.md`) parce
  qu'un filtre posé sur des signaux sans edge ne sauve rien. Un filtre
  sentiment ne vaudra que mesuré sur des signaux à edge mesuré, avec ses
  propres falsifications.
- **PAS DE VALEUR** : F2 déclenchée (borne haute de l'IC 95 % unilatéral du
  hit-rate < 0,52 à une lecture mensuelle post-F1) — définitif pour le juge
  concerné. Si les deux juges y sont, l'étude ferme par anticipation : un
  dispositif falsifié ne mérite pas ses 6 mois.
- **NON CONCLUSIF** : tout le reste — F1 jamais atteint à l'horizon (y compris
  un juge presque toujours `neutral` ou sous 0,8 de confiance : une sélection
  non informative ne remplit jamais F1), hit-rate au-dessus du plancher mais
  borne basse ne le dégageant pas, ou F5 échouée.

**Quel que soit le verdict, AUCUNE promotion trading directe.** Une VALEUR
CANDIDATE autorise une proposition d'étude — la décision est à Adrian (R10).
Le verdict final sera un `VERDICT_SENTIMENT.md` écrit **à l'arrêt de l'étude
seulement**, adossé ligne à ligne aux critères ci-dessus, journal en annexe.

---

## 7. Le pas de mesure — idempotence et codes de sortie

Un seul runner (`run_sentiment.py`), contrat de sortie commun aux études
scellées du dépôt :

```
0  passage effectué (y compris « rien de neuf »)      → OK
2  collecte indisponible (Finnhub, clé) — le jugement du passage a eu lieu
                                                       → réessai au passage suivant
3  scellé violé (hash de params.json)                 → INCIDENT, worker OFF
4  journal altéré (chaîne de hachage cassée)          → INCIDENT, worker OFF
```

À chaque passage : vérification du scellé et de la chaîne du journal **avant
toute écriture** ; puis, dans l'ordre : collecte dédupliquée (§ 2.2),
péremption (`STALE`, § 2.3), jugement des lots en attente (Claude puis
FinBERT, curseurs indépendants). Aucune news nouvelle, aucun lot en attente →
no-op, exit 0 : relancer plus souvent que nécessaire est sans effet et sans
risque. Panne d'un juge → `na` (§ 3), exit 0 ; panne de la collecte → exit 2,
journal intact, jugement du passage quand même effectué. **Premier passage =
pose du scellé** : le collecteur démarre au flux courant, aucun backfill
historique — un corpus prospectif ne se constitue pas rétroactivement.

---

## 8. Armement (décision Adrian — non exécuté par le dispositif)

L'étude est opérée par la console `orchestrator/robinbot-factory.py` — pas de
tâche planifiée Windows (décision Adrian 2026-08-17). **Une seule** entrée au
**catalogue** des workers (donnée FROIDE — ajout à la main dans la section
`WORKERS`, puis **redémarrage de la console requis**) :

```python
("s14_sentiment", ROOT, "py:studies/s14_sentiment/run_sentiment.py", 1800, "tick"),
```

L'interrupteur est le **panneau** `orchestrator/robinbot-panel.txt` (relu à
chaque cycle, effet au tick suivant, aucun redémarrage) :

```
s14_sentiment = on      # collecte + jugement toutes les 1800 s
```

Un worker absent du panneau est OFF. Le panneau allume ou coupe le **worker
entier**. **Couper UN juge** (« coupe Claude, il brûle des tokens ») sans
arrêter la collecte ni le témoin se fait dans le fichier opérateur
`C:\db\tbot\s14_sentiment\judges.txt` — même grammaire que le panneau
(`claude-cli = off`), relu à chaque passage, effet au passage suivant ;
fichier absent ou juge non listé = ON. C'est un acte opérationnel (§ 2.5),
hors scellé, comme le panneau. La factory met elle-même le worker OFF sur
exit 3 ou 4 — ce sont des alarmes de falsification, pas des pannes : on vient
**lire** avant de rallumer.

---

## 9. Durée et déclenchement de la lecture

- **Durée maximale : 6 mois** à compter du scellement. À l'échéance, lecture
  finale obligatoire et verdict selon § 6 — une étude qui n'a pas tranché en
  6 mois rend NON CONCLUSIF, elle ne court pas pour toujours.
- **Première lecture de valeur : au premier atteint de F1** (N ≥ 150 verdicts
  comptables ET ≥ 60 jours, par juge). Avant cela, `status.json` n'expose que
  les effectifs et la distance à F1 — les hit-rates ne sont pas calculés :
  on ne regarde pas la casserole.
- **Lectures suivantes : mensuelles** après F1. F2 (borne haute de l'IC 95 %
  unilatéral < 0,52) déclenchée à une lecture → arrêt définitif pour le juge
  concerné (§ 6), anticipé si les deux y sont. Sinon la question reste ouverte
  jusqu'à la lecture finale — pas de fermeture sur un simple point faible.

---

## 10. Fichiers du dispositif

| Fichier | Rôle |
|---|---|
| `PROTOCOL.md` | **Ce scellé.** Ne plus modifier (annexe multi-juges § 2.5 : ajout daté seulement). |
| `params.json` | Configuration figée — hash § 1.1. Ne plus modifier. |
| `sentiment_step.py` | bibliothèque (code livré avec l'étude) : collecte Finnhub, dedup, sanitisation, append `NEWS` ; péremption `STALE` ; lots, juge Claude headless, témoin FinBERT, clamp, `na`, append `VERDICT`. |
| `run_sentiment.py` | CLI du worker — un passage = collecte puis jugement (codes de sortie § 7 en tête). |
| `report_sentiment.py` | lecture contre F1-F5 et § 4 — jamais avant F1. |
| `test_sentiment_step.py` | scellé, chaîne, idempotence (juge jamais rappelé), dedup, sanitisation, clamp, `na`, péremption, convention de lot. |

Périmètre d'écriture : `studies/s14_sentiment/` et `C:\db\tbot\s14_sentiment\`
uniquement. Rien dans `core/`, rien dans `strategies/`, rien dans les études
armées (`gold_forward`, `s13_forward`, `macd_ai_paper`). Aucun ordre, jamais.
