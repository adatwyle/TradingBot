# HYPOTHESIS — s90 « fade de l'échec » (excursion adverse ≥ 3 ATR, cible ~1 ATR)

> **Statut : FIGÉ le 2026-08-17, AVANT tout nouveau backtest.** Aucun seuil,
> aucune grille, aucun instrument, aucune règle de verdict ne sera modifié
> après avoir vu un premier chiffre du présent dossier. Toute mesure
> postérieure qui dévie de ce protocole doit se déclarer post-hoc.

Ce dossier instruit LE candidat que quatre mesures indépendantes du projet
désignent. Il ne « cherche » pas un edge : il vérifie si celui déjà mesuré
quatre fois tient quand on le teste comme une stratégie autonome, sur un
univers déclaré d'avance, contre des témoins plus durs que ceux déjà passés.

## 0. Le dossier du motif — les quatre apparitions (antériorité)

| # | Dossier | Mesure | Sort |
|---|---|---|---|
| 1 | `s91_claude_scratch` (fade fenêtre asiatique) | brut réel +0,05 R/t OOS éligibles, spread nul | tué par le péage (facteur ~1,5) |
| 2 | `s09_balke_rangebreakout` §2.7 (trade « retournement » : cassure ratée puis traversée) | **+0,089 R/t × 367** réel | percentile 93,5-97 avec effectif témoin écarté — non concluant seul |
| 3 | `s10_legacy_meanrev` (résidu NIKKEI mean reversion) | seul instrument au-dessus du hasard, symétrique L/S | résidu, pas une preuve |
| 4 | `studies/grid_per_entry` (la décisive) | fade d'excursion ≥ 3 ATR, cible ~1 ATR : EURUSD +0,031 R/t × 197 (pct 100, 5/5 graines), XAUUSD +0,094 × 191 (5/5, porté par le SHORT contre un or haussier), DAX r3 +0,043 × 367 (5/5) — **net de spread réel + slippage 0,5 pip** | première survie au péage ; réserve §5.7 (témoin non conditionné aux excursions) |

Convergence structurelle : *l'échec d'un mouvement étendu est plus informatif
que le mouvement lui-même — et il ne devient exploitable que là où la cible
est assez large pour payer le péage.*

---

## 1. L'hypothèse causale (H90)

> **H90** : sur H1, quand le prix, à l'intérieur d'une tendance définie,
> subit une excursion adverse RAPIDE et PROFONDE (≥ 3 ATR depuis l'extrême de
> la jambe, sans que la tendance ait flippé), la dernière fraction de ce
> mouvement n'est plus portée par de l'information mais par du flux forcé —
> stops en cascade, réduction de risque mécanique, carnet aminci par le
> mouvement lui-même. Ce flux s'épuise ; il n'est pas remplacé par du flux
> informé (sinon la tendance aurait flippé). Le prix rétracte alors
> partiellement — de l'ordre d'une ATR — vers le consensus antérieur.
> Entrer dans le sens de la tendance supérieure, contre l'excursion, capture
> cette rétraction.

### Ce que H90 PRÉDIT (falsifiable)

1. **Dose-réponse** : l'espérance PAR TRADE croît avec la profondeur de
   l'excursion. Les entrées à 1-2 ATR sont du bruit ou pires (mesuré : rangs
   1-2 négatifs partout dans l'étude grid) ; l'effet n'apparaît qu'au-delà de
   ~3 ATR. Un résultat où le seuil 2 ATR bat nettement les seuils 3-4 ATR
   contredit le mécanisme « sur-extension ».
2. **Deux sens** : le mécanisme est symétrique. L'effet doit exister LONG et
   SHORT ; un résultat porté par un seul sens aligné avec la dérive de
   l'instrument est un beta, pas H90.
3. **Généralité** : stops en cascade et carnets amincis ne sont pas une
   propriété d'EURUSD, XAUUSD ou DAX. L'effet BRUT doit être présent sur les
   instruments liquides en général ; seule l'EXPLOITABILITÉ dépend du péage
   relatif (drag = coût aller-retour / cible de 1 ATR).
4. **Cible courte** : la rétraction est un retour partiel (~1 ATR), pas un
   retournement. Une cible à 2 ATR dilue l'effet (mesuré : G3 ne survit pas
   au rang 3+, hors DAX).

### Ce que H90 INTERDIT

- Un effet présent uniquement sur les 3 instruments vedettes de l'étude grid
  et absent partout ailleurs (à économie viable) → c'était de la sélection.
