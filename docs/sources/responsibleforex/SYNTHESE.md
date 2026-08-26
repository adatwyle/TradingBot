# Responsible Forex Trading — dépouillement des 15 transcripts

> **Objet** : extraire ce qui consolide nos stratégies, notre backtester ou nos
> méthodes — au sens de notre méthodologie, pas au sens marketing. Rien d'autre.
> **Sources** : `docs/sources/responsibleforex/*.txt` — **15 fichiers présents**
> (numérotés 01-16, le `08` est absent du dossier), 133 000 caractères,
> sous-titres automatiques. Auteur unique, non nommé dans les transcripts
> (chaîne « Responsible Forex Trading », vend ses EAs : Comeback Kid, Ranger,
> Vigorous, Powerhouse, Gopher, Sharpshooter, Crackerjack).
> **Date** : 2026-08-17. **Aucun fichier hors ce dossier n'a été modifié.**
> Citations : `fichier @ mm:ss` (timestamps des sous-titres, granularité 30 s).

---

## 0. Ce qu'il faut savoir avant de lire le détail

**Le modèle économique est la vente directe des EAs** (+ Discord, indicateurs
en appât `13 @ 04:30`). C'est un biais plus direct que le rebate broker de
Balke : chaque backtest montré est un argument de vente du produit montré. Ni
disqualifiant ni ignorable — traité claim par claim ci-dessous.

**La « sobriété » de la source est segmentée, et c'est le constat central du
dépouillement.** Les vidéos de *posture* sont réellement sobres : « les
institutions font 2-3 % par mois... 24 à 40 % sur 12 mois c'est considéré très
bon » (`12 @ 04:00`), « plus de 10 % mensuel ne tient typiquement pas plus de
trois mois » (`12 @ 03:30`), « je finirai probablement à 2-3 % » (`12 @ 05:30`).
Ça recoupe mot pour mot notre calibre externe (METHODOLOGY §10, Darwinex/
SignalStart : 2-3 %/mois, DD ≤ 15 %). **Mais les vidéos de *produit* portent
les promesses standard du secteur** : Powerhouse « 6 à 10 % par mois »
(`07 @ 03:00`), « 6 %/mois sur 7 ans transforme 10 k en 1,3 M — si vous trouvez
ça insuffisant vous êtes fous » (`07 @ 06:30`), Vigorous « 5 000 $ → 27 M$ en
20 ans de backtest » (`11 @ 01:00`), défi « 1 000 $ → 400 000 $ en 6-8 ans »
(`15 @ 00:00`) — ce dernier exige ~5 %/mois soutenus 8 ans, soit 2× la borne
d'excellence mondiale pendant 8 ans. La sobriété est la marque
(« Responsible ») ; les produits vendent l'ordinaire du secteur.

**Le fait le plus précieux du corpus, documenté par lui-même** : le compte
Ranger + Comeback Kid a vécu un **drawdown de 78 %** (mai 2021, AUDCAD,
`15 @ 01:00`, ré-admis `06 @ 02:30` et `14 @ 03:00`) alors que ses backtests
20 ans en tick data « 99,9 % modeling quality » affichaient **11,33 %**
(`01 @ 02:00`) à **16 %** (`03 @ 06:30`) de DD maximal. **Facteur 5 à 7 entre
le risque modélisé et le risque vécu, en moins d'un an de live.** C'est le
point de calibrage backtest→live sur la famille grid que personne d'autre du
corpus ne fournit — et il invalide sa propre méthode de calibration (§2.3).

**Cohérence interne des chiffres (le test fxalexg)** : le noyau vécu est
plutôt cohérent — 16 k$ atteints avec 1 000 $ + 200 $/mois sur 3 ans implique
~3 %/mois, et il dit « pas même 3 % » (`16 @ 00:00`) ; « moyenne 3,4 %/mois
sur 2 ans » (`14 @ 02:00`) est du même ordre. **Mais l'habillage gonfle** :
« 450 % d'augmentation » sur un compte dont ~60 % du solde vient des dépôts
mensuels (`15 @ 00:30` : 1 200 → 5 523 $ en 17 mois avec 200 $/mois ≈ 3 400 $
déposés — le gain de trading réel est ~1 000-1 900 $, soit 2-3 %/mois) ; et
dans la même vidéo « 5 à 10 % par mois, ce que j'atteins » côtoie « moyenne
3,4 % » (`14 @ 02:00`). Sur le drawdown, il choisit systématiquement le chiffre
bas : Myfxbook 11,4 % vs relevé MT5 4,29 % → il retient 4,29 (`03 @ 00:30`).

**Preuves tierces** : comptes « publics, mis à jour toutes les 5 minutes »
revendiqués (`02 @ 00:00`, `10 @ 02:00`), Myfxbook/FXBlue cités — aucun lien
dans nos transcripts, invérifiable pour nous. Son compte prop MyForexFunds
300 k$ a disparu avec la fermeture de la firme en sept. 2023, avant le premier
payout (`14 @ 00:00`) — événement externe réel qui, ironiquement, illustre ses
propres mises en garde. Deuxième praticien du corpus (après Balke) à documenter
ses pertes : « −27 % en trading manuel » (`03 @ 05:30`), le DD 78 %, les mois
perdants de 2023 (`14 @ 01:00`).

---

## 1. Tableau récapitulatif — trié par valeur décroissante

