# ProRealAlgos (Carl Erickson) — dépouillement des 12 transcripts

> **Objet** : extraire ce qui consolide nos stratégies, notre backtester ou nos
> méthodes ; produire pour chaque stratégie une fiche testable OU un classement
> motivé. Rien d'autre.
> **Sources** : `docs/sources/prorealalgos/*.txt` — 12 transcripts, ~180 000
> caractères, sous-titres automatiques dédupliqués. Auteur unique : Carl
> Erickson, fondateur de ProRealAlgos (`12 @ 00:30`), ~20 ans de trading déclarés,
> 100 % algo depuis ~5 ans (`09 @ 03:00`).
> **Date** : 2026-08-17. **Aucun fichier hors ce dossier n'a été modifié.**
> Citations : `fichier @ mm:ss` (timestamps sous-titres, granularité 30 s).

---

## 0. Ce qu'il faut savoir avant de lire le détail

**Le modèle économique est la vente d'algos ProRealTime + affiliation broker IG**
(« there is a link to the broker that I use. They are called IG », `03 @ 13:00` ;
« I'm shamelessly going to advertise that I sell these algos », `09 @ 16:30` ;
affiliation assumée `10 @ 03:30`). Chaque backtest montré est un argument de
vente. Traité claim par claim.

**La particularité qui distingue cette source** : ils publient les **dates de
sortie** de leurs algos et prêchent l'évaluation **depuis la release** — « the
only thing that matters is how this algo has performed since it was released »
(`10 @ 10:00`), « a back test is never real and back tests can easily be
manipulated » (`10 @ 11:30`), « don't trust anyone telling you anything about
the historic performance of their ALGO, even if it's free » (`10 @ 13:00`).
C'est une doctrine saine — un backtest depuis la date de release d'un code
figé est un vrai forward-test — **avec l'angle mort du survivant** : ~30 algos
publiés sur leur blog (`10 @ 16:30`), et ce sont les survivants qui ont droit
aux vidéos. Aucun tableau « tous les algos publiés, morts inclus » dans les 12
transcripts. Le dénominateur N reste inconnu, donc « nos algos performent
depuis release » n'est pas interprétable — mais la doctrine, elle, est
réutilisable contre eux-mêmes (voir §5 et la note s12).

**Deux voix contradictoires chez le même auteur, à ne pas confondre** :
1. **Le pédagogue honnête** : « you don't build strong systems by optimizing,
   refining and forcing mediocre ideas » (`11 @ 01:30`) ; « I could make the
   worst looking idea get a good back test by adding filters » (`11 @ 02:00`) ;
   walk-forward prêché comme méthode obligatoire (`08`) ; seuils d'effectif
   minimum (≥ 100 trades/direction, `11 @ 10:30`) ; perte de 18 700 €
   documentée chiffres à l'appui (`09`).
2. **Le vendeur** : « ultimate algos » à profit factor 13,38 assumés « high
   risk of being overfitted » (`04 @ 34:30`) ; « code snippet that will turn
   any algo 200% better » paywallé (`12 @ 10:30`) ; optimisations de fenêtres
   horaires sur 2 ans de données présentées comme amélioration ×6 du drawdown
   (`06`) ; +12 000 € sur 30 000 € en 45 jours (~27 %/1,5 mois) donné comme
   performance de son portefeuille (`09 @ 16:00`) — 10× notre calibre externe
   (METHODOLOGY §10), invérifiable, n = 45 jours.

**Aucun traitement du multiple testing dans 180 000 caractères.** Le mot
n'existe pas, aucune p-value, aucun bras témoin, aucune correction. Le fichier
`04` (criblage 500 combinaisons) rapporte les *best-of* par marché sans jamais
poser la question du hasard. Leur seul garde-fou est un walk-forward (`08`)
jamais appliqué dans les vidéos de stratégies elles-mêmes.

---

## 1. Tableau récapitulatif — trié par valeur décroissante