- Un effet qui ne survit qu'à spread nul → ce n'est pas un edge exploitable
  (issue déjà rendue pour s91 ; la même règle s'applique ici).
- Un effet qui disparaît quand on change la graine du témoin → aliasing.
- Un effet que des entrées aléatoires DANS LE MÊME ÉTAT d'excursion
  reproduisent PAS DU TOUT alors que le témoin non conditionné est battu et
  que l'état lui-même est perdant en aléatoire → incohérence interne, verdict
  au plus NON CONCLUSIF (voir F3b).

---

## 2. La règle candidate — COMPLÈTE et figée

Reprise à l'identique de la construction MESURÉE par l'étude grid (aucune
« amélioration » opportuniste) ; seul le seuil d'excursion est exposé en
paramètre, avec la géométrie de sortie.

### 2.1 Construction du signal

- **Tendance** : SuperTrend(10, 3.0) sur H1 donne le sens (+1/−1).
- **Gate** : ADX(14) H1 > 20 à l'instant du signal (le motif est un pullback
  DANS une tendance, pas un range).
- **Ancre** : en tendance UP, plus haut `high` depuis le flip (mise à jour
  causale barre par barre) ; symétrique en DOWN. L'ancre se réinitialise sur
  nouveau plus haut/plus bas (jambe soldée) ou sur flip.
- **Excursion adverse** : X_t = ancre − close_t (UP) ; close_t − ancre (DOWN).
- **Paliers** : espacement fixe de **1,0 ATR(14)** (le `s_mult=1.0` mesuré).
  k = ⌊X_t / ATR⌋. **Entrée au close** quand k atteint un palier entier
  ≥ `threshold_atr`, une seule fois par palier et par jambe (le palier compte
  comme tiré même si l'ADX le filtre — sémantique identique à l'étude).