| # | Élément | Case | Source | Valeur |
|---|---|---|---|---|
| A1 | **Point de calibrage risque grid** : MDD modélisé 11-16 % (20 ans, tick 99,9 %) → **78 % vécu en <1 an**. Facteur 5-7 sur LA métrique de risque | **À ADOPTER** (donnée de calibrage, pas une méthode) | `01,03,06,15` | ★★★★★ |
| T1 | **Espérance par entrée des entrées d'appoint grid** (le seul primitif falsifiable de la famille — §2.5) | **À TESTER** — étude bornée, harnais existant, PAS un s94 EA | `01,02,13,15` | ★★★★☆ |
| A2 | Conformance backtest↔live **chiffrée en agrégat** : ~5-10 % d'écart (trades, profit, DD) sur 6 mois / ~1 500 trades | **À ADOPTER** comme ordre de grandeur attendu pour R5 (le principe = déjà Balke A1) | `05` | ★★★☆☆ |
| A3 | Latence d'exécution 100-200 ms dans le strategy tester MT5 (« zero latency... useless ») | **À ADOPTER** (validation future EA MQL5, complète Balke A2) | `04 @ 11:00` | ★★☆☆☆ |
| A4 | Réflexe d'analyse : **inflation par dépôts** — equity curve gonflée par 200 $/mois présentée comme performance | **À ADOPTER** (checklist d'évaluation de source) | `15,16` | ★★☆☆☆ |
| D1 | 2-3 %/mois comme réalisme long terme ; >10 %/mois insoutenable | DÉJÀ FAIT — METHODOLOGY §10, 3e source concordante | `12` | — |
| D2 | Coûts (spread/swap/commission) toujours inclus au backtest | DÉJÀ FAIT (§3.2) — il le prêche, nous le mesurons | `06 @ 10:00` | — |
| D3 | 12 mois de démo forward avant le live | DÉJÀ FAIT — c'est notre R10 (PAPER obligatoire) | `06 @ 02:00` | — |
| D4 | Données longues, tous régimes, pas de filtre news | DÉJÀ FAIT en intention — notre limite est inverse (5,1 ans, §9) | `06 @ 11:00` | — |
| R1 | **Grid/martingale comme famille à reproduire en EA** | **À REJETER** — §2.4 : espérance réductible au per-entry, queue non bornable sur nos données, incompatible R2/R3/moteur | `01-03` | — |
| R2 | Calibration martingale sur les quantiles de queue **in-sample** (« combien de niveaux dans les 20 dernières années ») | **À REJETER** — c'est estimer le pire cas sur l'échantillon qui ne le contient pas ; le 78 % live est la sanction | `02 @ 04:30` | — |
| R3 | Scalping M1 2-3 pips (Crackerjack 78 % WR, Vigorous) | **À REJETER** chez nous — péage rédhibitoire + M1 non validable (§4) | `10,11` | — |
| R4 | « Plus de trades dans le backtest = meilleure adaptabilité future » ; « si votre backtest ne ressemble pas à ça, vos données sont mauvaises » | **À REJETER** — confond effectif et robustesse ; prend le résultat attendu comme critère de validité des données | `04 @ 18:30, 19:30` | — |
| R5 | « Every tick » synthétique préféré à « every tick based on real ticks » | **À REJETER** tel quel — contredit frontalement Balke (`09` Balke) ; sa raison (le réel n'est pas parfait) justifie la latence, pas le mode dégradé | `04 @ 11:30` | — |
| R6 | Powerhouse 6-10 %/mois ; 1 000 $ → 400 000 $ ; 5 k → 27 M backtest | **À REJETER** — contredit sa propre doctrine `12` et le calibre §10 | `07,11,15` | — |
| R7 | Stack trend `13` (ADX + SuperTrend + Aroon + engulfing + pivots) | **CLASSÉ SANS SUITE** — trend-pullback standard, famille mesurée morte chez nous ; le différenciateur est le grid, traité en T1/R1 | `13` | — |
| R8 | Hybride manuel + algo pour échapper à la détection copy-trading des prop firms | **À REJETER** — contournement de règles d'un tiers, hors de notre problème | `03 @ 05:00` | — |

---

## 2. Sujet 1 — Le grid trading (fichiers 01, 02, 03 + 13, 15)

### 2.1 Ses règles exactes de grid « responsable », reconstituées

| Composant | Règle | Source |
|---|---|---|
| Signal initial | Pullback dans une tendance forte : double filtre **ADX weekly + SuperTrend** (`01`), version détaillée `13` : ADX (TF supérieur) + SuperTrend (TF inférieur) + oscillateur **Aroon** pour le pullback + pattern de bougie (inside/engulfing, indicateur « ENG » propriétaire) dans le nuage Aroon | `01 @ 02:30`, `13 @ 02:00` |
| Espacement | **Grille ATR** (« flex... based on what the pair is doing »), ancrée sur les **pivots S/R journaliers** (3 niveaux support / 3 résistance recalculés chaque jour), tolérance 20-30 pips autour du 1er niveau | `13 @ 03:30-04:30`, `03 @ 03:00` |
| Multiplicateur | Ranger AUDCAD : **×1,5 tous les 3 ordres** (0.01/0.01/0.01/0.02...) ; Comeback Kid : légère progression **tous les 2 ordres** ; Ranger GBPCAD : **aucune martingale** (« it didn't make sense... when running back tests of 10 plus years ») | `02 @ 08:00-09:30`, `15 @ 09:30` |
| Plafond de niveaux | **Aucun plafond dur énoncé.** Observé : 5-8 ordres typiques (`15`), et il admet que les baskets GBPCAD montent « à 20 ou 30 trades au pire » dans le backtest 14 ans | `15 @ 06:30` |
| Take profit | Basket TP commun 20-30 pips (`03 @ 02:00`), scalp 3 pips sur les variantes M1 ; « cross-pair take profit » : le TP en % de balance ferme les baskets de plusieurs paires ensemble (Powerhouse) | `03`, `07 @ 07:00` |
| Coupure | **Equity stop, pas de SL par trade** : « equity stop losses instead of hard stop losses on each trade » ; sur son compte 33 k$ : **15 % de DD maximum, « I will cut trades if that takes place »**, récupération estimée en 3-4 mois | `01 @ 01:30, 08:30` |
| Sizing | 0.01 lot / 5 000 $ avec auto-compounding dans le backtest | `06 @ 08:00` |
| Ordre de grandeur du risque déclaré | « 5 ordres ≈ 0,5 % de drawdown » (`01 @ 03:30`) ; 5 trades ≈ 1-1,5 %, 8 trades ≈ 2 % (`15 @ 04:00, 08:00`) | |

### 2.2 Sa réponse au risque de queue : chiffrée, mais auto-invalidée

Il **a** une réponse chiffrée — c'est plus que la moyenne du secteur — et elle
tient en deux pièces :

1. **L'equity stop 15 %** (`01 @ 08:30`). C'est un vrai chiffre, écrit avant.
   Mais : (a) son propre compte-vitrine a vécu **78 %** sans être coupé — la
   règle des 15 % vaut pour le compte 33 k$, pas pour le compte du défi, et le
   78 % a été géré par... des dépôts mensuels qui rediluent le DD (`06 @ 02:30`,
   `14 @ 03:00`) ; (b) en 2023 il « accepte » un SL de 30 % en high risk
   (`14 @ 01:30`) puis re-optimise tout à 5 % pour les prop firms
   (`09 @ 01:30`). Le seuil suit les circonstances — c'est une préférence, pas
   un contrat.
2. **La calibration du multiplicateur sur l'historique** : « combien de
   niveaux la stratégie a-t-elle atteints dans les 20 dernières années ? »
   (`02 @ 04:30`). **C'est le défaut structurel** : estimer le quantile de
   queue sur l'échantillon, puis dimensionner la progression pour survivre à
   ce quantile. Par construction, l'échantillon ne contient pas la queue qui
   vous tue (sinon la config n'aurait pas été retenue). Le 78 % de mai 2021 —
   sur une paire calibrée ainsi — est arrivé **pendant** la période où le
   backtest 20 ans disait 11-16 %. Sa propre phrase de 2023 le reconnaît :
   « a strategy will break eventually whether it's now or two years from now »
   (`09 @ 01:00`), suivie d'une ré-optimisation post-douleur — le cycle
   Balke-GBPUSD, en version grid.

### 2.3 Le problème structurel, posé proprement

Un basket grid à TP commun est une somme de sous-positions entry_i → sortie
commune. **Son espérance est la somme des espérances par entrée, et chaque
entrée paie le spread plein.** Le grid ne crée pas d'edge : il redistribue
*quand* les pertes se réalisent — beaucoup de petits gains (WR de basket très
haut), et la perte concentrée dans les rares baskets qui atteignent l'equity
stop. C'est la skewness négative par construction. Conséquences :

- **Le WR et le « R par trade » de basket sont ininterprétables.** Son
  « profit tous les mois pendant 2 ans » (`03 @ 00:00`) est exactement ce
  qu'une martingale d'espérance négative produit entre deux accidents.
- **Un track record court ne prouve rien** : si P(accident/an) = 20 %, la
  moitié des fenêtres de 3 ans sont propres. Son propre historique le montre :
  2 ans lisses à 2 %/mois (`03`), ET un 78 % l'année d'avant sur la même
  famille (`15`).
- **Le backtest long ne protège pas** : le sien avait 20 ans de tick data
  99,9 % et un DD modélisé 5-7× trop faible. Le tueur est le régime absent de
  l'échantillon, pas la qualité des ticks.

### 2.4 Pourquoi PAS de reproduction s94 en EA

1. **Incompatibilité plateforme** : le grid exige plusieurs positions
   simultanées par instrument (moteur épisodique : position unique,
   `engine.py`), un sizing progressif DANS la logique (violation R2), pas de
   stop par trade (violation R3), un equity stop au niveau compte (couche
   `core/risk/`, pas stratégie). Tester « fidèlement » exige une évolution
   majeure de `core/` — un mur bien plus large que le `max_hold_bars` de s09.
2. **Nos données ne peuvent pas borner la queue** : 5,1 ans, un seul régime
   (METHODOLOGY §9). Même un EV mesuré positif laisserait le risque de ruine
   NON CONCLUSIF *a priori* — et c'est le risque, pas l'EV, qui est la question
   du grid. Un test qui ne peut pas trancher sa question centrale ne vaut pas
   son coût d'infrastructure.
3. **La partie falsifiable est atteignable sans la machinerie** (§2.5).

### 2.5 Le protocole honnête — le primitif per-entry (T1)

**Hypothèse réduite** : « entrer en sens contraire d'une excursion adverse,
aux niveaux de pivots journaliers / espacement ATR, pendant une tendance
supérieure, a une espérance positive par entrée nette de spread. » C'est tout
ce que le grid a le droit de revendiquer — le reste est de la redistribution.

Dispositif (étude bornée type `studies/`, harnais épisodique existant,
décision Adrian — rien n'est implémenté) :

| Pièce | Contenu |
|---|---|
| Trades | Chaque entrée d'appoint traitée comme un trade individuel : entrée au niveau grid_i, sortie au basket-TP équivalent (20-30 pips) OU au temps, spread aux deux bouts |
| F1 — témoin mesuré | `attach_control_arm`, 200 tirages à dispositif identique (mêmes heures, mêmes distances, même effectif). Si percentile < 95 : **famille close**, sans appel |
| F2 — long/short | 2021-2026 en tendance : le « avec la tendance » de son filtre est le candidat beta évident (leçon s01/s09) |
| F3 — décomposition par rang | espérance de l'entrée n°1 vs n°2 vs n°3+ : si seule la n°1 (le signal trend-pullback) porte quelque chose, le grid n'ajoute rien ; si les n°2+ portent, c'est le motif « fade de l'échec » — 4e apparition (s91, s09 §2.7, s10) |
| F4 — économie a priori | AVANT de coder : drag = spread / distance de TP. À 20-30 pips de cible EURUSD, drag ≈ 4-7 % ; à 3 pips (variantes scalp), 30-60 % — les variantes scalp sont éliminées sur papier |
| Effectif | ≥ 20 trades OOS médians, sinon NON CONCLUSIF |

**Ce que ça tranche** : per-entry ≤ témoin → toute la famille grid est close
chez nous pour le prix d'une étude d'un jour, sans toucher `core/`. Per-entry
> témoin → alors seulement la discussion « évolution moteur multi-positions »
mérite d'exister, avec le point A1 (facteur 5-7 sur le DD) comme borne de
méfiance sur tout backtest de la couche basket.

---

## 3. Sujet 2 — Sa méthodologie de backtest (04, 05, 06)

### 3.1 Ce qu'il a et que nous n'avons pas (état honnête)

| Chez lui | Chez nous | Verdict |
|---|---|---|
| Tick data Dukascopy 20 ans, import symbole custom MT5, « 99,9 % modeling quality » (`04 @ 03:30-10:00`) | Barres H1 Swissquote 5,1 ans, M5 ~16 mois | Réel avantage de profondeur — mais §0/A1 démontre que ça n'a pas protégé son estimation de risque. Notre faiblesse n°1 (un seul régime) reste vraie et il ne nous apprend pas à la lever gratuitement |
| **Latence simulée 100-200 ms**, jamais 0 (`04 @ 11:00`) | Pas de modèle de latence (slippage chiffré en sensibilité, s91 §2.10) | **A3 — à retenir** pour la validation de l'EA MQL5 dans le tester |
| Auto-compounding du lot dans le backtest (`06 @ 08:00`) | Hors sujet — nous mesurons en R, le sizing est R2 (couche risque) | Notre séparation est supérieure |
| GMT+2, offset déclaré à l'import (`04 @ 07:00`) | Fuseau calibré par s09 (GMT+3 IC) | Même piège, déjà documenté (s09 §6.6) |
| « Every tick » synthétique préféré à « real ticks » car « ce n'est pas comme ça que l'exécution broker marche » (`04 @ 11:30`) | Modèle barre pessimiste (stop prioritaire) | **Contradiction frontale avec Balke** (`09` Balke : real ticks obligatoires avec SL serrés). Balke a raison sur le fond : le mode dégradé n'est pas « plus réaliste », il est plus flou. Le vrai contenu de son intuition — l'exécution parfaite n'existe pas — se traite par la latence et le slippage, pas en dégradant les données |
| « Si votre backtest ne ressemble pas au mien, vos données sont mauvaises » (`04 @ 19:30`) | — | Inversion épistémique remarquable : le résultat attendu devient le critère de validité des données. À rejeter, et à retenir comme signature d'auto-confirmation |

**Ce qu'il n'a pas, nulle part dans 133 k caractères** : hors-échantillon,
walk-forward, témoin, effectif critique, correction du multiple testing —
**250 algorithmes construits** (`06 @ 04:30`), les vidéos montrent les
survivants. Le dénominateur est pire que chez Balke (200+). Sa ré-optimisation
2023 (`09 @ 00:00` : « optimize for the past but also for what you think is
going to be seen in the future ») est du look-ahead par itérations vécues.

### 3.2 L'écart backtest→live — la donnée rare, et sa double face

- **Face conforme** (`05`) : Sharpshooter, juin-déc 2022, backtest rejoué sur
  la période live exacte : écart ~10 % sur le nombre de trades (1 528 vs
  1 335, dont une semaine de données manquante), ~5 % sur le profit (24,16 %
  vs 25,4 %), ~0,5 pt sur le DD (17,44 vs 17 %) (`05 @ 03:00-05:00`). C'est le
  geste R5, fait sérieusement, en agrégat. **Ordre de grandeur à retenir pour
  notre conformance : un EA scalping bien modélisé colle à ~5-10 % en agrégat
  sur 6 mois.** Réserve : c'est l'EA qui a marché qui a eu sa vidéo
  (survivorship au niveau du choix de l'exemple), et l'agrégat n'est pas
  l'appariement trade par trade que notre R5 visera.
- **Face non conforme** (A1) : sur la famille grid, le même praticien avec les
  mêmes données mesure 11-16 % de DD et en vit 78 %. **La conformance agrégée
  sur 6 mois calmes ne valide pas la queue.** Les deux faces ensemble donnent
  la leçon complète : R5 valide le *modèle d'exécution*, jamais le *modèle de
  risque* — il faut les deux, et le second n'est validable que par un régime
  adverse ou un témoin structurel.

---

## 4. Sujet 3 — Powerhouse (07, 09) et les scalpeurs M1 (10, 11)

### 4.1 Powerhouse : non reproductible, et auto-contredit

Le Powerhouse est un **bundle** de 4 puis 7 stratégies (Comeback Kid trend,
Ranger range, Vigorous + Gopher scalp) sur un compte (`07 @ 02:30-08:00`).
Aucune des jambes n'est spécifiée au niveau règles dans ces fichiers — pas
reproductible. Les seuls contenus notables :
- « Cross-pair / cross-strategy take profit » (`07 @ 07:00-09:00`) : fermer
  toutes les jambes quand un TP en % de balance est atteint. C'est un
  couplage risque/signal que notre R2/R8 interdit par design — et sa
  justification (« les trades ferment plus vite donc moins de DD ») confond
  vitesse de réalisation et espérance.
- Le claim « 6-10 %/mois » (`07 @ 03:00`) contredit sa propre doctrine `12`
  (2-3 %) publiée **un mois avant** (janv. vs févr. 2022). La mission parlait
  de « 2,66 %/mois sur 3 ans » — ce chiffre n'apparaît dans aucun des 15
  fichiers ; ce qui s'en approche est le « 2 %/mois » du Comeback Kid
  (`03 @ 00:00`) et le « 3,4 %/mois de moyenne sur 2 ans » (`14 @ 02:00`).
- `09` (2023) est la vidéo la plus honnête du lot : « 2023, l'année la plus
  dure de mes 20 ans », abandon de l'objectif « courbe qui ne perd jamais »,
  optimisation pour « finir l'année positif avec des mois perdants », SL 5 %
  pour les prop challenges avec « 85-90 % de chances de passer »
  (`09 @ 00:00-02:00`). Traduction dans nos termes : ses optima 20 ans ont
  cassé en live et il a re-calibré après coup — la confirmation vécue de R2/R3
  (notre tableau §1), pas une méthode.

### 4.2 Scalpeurs M1 : le mur des coûts, jamais franchi ni même chiffré

- **Crackerjack** (`10`) : 7+ bougies M1 consécutives (impulsion 7-10 min) →
  fade pour **2-3 pips** de TP, filtre ADX, long avec la tendance, 2e entrée
  grid 8-10 pips plus loin, **78 % de WR revendiqué sur la 1re entrée**,
  24 243 trades sur 20 ans (`10 @ 01:00-04:30`).
- **Vigorous** (`11`) : RMI (croisement niveau 30) + filtre MAMA/FAMA H4,
  3-5 pips de cible, 10-15 trades/jour, backtest 5 k → 27 M$ / 119 000
  trades / DD pic 44 % (`11 @ 01:00-04:00`) ; live revendiqué : 47 % en
  ~2 ans, soit ~1,6 %/mois (`11 @ 00:30`) — **le live fait 1/30e du rythme du
  backtest**, écart qu'il ne commente jamais.
- **Que dit-il des coûts ?** Presque rien de quantifié. Le seul chiffre du
  corpus : une cible de 3 pips qui ferme à 3,4 pips « incluant spread, swap et
  commission » (`06 @ 09:30-10:30`) — soit **~13 % de la cible en frais, sur
  le trade qu'il choisit de montrer**. Aucun calcul de seuil de rentabilité,
  aucun slippage chiffré, aucune mention du spread variable des news (il
  trade sans filtre news, `06 @ 11:00`). Notre péage mesuré : drag médian
  8,57 % en **H1** (METHODOLOGY §2) ; à cible 2-3 pips sur EURUSD avec
  0,6-1,2 pip de spread retail, le drag est de **30-60 % de la cible** — un
  ordre de grandeur au-dessus de tout ce que nous avons jamais accepté de
  tester. Et le signal d'alarme demandé par la mission est complet : TP
  minuscule + WR 78 % + grid d'appoint = petits gains réguliers, queue à
  gauche — le profil s05 (70-80 % annoncés, 26,6 % mesurés) en pire.
- **Verdict chez nous** : non testable de toute façon — pas de M1, M5 limité à
  ~16 mois (METHODOLOGY §9). Rejet sur l'économie a priori, pas besoin de
  données : la règle « si la marge attendue est inférieure au péage,
  reconcevez » élimine la classe entière.

---

## 5. Sujet 4 — Le réalisme économique (12, 14, 15, 16)

Les chiffres réels documentés, dépôts déduits :

| Donnée | Valeur | Source | Cohérence |
|---|---|---|---|
| Doctrine | 2-3 %/mois = le vrai plafond durable ; >10 %/mois meurt en ~3 mois, au mieux ~1 an | `12 @ 03:30-06:00` | **Concorde avec §10** (Darwinex/SignalStart) — 3e source indépendante |
| Compte 2 ans | 93 % de profit, moyenne 3,4 %/mois, pertes mars et juin 2023, « l'an dernier 60 % » | `14 @ 01:00-02:00` | Interne : OK (moyenne vs composé) ; « 5-10 %/mois que j'atteins » dans la même vidéo : tension non résolue |
| Compte défi 3 ans | 1 000 $ + 200 $/mois → 16 k$, « pas même 3 % de moyenne » | `16 @ 00:00` | **Calculé : ~3 %/mois — cohérent avec sa phrase** |
| Compte défi 17 mois | 1 200 → 5 523 $ **avec** 200 $/mois — titré « 450 % » | `15 @ 00:30` | Gain de trading réel ~2-3 %/mois ; le titre est de l'inflation par dépôts (A4) |
| Drawdowns vécus | **78 %** (2021), SL 30 % « acceptable » (2023), re-calibré 5 % (prop, fin 2023) | `15,14,09` | **Ne concorde PAS avec l'enveloppe élite** (DD ≤ 15 %) : le rendement est dans la norme, le risque est 2-5× dehors — et c'est exactement la signature grid (le rendement régulier est payé en queue) |
| Cible du défi | 400 000 $ en 6-8 ans depuis 1 000 $ | `15 @ 00:00` | Exige ~5 %/mois pendant 8 ans = 2× la borne §10 tenue 4× plus longtemps que les meilleurs comptes vérifiés. Invraisemblable par notre calibre |

**Synthèse** : la partie vécue et vérifiable-en-interne de ses comptes tombe
sur 2-3,4 %/mois — précisément notre borne §10, ce qui la consolide. Tout ce
qui dépasse (6-10 %, 400 k$, 27 M$) est du backtest ou de la projection. La
leçon spécifique grid : **un rendement mensuel « dans la norme » ne suffit pas
à valider — il faut l'enveloppe complète rendement ET drawdown.** Ses 2-3 %
sont achetés avec des excursions à 78 %.

---

## 6. Sujet 5 — La tendance long terme (13)

Le « best long term trend trading system » est le Comeback Kid côté signal :
double filtre ADX (TF haut) + SuperTrend (TF bas), pullback détecté à l'Aroon,
entrée sur inside/engulfing dans le nuage, pivots S/R journaliers, **grille
ATR en secours si le trade part contre** (`13 @ 01:30-04:30`). Résultats
montrés : 46,92 % sur 2 ans, DD 4,29 % (`13 @ 00:00`) — le DD choisi est le
relevé bas de `03 @ 00:30`, et la période exclut 2021 (le 78 %).

**Structurellement, rien de neuf** : c'est du trend-pullback-continuation à
indicateurs standard — la famille que nous avons mesurée morte trois fois
(s04 trendcore, s11 breakout, `trend_core_50y`). La seule différence
structurelle avec ce que nous avons testé n'est pas dans le signal mais dans
le **rattrapage grid** — c'est-à-dire le sujet §2 : quand le signal trend a
tort, il moyenne au lieu de couper. Autrement dit sa « stratégie trend qui
marche » = signal trend (mesuré mort) + redistribution de pertes (mesurable
par T1). **Classé sans suite** en tant que stratégie trend ; absorbé par T1
pour la seule composante originale.

---

## 7. Concordances et contradictions avec nos mesures

1. **C1 — Le calibre 2-3 %/mois** : troisième source concordante avec
   METHODOLOGY §10 (après Darwinex/SignalStart), et la première qui le dit
   depuis l'intérieur du marketing EA. Renforce la borne.
2. **C2 — WR élevé annoncé vs mesuré** : son 78 % (M1, cible 2-3 pips) est le
   même motif que s05 (70-80 % annoncés → 26,6 % mesurés chez nous sur
   structure comparable). Non testé ici (pas de M1), mais le péage mesuré
   (2,14 pts de WR en H1, pire en dessous) rend le franchissement du seuil de
   rentabilité par un scalp M1 retail invraisemblable a priori.
3. **C3 — Backtest→live** : sa conformance agrégée à ~5-10 % (`05`) corrobore
   le geste Balke A1 et donne un ordre de grandeur cible à notre futur R5. Son
   contre-exemple grid (DD ×5-7) borne ce que la conformance peut promettre.
4. **C4 — Contradiction interne au corpus sources** : mode « every tick »
   synthétique (lui) vs « real ticks » obligatoires (Balke `09`). Nous
   tranchons côté Balke, en ajoutant sa latence 100-200 ms (A3).
5. **C5 — Le motif « fade de l'échec »** : sa 2e entrée grid (entrer après
   8-10 pips adverses) est structurellement le trade de retournement s09 §2.7
   et le résidu s91. T1/F3 en fait la 4e mesure indépendante du même motif —
   c'est la seule raison scientifique (au-delà de la clôture de famille) de
   faire l'étude.

---

## 8. Les angles morts de la source — nos risques si on copie

1. **Zéro hors-échantillon dans 133 k caractères.** Pas un walk-forward, pas
   un hold-out. L'optimisation est plein échantillon, la validation est « le
   live » — et le live a rendu 78 %.
2. **Multiple testing invisible** : 250 algos construits (`06 @ 04:30`), 4-7
   survivants commercialisés. Les vidéos « best strategy » sont le filtre.
3. **Le survivorship s'applique aussi à la conformance** : `05` montre l'EA
   qui colle ; rien sur ceux qui ne collaient pas.
4. **Chiffres de risque à géométrie variable** : 11,4 vs 4,29 (il prend 4,29),
   15 % « maximum » vs 78 % vécu, 30 % « acceptable » vs 5 % prop. Aucun
   chiffre de DD de cette source n'est utilisable sans sa provenance exacte.
5. **Inflation par dépôts** dans les courbes de « croissance » (`15`, `16`) —
   divulguée dans le texte, gommée dans les titres.
6. **L'exécution M1 n'est jamais coûtée** : ni slippage, ni spread news, ni
   commission par lot dans les vidéos scalp — le seul chiffre (13 % de la
   cible, `06`) vient d'une vidéo générique et d'un trade choisi.
7. **Éthique périphérique** : le contournement de la détection copy-trading
   des prop firms est présenté comme un argument produit (`03 @ 05:00`). À
   connaître pour calibrer la confiance globale dans le personnage.

---

## 9. Recommandation finale — LA chose à faire

**Ne pas ouvrir de dossier s94 « grid » en EA.** La reproduction fidèle exige
une évolution majeure du moteur (multi-positions, equity stop, sizing
progressif = R2/R3 cassés) pour tester une famille dont la question centrale —
la queue — n'est **pas bornable** sur 5,1 ans mono-régime, et dont le propre
auteur fournit la falsification vécue : DD modélisé 11-16 % sur 20 ans de tick
data → 78 % réalisé en moins d'un an (A1).

**LA chose à faire, si Adrian veut une action** : l'étude bornée T1
(« per-entry ») — un jour de calcul, harnais existant, zéro modification de
`core/` : espérance par entrée des entrées d'appoint grid (pivots journaliers,
espacement ATR, avec-tendance) contre témoin mesuré, avec décomposition par
rang d'entrée et contrôle long/short. Deux issues, toutes deux utiles :
- percentile < 95 → **la famille grid est close chez nous, définitivement et
  pour trois ordres de grandeur moins cher que l'alternative** ;
- percentile ≥ 95 → le signal vit dans les entrées d'appoint (4e apparition du
  motif « fade de l'échec », après s91, s09 §2.7 et s10) — et c'est ce
  motif-là, pas le packaging grid, qui mérite alors la discussion s90.

À défaut d'étude : classer sans suite, et verser au dossier commun les deux
seuls acquis fermes — le point de calibrage A1 (un backtest grid sous-estime
le risque d'un facteur 5-7, cas documenté) et la confirmation C1 du calibre
2-3 %/mois par une troisième source indépendante.

---

## Addendum — balayage complet (fichiers 17-36)

> **Date** : 2026-08-16. Dépouillement des fichiers ajoutés après la synthèse
> initiale (01-16). **Aucun fichier hors ce dossier n'a été modifié.**

**EN TÊTE — impact sur la reco finale : la reco per-entry (§9, T1) est
INCHANGÉE.** Rien dans les 20 nouveaux fichiers n'invalide le protocole ni
n'exige de le modifier. Trois apports mineurs pour l'étude en cours
(`studies/grid_per_entry/`) sont listés en §A6 — des paramètres de source
supplémentaires, pas des changements de dispositif.

### A0. État réel du corpus ajouté — 4 anomalies d'inventaire

1. **Doublons octet-pour-octet** : `25` ≡ `15` (journey ep11) et `33` ≡ `14`
   (20k→63k). Zéro contenu nouveau — déjà dépouillés dans la synthèse.
2. **Fichier absent** : `28` n'existe pas dans le dossier (comme le `08`).
3. **Fichier inexploitable** : `27` (journey ep9, 2021-09-24) — sous-titres
   automatiques totalement corrompus (bruit : « Yandex Market », « La Quinta
   Inn », `27 @ 00:00-09:30`). Aucune donnée comptable récupérable.
4. **Contamination par d'autres chaînes** — 3 fichiers ne sont PAS de
   Responsible Forex Trading :
   - `17` et `18` (2025-11) : auteur germanophone anonyme, comptes en **€**,
     « range breakout EA », morning range USDJPY 3-6 h, qui **promeut le
     trade manager MQL5 d'un tiers** (« I know the developer of the program
     personally », `17 @ 10:30`). RFT est un trader US ($, TradersWay/Oanda,
     vend ses propres EAs).
   - `21` (2025-01) : chaîne **crypto** (« Signum », TradingView, narrateur
     « Michel », `21 @ 02:30`) — Bitcoin/altcoins, pas du forex.
   Ces 3 fichiers sont traités ci-dessous mais **leurs claims ne disent rien
   de RFT** (et réciproquement) ; la question chronologique « avant/après son
   crash » ne s'applique qu'aux fichiers RFT.

Bilan net : sur 20 fichiers ajoutés, **14 sont du contenu RFT nouveau et
exploitable** (19, 20, 22, 23, 24, 26, 29, 30, 31, 32, 34, 35, 36 + le titre
de 25/33 pour la chronologie), 3 sont d'autres chaînes, 2 des doublons, 1 du
bruit.

### A1. Tableau 4 cases des nouveautés

| # | Élément | Case | Source |
|---|---|---|---|
| AD1 | **Comptabilité du journal $1000→$400k enfin fermée** : à 38 mois, ~53 % du solde vient des dépôts, et il a lui-même révisé la cible à ~215 k$@5 ans (§A2) | **À ADOPTER** (pièce comptable — confirme et chiffre A4) | `26,32` |
| AD2 | Datation précise du crash : DD 78 % le **4-7 juin 2021** (pas mai), AUDCAD, « older version of the Ranger » | **À ADOPTER** (précision sur A1 ; le fond ne change pas) | `32 @ 01:30`, `29 @ 03:30`, `26 @ 02:30` |
| AD3 | Checklist d'évaluation d'un EA du marché : modeling quality masquée = signal d'alarme ; reviews MQL5 falsifiables ; **compte vitrine sans aucun retrait en 4 ans** = compte publicitaire probable ; broker white-label = historique manipulable | **À ADOPTER** (hygiène d'évaluation de source, complète A4) | `30 @ 02:30-09:00` |
| AD4 | Mécanique réelle du « 100 % win rate » : 7 trades sur **2 jours** d'une semaine en cours (un mardi), en baskets grid ; les deux mécanismes suspectés (grid-pas-encore-perdant ET cherry-picking de fenêtre) sont présents simultanément | **À ADOPTER** (signature d'alarme confirmée, rien à tester) | `20 @ 02:00` |
| AD5 | Indicateur S/R : niveaux aux **corps de bougies** (open/close D1, pas les mèches), comptage des hits sur ~10 ans, épaisseur = significativité ; « cassé » = 2 clôtures H1 au-delà | **CLASSÉ SANS SUITE** avec fiche (§A4) — définition de niveau originale mais exploitation 100 % discrétionnaire + averaging | `23,24,22` |
| AD6 | Zone recovery (chaîne tierce) : hedge opposé à taille croissante, ici borné à 3 ordres, risque 500 € pour gagner 100 € | **À REJETER** (§A3 — martingale sur exposition nette + double péage ; dominée par un stop-and-reverse) | `17` |
| AD7 | Grid « swap positif » (chaîne tierce) : sélection des paires à swap positif + avec-tendance + SL au-dessus du dernier haut, échantillon **5 jours** | **À REJETER** (échantillon nul ; le seul contenu — le swap comme filtre de coût — est déjà couvert par D2/§3.2) | `18` |
| AD8 | « Rookie 81 % win » : l'assistante de RFT, **36 trades / 2 mois**, cible 10 pips/jour, 6,22 % en 2 mois (~2-3 %/mois) — argumentaire de vente de l'indicateur S/R | **À REJETER** comme preuve (effectif ridicule, tunnel de vente) ; noter que le rendement réel retombe sur 2-3 %/mois | `19 @ 01:30, 10:00` |
| AD9 | Ichimoku 4h (chaîne crypto) : BTC 4h, 35 % WR, DD 33 % (altcoins 43-91 %), long/flat alterné, réglages **non divulgués** (gated abonnement) | **CLASSÉ SANS SUITE** — crypto hors périmètre, règles non extractibles, backtest TradingView sans OOS | `21 @ 08:30-12:00` |
| AD10 | Pertes 2022 documentées : −28 % manuel en mai 2022 (10 % + 17 %), compte prop MFF 200 k$ **perdu par dépassement de 0,5 pt du daily-loss 5 %** (« miscalculation on the algorithm ») | **À ADOPTER** (pièce au dossier « le risque suit les circonstances » — §2.2) | `34 @ 00:30, 08:00` |
| AD11 | Serenity EA « moins de DD que le Comeback Kid » 2-4 %/mois ; Sharpshooter backtest 20 ans 3 k$→2,9 M$ | **À REJETER** — même famille de claims que R6 (backtest composé invraisemblable) | `23 @ 00:30`, `30 @ 05:30` |
| AD12 | Doctrine répétée : risque bas, 3-5 %/mois max, backtest ≥ 10 ans minimum | DÉJÀ FAIT — recoupe D1/D4 et §10 ; 4e redite interne | `36 @ 01:30, 03:30` |

### A2. La comptabilité du journal $1000→$400 000 (26, 32 ; 27 illisible, 25 doublon)

Épisodes exploitables et pièces comptables, en chronologie :

| Date | Pièce | Chiffres | Source |
|---|---|---|---|
| 2020-07-02 | Départ | 1 000 $, puis **+200 $/mois systématiques** | `26 @ 01:30`, `32 @ 00:00` |
| 2021-06-04/07 | Le crash | DD **78 %**, AUDCAD, « older version of the Ranger », trades coupés en perte (−30/35 %) | `32 @ 01:30`, `29 @ 03:30`, `34 @ 01:00` |
| 2021-10 (ep10, mois 16) | Solde 4 874 $ | Dépôts cumulés ≈ 4 000 $ (1 000 + 15×200) → **gain de trading réel ≈ 875 $ en 16 mois** (~1,2 %/mois sur le capital moyen). Il annonce « 38 % » de trading et le thumbnail affiche « 387 % » en fusionnant dépôts et gains — il l'admet à voix haute | `26 @ 01:00-01:30` |
| 2021-12 (ep11) | 1 200 → 5 523 $ | Déjà dépouillé (synthèse §0) : ~3 400 $ de dépôts dedans | `15 @ 00:30` |
| 2023-09 (mois 38) | Solde ~16 000 $ | Dépôts cumulés ≈ 8 600 $ → **profit de trading déclaré 7 478 $** ; ~53 % du solde vient des dépôts. Depuis le 8 juin 2021 : « 138 % de profit, 16 % de DD » | `32 @ 00:00-02:00` |
| 2023-09 | **Révision silencieuse de la cible** | Son propre calculateur à « 4 %/mois conservateur » donne 80-100 k$ à 3 ans et **215 k$ à 5 ans — « it's not four hundred thousand but the goal is to try to get as close as possible »** | `32 @ 01:00-01:30` |

**Verdict comptable** : le titre « $1000 to $400,000 » n'est **pas soutenu**
par sa propre comptabilité — (a) les courbes affichées mélangent
structurellement dépôts et gains (il le divulgue dans l'audio, jamais dans
les titres — le motif A4 exactement) ; (b) la trajectoire réelle à mi-course
(16 k$ à 3 ans, dont 8 600 $ déposés) exige, pour atteindre 400 k$ à 8 ans,
un rythme qu'il ne revendique même plus ; (c) lui-même a rétrogradé la cible
à ~215 k$@5 ans en 2023 sans le dire dans le titre de la série. Pas de trou
inexpliqué façon fxalexg en revanche : les dépôts sont réguliers et déclarés,
les pertes datées (fév. 2021, juin 2021, mai 2022, sept. 2022, 3 pertes
depuis mars 2023 `24 @ 03:00`) — c'est de l'inflation par habillage, pas de
la comptabilité truquée. Preuves tierces : toujours Myfxbook revendiqué,
toujours aucun lien vérifiable dans nos transcripts.

**Pertes annexes documentées (34, 35)** : mai 2022 −28 % en manuel (−10 %
puis −17 % « back-to-back », `34 @ 00:30`) ; compte prop MyForexFunds 200 k$
perdu en mai 2022 pour **0,5 point de dépassement du daily-loss 5 %**, par
« miscalculation on the algorithm » qui fermait les trades (`34 @ 08:00`) ;
sept. 2022 : 500 k$ de comptes prop « on the brink » (`35 @ 04:30`), nouvelle
perte manuelle le 15 sept. (`35 @ 02:00`). Le `35`, malgré son titre (« un
EA m'a mangé »), raconte l'inverse : ses algos tiennent, c'est son trading
manuel qui saigne — le titre est du packaging d'alarme, pas un contenu.

### A3. Verdict zone recovery (17) — et la taille de la position N

**Attribution d'abord** : le `17` n'est pas RFT (cf. A0) ; c'est une chaîne
tierce qui teste le mode « zone recovery » d'un trade manager commercial.

**Règles extraites** (tout ce que la vidéo donne — c'est peu) : zone = les
bornes d'un morning range (USDJPY 3-6 h, `17 @ 02:00`) ; à chaque traversée,
position **opposée** de « larger lot size » (multiplicateur jamais chiffré,
`17 @ 02:30`) ; sortie = gain fixe en € (100 €) OU **max order count = 3**,
auquel cas perte ~500 € (`17 @ 04:00`). Sa réponse au risque de queue est
donc **réellement bornée dans ce setup précis** (perte max définie 5:1) —
plus honnête que le grid RFT sans plafond — mais l'économie est celle d'un
profil 5 contre 1 : il faut **> 83,3 % de réussite** pour être à
l'équilibre, et l'échantillon montré est de **2 setups sur 1 jour**
(`17 @ 00:30`). Aucune espérance démontrée ni démontrable ici.

**La croissance géométrique demandée, chiffrée sur la mécanique générale**
(zone de largeur Z, TP à distance T au-delà de la borne opposée ; chaque
position N+1 doit couvrir les pertes accumulées + le gain cible G) :

    lot_{k+1} ≥ [ Σ pertes latentes (Z+T par lot opposé) − gains latents + G ] / T

Pour le paramétrage classique T = Z, la suite des lots est 1, 2, 3, 6, 12,
24… — **doublement à chaque retournement au-delà du 2e** ; après k
retournements, le lot courant ≈ 3·2^(k-2) et l'**exposition brute cumulée
≈ 2^k lots** (8 retournements ≈ 50+ lots pour 1 lot initial). Plus T est
serré relativement à Z, plus le facteur dépasse 2. C'est le multiplicateur
du grid RFT (×1,5/3 ordres) en pire, car :

1. **Le hedge ne réduit pas le risque, il le déguise** : un panier long L +
   short S est économiquement une position nette (S−L). Le zone recovery est
   donc une **martingale stop-and-reverse sur l'exposition nette**, à ceci
   près que toutes les jambes restent ouvertes — on paie le spread sur
   l'exposition **brute** (2^k) et le swap des deux côtés, pour un résultat
   net identique à fermer-et-retourner. Strictement dominé par l'équivalent
   sans hedge ; la question de queue est la même qu'au §2.2-2.3, avec un
   péage supérieur.
2. Le plafond « 3 ordres » du `17` rend la perte finie mais transforme le
   système en pari 5:1 sans edge identifié — la skewness négative de §2.3,
   version bornée.

**Conséquence pour nous : aucune étude dédiée.** Le primitif falsifiable du
zone recovery est le même que celui du grid — l'espérance par entrée du
retournement après excursion adverse — et il est **déjà couvert par T1/F3**
(le rang d'entrée n°2+ de l'étude per-entry mesure exactement « entrer en
sens opposé après k pips adverses »). Rien à ajouter au dispositif.

### A4. L'indicateur S/R (23, 22, 24, 31, 19) — fiche et classement

**Genèse datée** (utile au jugement) : déc. 2023 = « best month ever »
+27 %/~20 k$ en trading manuel discrétionnaire (`31 @ 00:00`) → il envoie la
vidéo à son développeur pour en faire un indicateur (`31 @ 04:00`) → sortie
janv. 2024 (`23`), campagne démo gratuite + interview de son assistante
(`19`), le tout **dans les 6 semaines suivant la main chaude**. En février,
la même stratégie fait « 2 % ce mois-ci » (`22 @ 20:00`) — la régression vers
2-3 %/mois est dans ses propres vidéos.

**Règles extractibles** (les voici, c'est la partie honnêtement originale) :

| Composant | Règle | Source |
|---|---|---|
| Définition du niveau | **Corps de bougies D1** (open/close), pas les mèches — « too much give between the body to the wick » ; un niveau = prix où ≥ 2 corps journaliers ont ouvert/clôturé | `24 @ 04:30-06:00` |
| Significativité | Comptage des hits sur ~10 ans (2000 barres D1) ; ligne épaisse/solide = beaucoup de hits, pointillée = 1-2 hits ; les paquets de lignes proches = « zones » | `23 @ 02:30-03:30` |
| Niveau cassé | **2 clôtures H1 consécutives au-delà** ; 1 clôture puis retour = niveau toujours actif | `22 @ 11:00`, `24 @ 06:30` |
| Momentum | Prix qui n'atteint PAS le niveau suivant = signal de continuation dans l'autre sens | `22 @ 13:30-14:00` |
| Exploitation | Discrétionnaire : blocs de 3-5 entrées à lot plat **en averaging** sur la zone, TP au pullback (10-15 pips près des news, 30-50 pips sinon) ; trade délibérément les pré-mouvements de news (NFP/FOMC) | `22 @ 12:30-13:00`, `24 @ 07:30-09:00` |

**Diffère-t-il structurellement de nos zones mortes (s01/s93) ?**
Partiellement : la définition corps-de-bougie + comptage décennal d'hits est
une vraie variante de construction (nos zones étaient bâties sur les
extrêmes/pivots). Mais (a) l'**exploitation** n'a aucune règle d'entrée/
sortie fermée — « your job is to anticipate how the news will affect it »
(`24 @ 10:30`) — donc rien d'implémentable fidèlement ; (b) le levier de
rendement revendiqué n'est pas le niveau, c'est **l'averaging en bloc**
(« that's the worst possible trade... then you can enter another sell sell
sell sell and you have a big massive profit », `22 @ 02:00`) — c'est-à-dire,
encore, le sujet §2, mesurable par T1 et par rien d'autre ; (c) les preuves
sont 6 semaines de main chaude + 36 trades de son assistante. **Classement
sans suite.** Si un jour la famille zone est rouverte (elle est close), la
définition corps-de-bougie serait la seule pièce à repêcher de cette fiche.

### A5. Confrontation aux conclusions initiales — le bilan explicite

1. **« 78 % live vs 11-16 % backtest » (A1) : INCHANGÉE, renforcée.** Trois
   ré-admissions supplémentaires et indépendantes du 78 % (`26 @ 02:00`,
   `29 @ 03:00-03:30`, `32 @ 01:30`), datation précisée (4-7 juin 2021 —
   la synthèse disait mai ; correction cosmétique, AUDCAD confirmé). Aucun
   nouveau fichier ne conteste le facteur 5-7.
2. **« Sobriété segmentée par le tunnel de vente » : INCHANGÉE, renforcée —
   et affinée.** Les nouveaux fichiers montrent que la segmentation passe
   **à l'intérieur des vidéos elles-mêmes** : le `20` titre « 100 % win
   rate » et prêche « 3-5 %/mois, préservation du capital » dans le corps
   (`20 @ 00:30`) ; le `32` projette « 4 %/mois conservateur » en
   contradiction avec sa doctrine 2-3 % (`12`) ; le `19` titre « 81 % win »
   pour un rendement réel de 2-3 %/mois (`19 @ 10:00`). Le titre est
   l'alarme, le corps est la couverture.
3. **« Reco étude per-entry » : INCHANGÉE.** Le zone recovery (A3) se réduit
   au même primitif (rang d'entrée n°2+, déjà F3) ; l'indicateur S/R (A4)
   confirme que l'averaging est le porteur de rendement revendiqué — ce qui
   est précisément l'hypothèse que T1 teste. Aucun protocole à modifier.
4. **Amendement mineur au §0 (à connaître, pas à réécrire)** : le corpus
   « Responsible Forex Trading » n'est pas homogène — 3 des fichiers ajoutés
   sont d'autres chaînes (A0). Les conclusions de la synthèse ne portent que
   sur les fichiers RFT ; c'était déjà le cas de fait (01-16 sont tous RFT).
5. **Chronologie 18/19 vs crash (question de la mission)** : le `18` n'est
   pas RFT (chaîne tierce, 2025) — la question ne s'applique pas ; le `19`
   (RFT, janv. 2024) est **2,5 ans APRÈS** le crash de juin 2021 : le
   pattern « repackager du high-win-rate après l'accident » est confirmé,
   avec le grid remplacé par le S/R + averaging dans le rôle du produit à
   haut WR.

### A6. Notes pour l'étude per-entry en cours (`studies/grid_per_entry/` — ne pas toucher, transmettre)

1. **TP de basket strict 30 pips sur le Ranger** (toutes tailles de basket,
   1 à 3 trades, `26 @ 05:30`) — la synthèse donnait « 20-30 pips » (`03`) ;
   30 est la valeur opérationnelle documentée la plus précise pour le
   paramètre « sortie au basket-TP équivalent » de T1.
2. **Distribution des rangs en régime calme** : oct. 2021 (rangy), 46 trades,
   80 % WR, baskets majoritairement de 1-3 trades, max 5 (`26 @ 04:30-08:30`)
   — utile comme ordre de grandeur attendu de la répartition n°1/n°2/n°3+ en
   marché favorable (F3) : l'essentiel de l'effectif sera au rang 1.
3. **Variante de niveau à ignorer sauf réouverture** : niveaux corps-de-
   bougie D1 avec comptage d'hits (A4) — alternative aux pivots journaliers
   de T1 ; ne PAS l'ajouter au dispositif (le protocole fige les pivots),
   simplement savoir qu'elle existe si un F5 exploratoire était un jour
   discuté.
4. Rappel de calibrage inchangé : tout DD backtest de la famille porte la
   borne de méfiance ×5-7 (A1).