| # | Élément | Case | Source | Valeur |
|---|---|---|---|---|
| P1 | **Précisions pour la session s12** : règles exactes du Daily MACD gratuit + date de release 2022-06-21 + borne OOS légitime (§2) | **À TRANSMETTRE** (session s12) | `10`, `05` | ★★★★★ |
| T1 | **Criblage `04` : le mean reversion RSI D1 sur indices est la meilleure entrée dans 6/10 cas** — 2e source indépendante concordante avec AI Pathways T1, renforce le test s12/T1 en cours | **À TESTER** (extension de grille du test D1 en cours, pas un nouveau projet) | `04` | ★★★★☆ |
| A1 | **Doctrine « évaluer depuis la release »** : pour toute source publiant des dates de release, la fenêtre post-release est le seul backtest opposable | **À ADOPTER** (checklist d'évaluation de sources + protocole s12) | `10 @ 09:30-13:30` | ★★★★☆ |
| T2 | **Quick flip scalper (03)** : fade de l'opening range M5 sur NASDAQ — économie a priori favorable sur indice, données marginales chez nous | **FICHE CONDITIONNELLE** (§3.3) | `03` | ★★★☆☆ |
| A2 | Heuristique walk-forward `08` : « 1 itération OOS négative sur 3 → poubelle ; 1 sur 20 → tolérable » + métrique Walk-Forward Efficiency (OOS annualisé / IS annualisé) | **À ADOPTER** (marginal — variante de notre degradation_pct, mais côté *décision*) | `08 @ 22:00-23:00` | ★★☆☆☆ |
| D1 | Walk-forward anchored/non-anchored, IS/OOS, « in-sample results are optimistic » | DÉJÀ FAIT — et notre audit va plus loin (n_eff, témoin mesuré) | `08` | — |
| D2 | Seuils de screening d'idées : ≥ 100 trades/direction, DD < 50 % du gain, ≤ 1 filtre, ≥ 250 trades après filtres, optimiser sur un sous-échantillon | DÉJÀ FAIT — nos IC et le registre d'essais sont plus stricts | `11`, `12` | — |
| D3 | « Une equity curve sans pertes = signal d'alerte d'overfit » | DÉJÀ FAIT (test de plateau, ablation) | `11 @ 09:30` | — |
| D4 | Effectif minimum contre le « RR dogma » (un RR < 1:1 peut être viable si WR suffit — mais exiger 200 trades) | DÉJÀ FAIT — c'est notre seuil de rentabilité 1/(1+rr) + IC binomial | `11 @ 11:00-12:00` | — |
| R1 | **Break & bounce (01)** : scalping actions M5/M15, retest du high/low de la veille | **CLASSÉ SANS TEST** (§3.1 — péage 5-13 pts de WR, données absentes, claim 70 % WR à RR 2-3 invraisemblable) | `01` | — |
| R2 | **Touch & turn (02)** : fade M1 de l'opening candle sur actions | **CLASSÉ SANS TEST** (§3.2 — M1 non validable chez nous + péage 8-17 % de la cible, même famille que le rejet responsibleforex) | `02` | — |
| R3 | Filtres horaires/jours/mois optimisés (`06`, `12`) : fenêtres 21-23h long / 5-9h short sur DAX, « pas de longs le jeudi », « pas d'août » | **À REJETER** comme edges (overfit démontré par l'auteur lui-même, 2 ans de données) — fenêtres extraites §4.2 pour recoupement éventuel | `06`, `12` | — |
| R4 | Position sizing calibré sur le pire drawdown historique depuis 2019 | **À REJETER** comme méthode de queue (§4.3 — même défaut que responsibleforex R2, sanctionné chez eux par un facteur 5-7) ; le principe « survivre au DD » est déjà chez nous | `07` | — |
| R5 | S-MACD Divergence : optimiser 5 paramètres d'indicateur in-sample sur 1 seconde et « choisir le backtest à haut win rate » | **À REJETER** (produit + méthode nulle) — la normalisation S-MACD elle-même est une info utile pour s12 (§2) | `05` | — |
| R6 | « AI bot 30k » : ChatGPT-5 compresse 20 algos en 28 lignes, −18 700 € en 45 jours à 5 % de risque/trade | ÉDITORIAL — résultat négatif honnête, n = 1, aucune méthode ; la contre-performance dit surtout que risquer 5 %/trade tue n'importe quoi | `09` | — |
| R7 | « Ultimate algos » du criblage 04 (PF 13,38, filtres septembre/décembre, zombie exits conditionnels) | **À REJETER** — sur-ajustement assumé par l'auteur (« high risk of being overfitted », `04 @ 34:30`) | `04 @ 33:30-36:30` | — |

---

## 2. P1 — Précisions pour la session s12 (Daily MACD) — À TRANSMETTRE

La session s12 teste leur « Daily MACD » gratuit. Deux fichiers de ce corpus
apportent des précisions qu'elle n'a peut-être pas :

### 2.1 Les règles exactes du free algo, énoncées par l'auteur

`10 @ 19:30-20:00`, en décrivant le code du free algo qu'il distribue :

> « The strategy looks for **consistently falling MACD values over 5 days**. It
> makes sure that **today's MACD value is below zero** and that the **close of
> today is weaker than yesterday**. And it also makes sure that the **close is
> near the low of the trading range**. If all of that lines up at the same
> time, it enters a **long** position. The exit code is very simple: **if the
> close breaks above the previous day's high**, then the strategy closes the
> trade. »

Soit : long-only, D1, 4 conditions d'entrée (MACD décroissant 5 jours
consécutifs, MACD < 0, close < close[1], close près du bas du range — « near »
non quantifié dans le transcript), sortie au dépassement du high de la veille.
**Instrument : SP500** (« this strategy was built for SP500... USA 500 »,
`10 @ 13:30`), **spread utilisé dans sa démo : 1 point** (`10 @ 15:00`).