- **Sens** : celui de la tendance SuperTrend (contre l'excursion).
- **Stop** : `sl_atr × ATR(14)_t` sous/sur l'entrée. **Cible** :
  `tp_atr × ATR(14)_t`. Pas de sortie temporelle (`max_hold_bars=None`).

### 2.2 Grille — 6 cellules, dérivée de H90, pas de la performance

| Paramètre | Valeurs | Justification a priori |
|---|---|---|
| `threshold_atr` | {2, 3, 4} | 3 = le seuil désigné par la mesure n°4 ET par H90 (sur-extension) ; 2 = sonde dose-réponse (H90 prédit ≈ ≤ 0) ; 4 = profondeur supérieure (H90 prédit ≥ seuil 3 par trade, effectif moindre) |
| `tp_atr` | {1.0} | la rétraction partielle de H90 — figé, pas balayé |
| `sl_atr` | {1.0, 2.0} | RR honnête 1:1 (la cellule G2 mesurée) + voisin desserré ; PAS de stop 6 ATR (proxy « sans stop » du grid, indéfendable en production) |

**Cellule primaire, désignée d'avance : `threshold_atr=3, tp_atr=1, sl_atr=1`**
(c'est la géométrie de XAUUSD r3_G2_s1.0 et l'équivalent RR honnête
d'EURUSD r3_G1_s1.0). Les 5 autres cellules sont des contrôles de voisinage
et de dose-réponse, PAS des candidates de repli : si la primaire échoue et
qu'une voisine « marche », le verdict reste l'échec de la primaire (le succès
de la voisine est consigné comme information, pas revendiqué).

### 2.3 Univers d'instruments — déclaré d'avance, et pourquoi

**Le test propre est TOUS les instruments du catalogue disposant du snapshot
H1 figé**, soit **17** :

EURUSD, USDCHF, USDJPY, USDCAD, AUDUSD, EURCHF, AUDCHF, EURJPY, AUDCAD
(forex), SP500, NASDAQ, DAX, FTSE, NIKKEI (indices), XAUUSD, XAGUSD
(métaux), WTIUSD (énergie).

- Exclus : EURCAD, CADCHF, CHFJPY, EURAUD (catalogue sans cache H1 figé —
  on ne mélange pas un snapshot figé et un téléchargement du jour) ; BTCUSD
  (cache H1 sur une autre profondeur, régime crypto hors mandat) ; GBPCHF,
  GBPUSD (en cache mais absents du catalogue — on ne devine pas un spec
  broker ; même exclusion que s91 §6.5 et l'étude grid).
- **EURUSD, XAUUSD, DAX sont l'ENSEMBLE DE DÉCOUVERTE** (l'étude grid les a
  sélectionnés sur ces mêmes barres). Leur re-mesure ici ne prouve rien —
  elle vérifie seulement la cohérence des chemins. **La mesure décisive est
  l'ensemble des 14 autres**, jamais utilisés pour sélectionner le motif :
  4 vus par l'étude sans y passer le témoin (USDJPY, AUDCAD*, SP500, WTIUSD)
  et 10 jamais testés sur ce motif (USDCHF, USDCAD, AUDUSD, EURCHF, AUDCHF,
  EURJPY, NASDAQ, FTSE, NIKKEI, XAGUSD).
  *AUDCAD avait passé en mince (21 trades) — classé hors découverte.
- H90 prédit l'effet BRUT partout ; l'effet NET seulement où l'économie le
  permet. **Filtre économique a priori (P0, avant tout backtest)** : drag =
  (spread catalogue + 2 × 0,5 pip) / (1 × ATR H1 médiane en pips) ; une
  cellule à drag > 25 % est déclarée morte sur papier (règle F4 de l'étude
  grid, reconduite telle quelle). Le verdict de généralité ne se juge que
  sur les instruments économiquement viables.

### 2.4 Dispositif de mesure

- Moteur commun R9 (`core/backtest/engine.py`) — aucune boucle maison.
- **Coûts réels partout** : spread catalogue + slippage 0,5 pip aux deux
  bouts. Aucun chiffre « brut » ne sera revendiqué comme edge.
- Walk-forward ancré 4 fenêtres (60/70/80/90 %), `engine_kwargs` explicites
  identiques stratégie/témoins : `max_positions=1, cooldown_bars=2,
  cb_losses=3, cb_cooldown_bars=24, max_hold_bars=None` (identiques à la
  mesure n°4).
- R1 (causalité) via `core.validation.causality --save`, complété par
  l'invariant de troncature multi-instruments dans le runner. `precompute`
  renvoie un DataFrame → couche indicateur réellement couverte.
- R5 (conformance) via `core.validation.conformance --save`.
- Effectifs AFFICHÉS partout. Toute métrique sans n est nulle.
- Snapshot figé : cache H1 du 2026-08-16 (2021-07 → 2026-08-14/16 selon
  instrument), `max_age_hours` neutralisé.

---

## 3. Falsifications — chiffrées, figées

| # | Condition | Seuil | Conséquence si déclenchée |
|---|---|---|---|
| **F1 — hasard (par cellule)** | Témoin apparié standard (`attach_control_arm`, 200 tirages, graine 20260816), **NON conditionné : tirages sur TOUTES les barres de la fenêtre**, à géométrie/effectif/sens identiques | percentile < 95, ou effectif témoin écarté, ou < 20 trades OOS | la cellule ne compte pas |
| **F2 — généralité hors découverte** | R/t OOS NET poolé de la cellule primaire sur les **14 instruments hors découverte économiquement viables** (drag ≤ 25 %) | ≤ 0 (avec n ≥ 100 trades poolés) | **le motif est une sélection post-hoc → PAS D'EDGE général** ; les 4 apparitions sont requalifiées coïncidence de sélection |
| **F3a — témoin non conditionné** | = F1, exigé aussi sur le POOL hors découverte (percentile du pool contre témoins agrégés par instrument, règle : ≥ 2 instruments hors découverte passent F1 individuellement) | < 2 instruments hors découverte passent F1 | l'edge général n'est pas démontré au niveau instrument (au mieux NON CONCLUSIF si le pool F2 est positif) |
| **F3b — témoin CONDITIONNÉ (réponse à la réserve §5.7)** | Tirages aléatoires restreints aux barres DANS L'ÉTAT (tendance active, ADX > 20, excursion ≥ threshold × ATR), géométrie identique, 200 tirages × 5 graines, mêmes engine_kwargs — sur les cellules de découverte ET le pool hors découverte | lecture à 3 issues, déclarée d'avance (ci-dessous) | voir mapping |
| **F4 — deux sens** | Décomposition L/S du pool survivant : chaque sens ≥ 0 R/t OU le sens négatif reste dans l'IC du bruit ; un résultat porté par un seul sens ALIGNÉ avec le beta témoin de la période | un seul sens porte + beta même signe | requalifié beta → la cellule/l'instrument ne compte pas |
| **F5 — stabilité multi-graines** | Percentiles F1 recalculés sur 5 graines (20260816, 20260817, 7, 424242, 990001) | < 4/5 graines ≥ 95 | cellule écartée (aliasing de grille documenté dans l'étude n°4) |
| **F6 — effectif** | < 20 trades OOS par cellule interprétée ; < 100 trades poolés pour toute conclusion de pool | — | NON CONCLUSIF sur l'objet concerné |
| **F7 — ablation coûts** | Rejeu spread nul + slippage nul (mêmes signaux) : chiffre le péage. Si une cellule n'est positive QU'À coût nul | — | elle est morte en exécutable (même issue que s91) ; consignée, pas revendiquée |
| **F8 — dose-réponse** | R/t OOS poolé (tous instruments viables) : threshold 2 vs 3 vs 4 | si threshold 2 > threshold 3 ET threshold 2 nettement > 0 | le mécanisme « sur-extension » de H90 est faux ; tout résultat positif restant est requalifié « anomalie non expliquée », pas EDGE CANDIDAT |

### Mapping F3b — trois issues, écrites d'avance

Le témoin conditionné mesure si le TIMING du palier ajoute quelque chose à
l'ÉTAT d'excursion. Notation : pct_c = percentile de la stratégie contre le
témoin conditionné ; E_c = R/t moyen NET des tirages conditionnés.

1. **pct_c ≥ 95** → le palier précis apporte de la valeur au-delà de l'état.
   Lecture la plus forte.
2. **pct_c < 95 MAIS E_c > 0** → l'état lui-même est l'edge (n'importe quelle
   entrée dans l'état gagne en moyenne) et notre règle le réalise. C'est une
   CONFIRMATION de H90 (c'est l'état de sur-extension qui paie), pas un
   échec : la réserve §5.7 est levée dans ce cas aussi.
3. **pct_c < 95 ET E_c ≤ 0** → contradiction : la stratégie ne bat pas des
   entrées aléatoires dans son propre état, et cet état est perdant en
   aléatoire. Le passage du témoin NON conditionné était alors un artefact
   (profil de risque/régime ATR). **Verdict au plus NON CONCLUSIF, jamais
   EDGE CANDIDAT.**

### Règles de verdict — écrites d'avance

- **EDGE CANDIDAT** si TOUTES : (a) F2 non déclenchée (pool hors découverte
  viable NET > 0, n ≥ 100) ; (b) ≥ 2 instruments hors découverte passent F1
  individuellement avec F5 ; (c) F3b issue 1 ou 2 ; (d) F4 non déclenchée
  sur le pool survivant ; (e) F8 non déclenchée ; (f) les cellules de
  découverte re-mesurées restent cohérentes avec l'étude n°4 (même ordre de
  grandeur — sinon expliquer l'écart avant tout verdict).
  → La SEULE étape suivante est alors un forward-test scellé (motif
  gold_forward), proposé à Adrian, jamais armé d'initiative.
- **PAS D'EDGE** si F2 déclenchée (le pool hors découverte, économiquement
  viable, est ≤ 0 net) ou si F4/F8 requalifient l'ensemble. Ce verdict CLÔT
  le motif : les quatre apparitions s'expliquent alors par la sélection, et
  aucune cinquième instruction n'est justifiée sans donnée nouvelle.
- **NON CONCLUSIF** si F6 (effectifs) empêche de trancher, ou si F3b issue 3,
  ou si les résultats hors découverte sont positifs mais sous tous les seuils
  de démonstration. Consigner précisément ce qui manque et à quel prix.

### Attente sous H0 (déclarée)

6 cellules × 17 instruments = 102 cellules, fortement corrélées (3 seuils de
la même jambe, 2 stops des mêmes entrées) : la convention n × 0,05 (~5
« pass ») est une borne de commodité. Le juge est le témoin mesuré (F1),
la réplication hors découverte (F2/F3a) et la stabilité de graine (F5) —
jamais un compte de cellules vertes.

---

## 4. Ce que cette instruction ne fait PAS

- Pas de nouvelle exploration de paramètres au-delà des 6 cellules déclarées.
- Pas de filtre de session, de jour, de news ajouté en cours de route — si
  une telle idée émerge des chiffres, elle est consignée comme piste
  POST-HOC pour un dossier futur, pas testée ici.
- Pas de sizing, pas de portefeuille, pas de PAPER/LIVE (décision Adrian).
- Pas de modification de `core/`, `server/`, d'une autre stratégie, ni des
  études sources.