### 2.2 La borne OOS légitime : 21 juin 2022

Release date énoncée deux fois : « a date on the post of the algo which was in
June 2022 » (`10 @ 13:00`), « I'm setting **June 21st, 2022** here »
(`10 @ 14:30`). Conséquence méthodologique directe pour s12 : **tout ce qui
est postérieur au 2022-06-21 est hors échantillon au sens fort pour EUX** (code
figé publiquement, non modifiable a posteriori). Le protocole s12 devrait
rapporter séparément la performance ≥ 2022-06-21 : c'est la seule fenêtre où
leur claim « performs well since release » (`10 @ 15:30`) est falsifiable, et
c'est une vraie coupure pré-enregistrée — chose que nous n'avons jamais sur
nos propres stratégies. Réserve : la sélection *du survivant présenté* parmi
~30 algos publiés reste non corrigée (biais du survivant, §0) — la coupure est
propre, le choix de l'algo ne l'est pas.

### 2.3 Le « MACD » maison est possiblement normalisé (S-MACD)

`05` décrit leur indicateur fétiche : un MACD **stochastique-normalisé**,
borné ~±40, comparable entre instruments (« the S macd will represent the
index in a relative format relative to the closing price », `05 @ 01:30`).
Si le code du Daily MACD utilise leur S-MACD et non le MACD standard, les
signaux diffèrent. À vérifier par s12 **dans le code téléchargé**, pas dans
les vidéos — le transcript `10` dit « MACD » sec, mais l'ambiguïté vaut une
ligne de vérification (période/fast/slow/signal non données dans les vidéos).

---

## 3. Les trois scalpings — règles exactes, économie a priori, verdicts

Règle du jeu (mission) : calcul de péage relatif AVANT verdict, par stratégie.
Formules METHODOLOGY §2 : `drag = spread / SL`, `pénalité_WR = drag / (1+rr)`,
`seuil_WR = 1 / (1+rr)`. Chiffres tirés des exemples de l'auteur lui-même.

### 3.1 `01` — « Break & Bounce » (769 707 vues) — CLASSÉ SANS TEST

**Règles exactes** (`01 @ 01:30-12:00`) :

| Composant | Règle | Source |
|---|---|---|
| Instrument | actions US (démo Netflix), « works with any asset » | `01 @ 01:30` |
| Étape 1 (D1) | box high/low de la veille, étendue au jour courant | `01 @ 01:30` |
| Étape 2 (M15) | breakout confirmé = **clôture M15** au-dessus/au-dessous du box | `01 @ 05:00` |
| Étape 3 (M5) | retest du niveau + **hammer / inverted hammer / engulfing** ; hammer valide seulement après mouvement contraire net | `01 @ 07:30-11:00` |
| Fenêtre | **premières 2 h 30** après l'open, sinon pas de trade | `01 @ 07:30` |
| Entrée | break du hammer ; engulfing : entrée au high/low de la bougie précédente sans attendre la clôture | `01 @ 08:30-09:30` |
| SL / TP | SL au low/high de la bougie signal ; TP = 2× à 3× le SL | `01 @ 11:30`, `01 @ 15:30` |
| Clôture forcée | à la clôture du marché si ni SL ni TP | `01 @ 16:00` |
| Fréquence | 2-3 setups/mois **par action** → scan multi-actions requis | `01 @ 13:00` |
| Claim | algo live depuis ~9 mois : « win rate of 70%, profit factor of 1.6 » | `01 @ 03:30` |

**Économie a priori.** Ses deux trades démontrés : SL 17 ¢ / TP 51 ¢ sur
Netflix ~94,5 $ (SL = 0,18 % du prix) et SL 39 ¢ / TP 78 ¢ (SL = 0,41 %).
Coût aller-retour CFD action (spread + commission IG ~2 ¢/action/côté) :
~6-9 ¢ sur un titre à ~95 $. Drag = 6-9 ¢ / 17-39 ¢ = **21-53 % du SL**.
Pénalité à RR 2-3 : **5 à 13 points de WR**. C'est la zone du rejet a priori
responsibleforex (drag 30-60 % de la cible) : marge plausible d'un signal
price-action (quelques points de WR) < péage. Facteur défavorable > 1,5 → pas
de test.

**Aggravants** : (a) le claim 70 % WR à TP = 2-3× SL donnerait ~1,4-1,8 R
d'espérance par trade — plusieurs ordres de grandeur au-dessus du calibre
externe §10, sans track auditée ; (b) nous n'avons **ni données actions, ni
M5 au-delà de ~16 mois** (METHODOLOGY §9) — même en voulant tester, on ne
peut pas ; (c) la famille sous-jacente (breakout + retest) est celle de s11,
mesurée morte chez nous en H1, et « négative en moyenne » chez AI Pathways.

**Verdict : classé sans test.** Falsification qui le ferait rouvrir : un
Myfxbook/relevé broker vérifié de l'algo « live 9 mois » — non fourni.

### 3.2 `02` — « Touch & Turn » scalping M1 (538 974 vues) — CLASSÉ SANS TEST

**Règles exactes** (`02 @ 01:00-12:30`) :

| Composant | Règle | Source |
|---|---|---|
| Instrument | actions US (Netflix, Meta), extensible « any index, any stock » | `02 @ 10:30` |
| Setup | bougie d'ouverture M15 close ; **« liquidity candle »** si range ≥ 25 % de l'ATR(14) daily | `02 @ 05:30-06:30` |
| Direction | **fade** : bougie d'ouverture rouge → limit BUY au **low** du range ; verte → limit SELL au high | `02 @ 07:30` |
| TP | niveau Fibonacci **38,2 %** du range d'ouverture (61,8 dans la démo live short) | `02 @ 08:30`, `02 @ 18:00` |
| SL | **la moitié de la distance TP** (TP = 2× SL) | `02 @ 08:30` |
| Fenêtre | premières **90 minutes** de l'open | `02 @ 18:00` |
| Exécution | M1, ordre limite | `02 @ 07:30` |
| Claim | scénario perdant « moins de 30 % du temps » (argument des 4 scénarios, pas un backtest montré) | `02 @ 14:30` |

**Économie a priori.** Exemple Netflix : TP 56 ¢ (0,60 % du prix), SL 28 ¢
(0,30 %). Coût aller-retour ~6-9 ¢ → **drag = 21-32 % du SL**, pénalité à
RR 2 : **7-11 points de WR** ; péage = **8-17 % de la cible**. Même famille
économique que le scalping M1 responsibleforex, rejeté a priori (drag
30-60 % de la cible) — ici un cran moins mauvais mais toujours rédhibitoire :
le seuil de WR passe de 33 % à 40-44 %, et l'argument « 4 scénarios » de
l'auteur n'est pas un backtest (aucun chiffre montré, `02 @ 14:30` : « as
these back tests shows » sans jamais afficher le rapport).

**Aggravant décisif** : exécution M1 — nous n'avons **aucune donnée M1** et
~16 mois de M5. Structurellement non validable chez nous.

**Verdict : classé sans test.** À noter : le mécanisme (fade de l'excès
d'ouverture) est du mean reversion intraday — la *famille* est cohérente avec
ce que deux sources déclarent vivante, mais à ce timeframe le péage la
condamne pour nous. Si un jour l'idée est retestée, c'est la version M5 sur
indice (§3.3) qui est le bon véhicule, pas celle-ci.

### 3.3 `03` — « Quick Flip » ONE CANDLE (1 654 883 vues) — FICHE CONDITIONNELLE

**Règles exactes** (`03 @ 01:30-13:30`) :

| Composant | Règle | Source |
|---|---|---|
| Instrument | NASDAQ 100 (démo principale) + actions (NVDA) ; « more prominent in individual stocks » | `03 @ 01:30`, `03 @ 15:00` |
| Setup | bougie d'ouverture M15 boxée ; liquidity candle si range ≥ 25 % ATR(14) D1 (souplesse : 22-23 % acceptable, `03 @ 07:00`) | `03 @ 05:30-07:00` |
| Signal | sur **M5** (ou moins) : hammer / inverted hammer / engulfing **hors du box**, dans le sens du fade ; signal DANS le box = invalide | `03 @ 08:00-08:30`, `03 @ 19:00` |
| Fenêtre | 90 minutes après l'open | `03 @ 08:30`, `03 @ 17:30` |
| Entrée | break de la bougie signal (engulfing : au high/low de la bougie précédente) | `03 @ 09:30-11:00` |
| SL | au-delà de la mèche de la bougie signal | `03 @ 10:00` |
| TP | **le côté opposé du box** d'ouverture | `03 @ 12:30` |
| Exemple chiffré | NASDAQ : entrée 24 872, SL 28 pts, TP 212 pts (RR ~7,6) ; NVDA : SL 2,65 $, TP 7 $ (RR 2,7) | `03 @ 13:30`, `03 @ 20:30` |
| Claim | aucun chiffre agrégé — « almost every time it reverses » (`03 @ 14:00`), zéro backtest montré | |

**Économie a priori — c'est le cas où le rejet en bloc serait faux.** Sur
NASDAQ CFD en heures liquides US, spread ~1-2 points. SL de l'exemple : 28
points → **drag = 3,6-7 %**, pénalité à RR 7,6 : **0,4-0,8 point de WR** ;
même avec un SL plus réaliste de 50-100 pts et RR 2-3, pénalité ≈ 0,5-2 pts.
C'est l'ordre de grandeur de notre péage H1 (2,14) ou mieux. **L'économie ne
condamne pas cette stratégie sur indice** — contrairement à 01/02 sur actions.

**Ce qui reste contre elle** : (a) profondeur M5 ~16 mois chez nous
(METHODOLOGY §9 : « stratégies M5 non validables ») — un seul régime, IC
larges, ~250-350 séances soit un effectif de setups probablement 60-150 après
filtre liquidity candle ; (b) aucun backtest fourni par l'auteur, que des
exemples choisis (il le dit lui-même : « this isn't cherry-picked », suivi
uniquement d'exemples gagnants et d'un unique perdant sur `02`) ; (c) le
signal contient des composants discrétionnaires (« clear negative movement »,
qualité de la mèche `03 @ 17:00` : « it's not a perfect-looking liquidity
candle... I think it's good enough »).

**Fiche de test (si la session principale arbitre GO)** :
- **Hypothèse** : le fade de l'opening range M15 du NASDAQ (signal de
  renversement M5 hors box, dans les 90 min post-open US), TP au côté opposé
  du box, a une espérance par trade positive après coûts.
- **Protocole** : M5 NASDAQ (+ SP500 en 2e instrument, fixé d'avance), 16 mois
  disponibles. Règles mécanisées : liquidity = range M15 ouverture ≥ 25 %
  ATR(14) D1 ; signal = engulfing OU hammer (mèche ≥ 2× corps) hors box ;
  entrée au break ; SL mèche ; TP côté opposé ; time-stop à la clôture de
  séance. Grille minimale : 2 seuils liquidity (20 %, 25 %) × 2 types de
  signal × 1 = **4 cellules**, consignées au registre d'essais. R1
  obligatoire, bras témoin mesuré (l'outil existe, ~2 min/config — audit D3),
  contrôle long/short.
- **Critère écrit avant tout chiffre** : R/trade > 0 après coûts ET percentile
  ≥ 95 du témoin aléatoire ET les deux côtés (fade de bougie verte ET rouge)
  contribuent. Sinon : classement définitif.
- **Statut du verdict** : quel que soit le résultat, **screening 1 régime**
  — un pass ne donnerait pas un feu vert de déploiement, seulement une mise
  en surveillance (l'échantillon est notre limite, pas la leur).
- **Coût estimé** : ~1 jour de session (implémentation signal M5 + 4 cellules
  + témoin), aucune donnée nouvelle à acheter.

---

## 4. Priorité 1 et 3 — le criblage `04` et la méthode

### 4.1 `04` — « I Backtested 500 Trading Entries » : le criblage de masse

**Dispositif** (`04 @ 02:00-06:30`) : 5 entrées × 10 sorties × 5 indices
(SP500, NASDAQ 100, Dow, DAX 40, OMXS30) × long/short = 500 backtests.
**Daily**, ~30 ans pour les US (`04 @ 19:30` « last 30 years »), exécution à
l'open du lendemain, SL 5 % immédiat, zombie exit 20 jours, taille 1/point
(sur-pondère les années récentes, dit explicitement `04 @ 05:00`).
**« Spreads and overnight fees are not included »** (`04 @ 05:30-06:00`).
Valeurs des paramètres choisies « quite randomly » (`04 @ 10:00`) — assumé,
c'est un criblage de structure, pas d'optimisation.

**Multiple testing : non traité.** 50 combinaisons par marché et par sens,
best-of rapporté, zéro correction, zéro témoin, zéro hors-échantillon. Le
seul mitigant — réel — est la **répétition trans-marchés du même vainqueur**
(forme faible de transfert à froid) : une entrée qui gagne le best-of sur 6
des 10 tableaux indépendants est moins probablement un artefact qu'un best-of
isolé.

**Leurs verdicts de familles** (`04 @ 30:00-33:00`) :

| Famille | Leur verdict | Le nôtre / autres sources | Statut |
|---|---|---|---|
| **Mean reversion RSI(14) < 30, D1, indices** | meilleure entrée dans **6/10** cas, « souvent 3 à 10× mieux » que la 2e (`04 @ 31:00`) ; pire entrée pour shorts DAX | jamais testé chez nous sur ce périmètre exact (s12/T1 en cours) ; AI Pathways `9000` : seule famille vivante, RSI-reversion sur 20 tickers | **CONCORDANCE INTER-SOURCES n°1** — voir T1 |
| **Breakout Bollinger** | pire entrée dans **8/10** cas — « Whoever said that the bowlinger band entry was a great entry was just bullshitting » (`04 @ 32:30`) | s11 cassure morte chez nous (H1) ; AI Pathways : breakout négatif en moyenne | **CONCORDANCE n°2 — 3 sources indépendantes sur la mort des cassures** |
| **Trend MA(20/50) cross** | moyen ; best-of seulement OMXS30 long et NASDAQ short | trend mort ×3 chez nous ; AI Pathways négatif en moyenne (« no real reason a line crossing another line should predict anything ») | **CONCORDANCE n°3** (leur exception OMXS30 = 1 best-of sur 10, banal sous le nul) |
| **Shorts sur indices** | « most numbers here are negative... leave it for the daredevils » (`04 @ 21:30`) | notre contrôle long/short : les longs indices 2021-2026 portent du beta, pas de l'edge | Cohérent — mais eux ne font PAS le contrôle : leurs best-of longs contiennent le drift séculaire, non séparé |
| Sorties | breakeven-trailing bon pour shorts, tue les longs ; MA-trail bon longs US seulement ; « entries and exits interact » (`04 @ 37:00`) | non couvert chez nous à ce niveau de détail | Info de conception, pas un edge |

**Lecture honnête du fichier** : sans coûts (véniel en D1 : péage ~0,46 pt de
WR chez nous), sans OOS, sans correction — les *chiffres* ne valent rien,
mais la *structure* (quelle famille gagne les best-of de façon répétée sur 10
tableaux) est le même signal que le criblage AI Pathways, obtenu par un
auteur, une plateforme et un univers différents. C'est exactement le type de
concordance qui a établi l'or et le 2-3 %/mois.

**T1 — ce que ça change pour nous** : le test mean reversion D1 (s12/T1
AI Pathways) en cours gagne une 2e source indépendante. Extension proposée,
à coût quasi nul si la grille s12/T1 n'est pas encore gelée : inclure la
variante de sortie **MA-trail EMA(10)** et la sortie **close > high de la
veille** (celle du Daily MACD) dans les 2 modes de sortie du protocole — ce
sont les sorties que `04` déclare synergiques avec l'entrée RSI sur les
indices US (`04 @ 19:30`, `04 @ 25:30`). Si la grille est gelée : ne pas
l'élargir (registre d'essais), le noter pour une éventuelle 2e passe.

### 4.2 `06` + `12` — filtres horaires/jours/saisons : l'anti-exemple utile

`06` est une **démonstration d'overfitting assumée** : « I'm not going to
care about the risk of overly optimizing this strategy » (`06 @ 01:00`), sur
~2 ans de données (« doesn't really have much statistical relevance »,
`06 @ 06:00`), et le test final sur la période antérieure non optimisée
montre une courbe qu'il qualifie lui-même de dégradée (`06 @ 09:00`).

Fenêtres exactes extraites (pour recoupement avec notre effet de session
mesuré, rien de plus) : DAX 10-min, RSI 14 — longs autorisés **21:00-23:00**
seulement ; shorts **05:00-09:00** ; pas de longs les 5 premiers jours du
mois ; pas de longs le jeudi ; pas de longs en août, pas de shorts en
octobre (`06 @ 02:30-07:00`). `12` retombe indépendamment sur « pas de
jeudi » (`12 @ 04:00`) — sur le même marché et la même maison, ce n'est pas
une réplication indépendante.

**Recoupement avec nos mesures** : notre effet de session est réel mais
enterré par le péage (s91+s09) — et il concerne des fenêtres de liquidité
(sessions), pas des heures fines optimisées. Rien ici ne le contredit ni ne
le renforce : leurs fenêtres sortent d'une optimisation in-sample sur 2 ans,
précisément ce que notre convention interdit de lire comme un edge. **À
rejeter comme edges, à conserver comme catalogue de ce que produit une
optimisation calendaire naïve.**

Une seule pratique de `12` mérite mention : optimiser sur **20 % des données**
en gardant 80 % intacts (`12 @ 05:30`) — l'intention (préserver de l'unseen)
est bonne, mais il ne montre jamais la validation sur les 80 % : le geste est
inachevé. Notre hold-out scellé (AI Pathways A3) est la version complète.

### 4.3 `07` — position sizing : une bonne posture, une mauvaise queue

Le principe sain — « the most important principle is that your position size
allows you to stay in the game at all times » (`07 @ 01:00`), ne rien changer
en drawdown si le sizing initial était correct (`07 @ 04:00`) — est déjà chez
nous (R2, guards, règles d'arrêt §8).

La méthode, elle, est le défaut classique : la calculette dimensionne pour
survivre au **pire drawdown historique depuis 2019** de leurs 29 algos
(`07 @ 02:30`), avec l'aveu en fin de vidéo « future draw downs could exceed
historic draw downs » (`07 @ 08:00`). C'est exactement la calibration de
queue in-sample que responsibleforex R2 illustrait — sanctionnée chez ce
dernier par un facteur 5-7 entre DD modélisé et vécu. S'y ajoutent : « best
date to increase position sizes... November 1st » (`07 @ 04:30`) — un
artefact saisonnier non justifié ; et « over 100% in just 7 months »
(`07 @ 07:30`) comme vitrine. **À rejeter comme méthode ; rien à adopter.**

### 4.4 `08` — leur walk-forward vs le nôtre

Contenu : pédagogie propre des 4 méthodes (live direct / plein échantillon /
IS-OOS simple / walk-forward), anchored vs non-anchored (`08 @ 18:00`),
module PRT 2-20 itérations, et la métrique **Walk-Forward Efficiency** = OOS
annualisé / IS annualisé (ex. 66 %, `08 @ 21:30-22:00`).

| Aspect | Eux | Nous |
|---|---|---|
| Fenêtrage | anchored OU non-anchored (vrai glissant natif dans PRT) | anchored 4 fenêtres ; notre MODE_ROLLING était un faux glissant (étude or) — le vrai K-folds est notre chantier A2 |
| Sélection par itération | « the one that earned the most money » (`08 @ 13:00`) — top-1 brut, aucun plateau | test de plateau + cohérence de famille |
| Décision | heuristique « 1 OOS négative / 3 itérations → toss ; 1 / 20 → tolérable » (`08 @ 22:00-23:00`) | proportion de folds + IC + témoin mesuré (post-audit) |
| Dégradation IS→OOS | WFE annualisée, affichée par itération | `illusion_r` / `honest_r` / `degradation_pct` — équivalent |
| Multiple testing | absent | convention n×0,05 (démolie par l'audit D2) → témoin mesuré |

**Ce qu'ils ont que nous n'avons pas** : rien de substantiel — le module
non-anchored natif est l'équivalent du K-folds que nous devons encore
implémenter (A2 AI Pathways), et la WFE est une reformulation annualisée de
notre degradation_pct. **Ce que nous avons qu'ils n'ont pas** : plateau,
témoin, IC, registre, R1. Leur heuristique de décision (A2 du tableau §1)
est le seul emprunt possible : un seuil *décisionnel* simple sur la
proportion d'itérations OOS négatives, à calibrer sur nos cas si on l'adopte
— pas à importer tel quel (leur « 1/3 → poubelle » sur 3 itérations est
statistiquement du bruit, comme nos 4 fenêtres).

### 4.5 `09` + `10` — éditorial

- `09` (AI bot 30 k€) : valeur unique = l'honnêteté du résultat négatif
  détaillé (−18 687 €, 43 trades, WR 49 %, `09 @ 15:30`). Méthodologiquement
  vide (n = 1, 45 jours, risque 5 %/trade). La comparaison « mes algos ont
  fait +12 000 € sur la même période » (`09 @ 16:00`) est un claim vitrine
  invérifiable — ~27 % en 45 jours, 10× le calibre §10 ; le même auteur
  vendait la calculette `07` sur « ne pas dépasser le DD historique ». À
  classer, rien à extraire.
- `10` (started 2025) : porte la doctrine « depuis la release » (§0, §2) et
  le workflow « 10 algos en démo ≥ 6 mois avant tout live » (`10 @ 18:00`) —
  ce dernier concorde avec notre R10/PAPER et le « 12 mois démo » de
  responsibleforex D3. Déjà chez nous.

---

## 5. Concordances / contradictions avec nos 11 verdicts

### Concordances (le plus précieux du dépouillement)

| # | Sujet | Sources concordantes | Impact |
|---|---|---|---|
| K1 | **Mean reversion D1 indices = la famille vivante** | `04` (6/10 best-of RSI) + AI Pathways `9000` (64 % des survivants) — 2 criblages indépendants, univers et plateformes différents | Renforce la priorité du test s12/T1 en cours ; c'est la 3e concordance inter-sources du projet après l'or et le 2-3 %/mois |
| K2 | **Cassures mortes** | `04` (Bollinger pire entrée 8/10) + nous (s11, s09) + AI Pathways | Clôt encore un peu plus le dossier cassures |
| K3 | **Trend mort** | `04` (MA cross moyen-faible) + nous (×3) + AI Pathways | idem |
| K4 | **Effectif minimum obligatoire** | `11` (≥ 100 trades/direction, ≥ 200 si RR < 1) vs AI Pathways R5 (« le nombre de trades n'importe pas ») | ProRealAlgos est de NOTRE côté contre AI Pathways sur ce point — notre règle IC reste plus stricte que les deux |
| K5 | **Démo prolongée avant live** | `10` (≥ 6 mois) + responsibleforex (12 mois) + notre R10 | Rien à changer |
| K6 | **Le péage relatif décide du timeframe** | leurs 3 scalpings passés au crible §3 : le M1 actions meurt, le M5 indice survit au calcul | Notre METHODOLOGY §2 discrimine correctement à l'intérieur d'une même chaîne — validation d'usage de l'outil |

### Contradictions / points de friction

| # | Sujet | Eux | Nous | Test qui départage |
|---|---|---|---|---|
| F1 | Longs indices D1 sans contrôle directionnel | best-of longs « pretty great results in the last 30 years » (`04 @ 19:30`) | s01/USDJPY : +69,7 R long / −10,0 R short = beta, pas edge | Déjà dans le protocole s12/T1 : contrôle long/short + témoin aléatoire (qui absorbe le drift). Rien de nouveau à lancer |
| F2 | Fenêtres horaires fines comme edge (`06`) | long 21-23h / short 5-9h DAX | effet de session réel mais enterré par le péage (s91+s09) ; leurs fenêtres = opt in-sample 2 ans | Aucun test — leur propre vidéo montre la dégradation hors fenêtre d'optimisation. Classé |
| F3 | Sizing sur pire DD historique (`07`) | suffisant si « moderate » | responsibleforex : facteur 5-7 entre DD modélisé et vécu | Aucun test — deux sources du corpus s'entre-réfutent, la nôtre (bootstrap A4, quantile) est la réponse |

---

## 6. Angles morts de la source (risques si on copie)

1. **Survivant parmi N publiés** : la doctrine « depuis la release » est saine
   par algo, mais ils publient ~30 algos et communiquent sur les vivants. Sans
   la liste complète datée, « nos algos performent depuis release » n'a pas de
   dénominateur. Si on adopte A1, l'adopter avec le dénominateur : évaluer
   TOUS les algos datés d'une source, pas ceux qu'elle met en avant.
2. **Zéro coût dans le criblage `04`** (`04 @ 05:30`) — véniel en D1, fatal si
   quelqu'un transpose les conclusions en intraday. Nos §2/§3.2 couvrent.
3. **Zéro multiple testing, zéro IC, zéro témoin** dans les 12 fichiers — les
   chiffres de la source ne sont jamais importables, seulement ses structures
   (release date, WFE, familles gagnantes trans-marchés).
4. **Claims de scalping invérifiables** : le « 70 % WR / PF 1,6 live »
   (`01 @ 03:30`) est la seule trace de résultat live de la chaîne côté
   scalping, sans lien auditable — même standard de rejet que Nate Herk / AI
   Pathways (n court, pas de relevé).
5. **Le levier pédagogique masque le levier commercial** : les vidéos méthode
   (`08`, `11`, `12`) donnent une crédibilité que les vidéos produit
   encaissent (« ultimate algos », snippet payant, calculette). Traiter
   chaque vidéo selon sa catégorie, jamais la chaîne en bloc.

---

## 7. RECOMMANDATION FINALE

**Ordre de priorité de ce qui mérite une action réelle** (la session
principale arbitre et dispatche) :

1. **Transmettre P1 à la session s12 (coût ~0)** : règles exactes §2.1,
   release date 2022-06-21 comme borne OOS séparée à rapporter, vérification
   S-MACD vs MACD standard dans le code téléchargé. C'est le meilleur ratio
   valeur/coût du dépouillement.
2. **Étendre (si non gelée) la grille du test mean reversion D1 en cours**
   avec les 2 sorties que `04` déclare synergiques (MA-trail EMA(10) ;
   close > high veille) — K1 est la concordance la plus forte du corpus.
   Coût : 2 modes de sortie de plus dans une grille existante, consignés au
   registre. Si la grille est gelée : noter pour une 2e passe, ne pas
   élargir.
3. **Fiche conditionnelle T2 (quick flip M5 NASDAQ, §3.3)** : seule stratégie
   de la chaîne dont l'économie a priori survit au calcul de péage. GO
   seulement en acceptant d'avance le statut « screening 1 régime, 16 mois,
   non déployable quel que soit le résultat ». Coût : ~1 jour. Si la file de
   tests est chargée, c'est le premier candidat à différer — l'espérance
   d'information est réelle mais bornée par nos données.
4. **Classés sans suite, définitivement (sauf preuve auditée nouvelle)** :
   `01` break & bounce (péage 5-13 pts WR + données absentes + claim
   invraisemblable), `02` touch & turn M1 (M1 non validable + péage 8-17 %
   de la cible), `05` S-MACD divergence (produit, méthode nulle), `06`/`12`
   filtres calendaires (overfit auto-démontré), `07` sizing sur DD
   historique (méthode réfutée par responsibleforex A1), `09` AI bot
   (éditorial), « ultimate algos » de `04` (overfit assumé).
5. **Aucune adoption d'outillage majeure** : leur WFO n'apporte rien que
   notre chantier A2 (K-folds) ne couvre déjà ; la WFE et l'heuristique de
   rejet OOS (`A2` §1) sont des emprunts cosmétiques, à considérer seulement
   quand A2 sera implémenté.

**Une phrase pour la session principale** : cette chaîne ne vaut ni par ses
stratégies (2 des 3 scalpings meurent au calcul de péage avant tout test) ni
par sa méthode (walk-forward standard, zéro statistique), mais par deux
choses : la **concordance indépendante n°2 sur le mean reversion D1 indices**,
et la **borne de release 2022-06-21** qui donne à la session s12 la seule
coupure hors-échantillon pré-enregistrée dont nous ayons jamais disposé sur
une stratégie tierce.
