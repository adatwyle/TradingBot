# Trade Buddy (René Balke) — analyse écran par écran — 2026-09-12

**Source** : vidéo [qgsi-u0kOVw] (rétrospective 48 min), segment 36:50 → 48:06 ; 168 captures
sous `frames/tradebuddy/` (nommage `sNNN_MMmSSs.jpg`), dont 68 référencées ci-dessous ; transcript `corpus/qgsi-u0kOVw.md`.
**Directive Adrian (2026-09-12, verbatim)** : « à partir de 37:10 René Balke visualise son
TradeBuddy — passe à travers chaque image, analyse les fonctionnalités développées et
développe-les sur l'UI tBot, c'est ce que je veux ».
**Produit dérivé** : `spec/specification-app/SPEC_analytics-trades_2026-09-12.md` (F01-F27 →
exigences AN-n, lots L1/L2/L3).
**Méthode** : lecture des 168 captures + transcript, formules reconstruites et vérifiées sur
les valeurs affichées ; trois relectures critiques intégrées (manques d'écran, erreurs de
mapping tBot, fidélité à la narration). Statut de chaque élément : **montré** (à l'écran),
**dit** (à l'oral), **déduit**.

## 1. Trade Buddy en une page

Outil local navigateur (bmtrading.de/en/trade-buddy/), zéro serveur, données importées
depuis MT5 par fichier texte. Sidebar fixe, 5 groupes / 9 pages :

| Groupe | Page | Vue dans la vidéo | Rôle |
|---|---|---|---|
| OVERVIEW | Dashboard | oui (37:04-38:42) | compte entier sans filtre : en-tête compte, 8 KPI, courbe de solde, P&L par mois (barres), donut win/loss, P&L par symbole, par jour de semaine |
| OVERVIEW | Trades | oui (37:27-37:30) | journal tabulaire 16 colonnes, filtres, import |
| SETUP | Strategies | survolée (37:26, 38:42) | mapping magic → nom de stratégie |
| ANALYZE | Analysis | oui (38:43-48:06, ~90 % du temps) | mêmes KPI recalculés selon 7 filtres, PERFORMANCE (solde / drawdown), heatmap mensuelle, distribution, weekday, par symbole, par stratégie, SUMMARY |
| ANALYZE | Correlation | non | inconnu |
| ANALYZE | Backtest comparison | non | inconnu |
| FORECAST | Monte Carlo | non | inconnu |
| SYSTEM | Logs, Settings | non | inconnu (Settings héberge vraisemblablement nom de compte, broker, devise, starting balance) |

Sidebar sous le logo « TB Trade Buddy » : toggle thème (soleil) + boutons EN / DE (pas de
barre haute). Seul le bouton « Print / Save as PDF » vit dans l'en-tête de la page Analysis
(en-tête sticky au scroll, s134/s140 — la rangée KPI, elle, défile).

Point structurant : **tout sous-ensemble filtré est rejoué comme un compte virtuel partant de
la starting balance** (ligne pointillée « €50,000 »), ce qui rend courbes et drawdowns
comparables entre stratégies et symboles — et rend la courbe **synthétique** : dépôts et
retraits sont ignorés (voir §4, écart avec le solde MT5 réel).

Ce que René regarde, dans l'ordre : (1) Dashboard KPI + P&L par symbole ; (2) Analysis filtré
par stratégie → KPI + courbe + heatmap ; (3) bascule Drawdown pour montrer les creux ;
(4) drill-down par symbole dans la stratégie ; (5) SUMMARY → losing streak. Il n'utilise jamais
FROM/TO, DIRECTION, WEEKDAY, MAGIC, ni la recherche, ni le tri du journal.

## 2. Inventaire chronologique (intervalle · page · widgets · valeurs lues · ce qu'il en dit)

### 36:50 — MT5 (contexte avant Trade Buddy) — `s000_36m50s.jpg`

- **Page** : MetaTrader 5, titre « CapitalPointTrading-MT5-4 - Hedge - Capital Point Trading Ltd ».
- **Widgets** : Navigator > Scripts > `TradeBuddyMT5` (le script d'export) ; Toolbox
  Trade : **6 positions ouvertes** (usdjpy, eurjpy, de40, xauusd, us30, ustec, P&L flottant
  −508.48) + 2 ordres gbpusd « placed » ; **Balance : 19 738.01 EUR** ; graphiques EA
  « TurnaroundTuesday Magic 7/8/9 ».
- **Lecture** : (a) Trade Buddy n'importe que le clôturé — aucune vue « positions ouvertes /
  flottant » n'existe dans l'outil ; (b) le solde réel (19 738 €) n'a rien à voir avec la
  fin de la courbe Trade Buddy (≈ 149 537 € = 50 000 + Σ net) : retraits massifs non modélisés
  (confirmé par Myfxbook à 48:03) ; (c) le broker affiché dans Trade Buddy (« IC Trading »)
  est un libellé saisi, pas une valeur importée.

### 37:04 → 37:26 — Dashboard — `s003_37m04s.jpg`, `s003_37m15s.jpg`, `s003_37m26s.jpg`

- **En-tête compte** : « 50K BM Trading · #11141149 · IC Trading · EUR · Starting balance:
  €50,000.00 · 4,371 trades ».
- **8 tuiles KPI** (montré) : TOTAL TRADES 4,371 (Long · Short) · WIN RATE 52.0 % (2,271 /
  2,099) · NET P&L +€99,537.31 (Ø €22.77 / trade) · PROFIT FACTOR 1.16 · MAX DRAWDOWN
  €22,050.64 (Recovery: 4.51) · SHARPE RATIO 0.05 (Full period) · AVG WIN +€312.35 / AVG
  LOSS −€290.52 · EXPECTANCY +€22.71 (Per Trade).
- **BALANCE CURVE** : aire bleue, pointillé €50,000, axe €40k-€160k, axe X dates yy.mm.dd
  depuis 24.03.21 ; curseur croix sans tooltip.
- **P&L BY MONTH** : barres vertes/rouges, axe −€5,000 → €15,000, étiquettes un mois sur deux.
- **WIN / LOSS** : donut vert/rouge, centre « 52.0 % · 2,271 / 2,099 ».
- **P&L BY SYMBOL** : barres horizontales triées : XAUUSD ≈ 31k, USTEC ≈ 29k, DE40 ≈ 21k,
  US30 ≈ 15k, USDJPY ≈ 5.5k, EURUSD ≈ 1.5k, EURJPY ≈ −2.5k, GBPUSD ≈ −8k (valeurs estimées,
  pas d'étiquettes).
- **P&L BY WEEKDAY** : Mon ≈ 48k, Tue ≈ 28k, Wed ≈ 27k, Thu ≈ 5k, Fri ≈ −11k, Sat/Sun vides.
- **Dit** (37:18-37:28) : « automatic import function from the MetaTrader 5. It's a two-step process ». Survol de « Strategies » à 37:26 sans clic.

### 37:27 → 37:30 — Trades + modale Import — `s004_37m27s.jpg`, `s005_37m28s.jpg`, `s006_37m29s.jpg`, `s007_37m30s.jpg`

- **Trades** (s004) : sous-titre « 50K BM Trading · 4,371 trades », champ « Search… »,
  bouton « Import trades », compteur « 1–200 / 4,371 (4,371 total) », barre de 7 filtres
  (FROM, TO, SYMBOL, STRATEGY, DIRECTION, WEEKDAY, MAGIC + Clear filters), tableau : TICKET,
  SYMBOL, DIRECTION (badge LONG vert / SHORT rouge), VOLUME, OPEN TIME, CLOSE TIME ↓, OPEN
  PRICE, CLOSE PRICE, PROFIT, COMMISSION, SWAP, NET PROFIT, STRATEGY, MAGIC, COMMENT, ✎ / ✕.
  Ligne lue : 4605403351 · USTEC · LONG · 1.90 · 2026-09-09 01:05 → 23:50 · 29511.2 →
  29430.4 · −€131.98 · €0.00 · €0.00 · −€131.98 · Go Long · 3. Mapping visible : magic 1/2/3
  = Go Long, 4/6/11/12 = Range Breakout, 8 = Turnaround Tuesday. **Pas** de colonnes SL/TP
  (pourtant importées). Seuls le compteur et la flèche ↓ sur CLOSE TIME sont visibles :
  pagination, tri par autre colonne et recherche sont **déduits**, jamais utilisés.
- **Modale Import trades · 50K BM Trading** (s005, s006) : lien guide YouTube ; HOW IT WORKS
  Step 1 (télécharger `TradeBuddyMT5.zip`, le placer dans `MQL5\Scripts`, l'exécuter → .txt
  des trades fermés dans `MQL5\Files`), Step 2 (déposer le .txt) ; FILE FORMAT REFERENCE :
  « One trade per line, 15 fields separated by semicolons: ticket;symbol;volume;direction;
  open_price;open_time;close_price;close_time;commission;swap;profit;sl;tp;magic;comment » ;
  « Duplicate tickets are skipped automatically » ; « nothing is uploaded to a server » ; Close.
- s007 : retour sur Trades après fermeture.

### 37:31 → 38:42 — Dashboard, narration des KPI — `s008_37m31s.jpg`, `s009_37m37s.jpg`, `s009_38m01s.jpg`, `s009_38m25s.jpg`, `s010_38m26s.jpg`, `s011_38m42s.jpg`

- **Dit** (37:33-37:48) : « more than 4,000 trades, win rate slightly above 50 %, profit
  around 100,000, profit factor 1.16, max drawdown 22,000 ».
- **Dit** (37:49-37:55) : « the maximum drawdown was 22,000 euro, which to me is a very good
  ratio compared to the overall profit » → lecture du **recovery factor** (4.51).
- **Dit** (37:59-38:10) : « average win and loss are actually quite similar and the expectancy
  per trade is €22. But if you have a lot of trades, then 22 euro on average per trade really
  adds up » → AVG WIN / AVG LOSS et EXPECTANCY sont lus.
- **Dit** (38:01-38:25, curseur sur P&L BY SYMBOL) : « some symbols like gold made most of the
  profit. Some symbols like GBP dollar and Euro Japanese yen are even negative ».
- s011 : survol « Strategies » (38:42), pas de clic.

### 38:43 → 39:06 — Analysis, sans filtre — `s012_38m43s.jpg`, `s013_38m44s.jpg`, `s014_38m47s.jpg`, `s015_38m48s.jpg`, `s016_39m06s.jpg`

- **En-tête** : « Analysis — Filter and break down trade performance », bouton bleu « Print /
  Save as PDF » ; barre 7 filtres tous « All ».
- **KPI** identiques au Dashboard (mêmes 8 valeurs).
- **PERFORMANCE** : cases à cocher de légende « Balance » (bleu) / « Drawdown » (rouge) ;
  animation de tracé en cours (s013) ; tooltip « 26.02.13 — Balance €109,635 ».
- **P&L BY MONTH** (heatmap) : lignes 2024 / 2025 / 2026, colonnes JAN…DEC + TOTAL, ligne
  TOTAL ; cellule = montant + % ; 2024 +€24,545 (+49.09 %), 2025 +€35,264 (+70.53 %), 2026
  +€39,729 (+79.46 %), TOTAL +€99,537 (+199.07 %) ; tooltip (s016) « 2025 Jun / +€7,719.62 /
  147 trades ». Ligne TOTAL : seule la cellule TOTAL×TOTAL est renseignée, les totaux
  colonne-mois (toutes années) sont **vides**.
- Bas de page (s014, partiel) : en-têtes « P&L DISTRIBUTION » | « P&L BY WEEKDAY », axe Y
  500 / 1.0k / 1.5k. **Trou de couverture** : aucune capture ne montre la zone entre ces
  en-têtes et le bas de P&L BY SYMBOL / P&L BY STRATEGY (repris à s134) dans sa continuité ;
  s113 et s135 confirment l'ordre distribution → weekday → symbole → stratégie → SUMMARY,
  sans widget intercalé visible.
- **Dit** : « almost every single month was a profit ».

### 39:12 → 40:04 — Analysis, filtre Go Long — `s018_39m12s.jpg`, `s019_39m13s.jpg`, `s020_39m14s.jpg`, `s023_39m36s.jpg`, `s023_39m49s.jpg`, `s023_40m03s.jpg`, `s024_40m04s.jpg`

- **Dropdown STRATEGY** (s018) : GO LONG (coché), TURNAROUND TUESDAY, RANGE BREAKOUT, ATR
  CANDLE BREAKOUT, UNASSIGNED ; libellé « 1 selected ».
- **KPI Go Long** (s019) : 1,837 / 54.2 % / +€54,800.30 / 1.18 / €23,739.42 (Recovery 2.31)
  / 0.06 / +€355.80 −€356.21 / +€29.83.
- **Heatmap Go Long 2024** : +€272, −€2,895, +€4,273 … TOTAL +€10,925 (+21.85 %) — même
  dénominateur 50 000 pour le sous-ensemble.
- **Courbe** : axe X recalé sur 24.03.21 ; tooltip (s020) « 24.07.14 — Balance €57,930 ».
- **Drawdown** (s023 ×3, s024) : Balance décochée, Drawdown cochée ; aire rouge sous 0, axe
  0 → −€25,000 ; tooltips « 25.04.06 — Drawdown −€23,553.17 (−47.11 %) », « 25.04.05 —
  −€20,576.71 (−41.15 %) », « 25.05.21 — −€496.76 (−0.99 %) ». Le % est rapporté à la
  **starting balance** (23,553.17 / 0.4711 = 50 000), pas au pic.
- **Dit** : drawdown d'avril 2025 « tariffs » ; « a big drawdown, 24,000 euro almost ».

### 40:24 → 41:00 — Analysis, drill-down Go Long par symbole puis Turnaround Tuesday — `s025_40m24s.jpg`, `s026…s033 (40:30-40:39)`, `s034_40m41s.jpg … s040_41m00s.jpg`, `s038_40m50s.jpg`

- s025 : animation de courbe.
- **Dropdown SYMBOL contextuel** (s026-s033) : seulement DE40 / US30 / USTEC (symboles présents
  sous Go Long) — liste **dépendante** du sous-ensemble courant.
- **Turnaround Tuesday** (s034-s040) : 163 / 64.4 % / +€16,956.65 / 2.03 / €3,167.70
  (Recovery 5.35) / 0.28 ; axe X depuis 24.04.01 ; tooltip (s038) « 24.11.22 — Balance €52,016 ».

### 41:06 → 41:23 — Turnaround Tuesday × USTEC, puis Range Breakout — `s042_41m06s.jpg`, `s048_41m15s.jpg`, `s050_41m18s.jpg`, `s051_41m18s.jpg`, `s052_41m21s.jpg`, `s053_41m22s.jpg`, `s054_41m23s.jpg`

- s042 : dropdown STRATEGY ouvert — il **recouvre** les tuiles NET P&L et PROFIT FACTOR
  (simple empilement z-index, pas un comportement).
- **TT × USTEC** (s048) : 70 / 57.1 % (40W / 30L) / PF 1.76 / DD €2,127.52 (Recovery 2.95) /
  Sharpe 0.22 / +€363.70 −€275.42 / +€89.79 → point de contrôle : expectancy = net/N sans
  trade à 0.
- **Range Breakout** (s052-s054) : 2,316 / 49.8 % (1,154W / 1,161L) / +€25,516.88 / 1.09 /
  €10,683.10 (Recovery 2.39) / 0.03 ; curseur **sablier** pendant le recalcul (s052) ;
  tooltip (s054) « 25.02.02 — Balance €60,991 ». 1,154 + 1,161 = 2,315 ≠ 2,316 : un trade
  à net = 0, compté dans N mais ni W ni L ; expectancy affichée 10.91 ≠ net/N 11.02.

### 41:51 → 42:03 — Range Breakout : drawdown, symboles, DE40 — `s058_41m51s.jpg`, `s059_41m52s.jpg`, `s061_41m59s.jpg`, `s062_42m03s.jpg`

- s058 : les deux cases décochées → graphique vide (état transitoire) ; s059 : Drawdown,
  tooltip « 25.08.26 — Drawdown −€1,710.47 (−3.42 %) ».
- **Dropdown SYMBOL** (s061) : 7 options sous Range Breakout (USDJPY, GBPUSD, EURJPY,
  XAUUSD, DE40, US30, EURUSD).
- **DE40** (s062) : 205 / 63.9 % (131W / 74L) / +€6.44 / 1.00 / expectancy **−€0.39** ; axe
  Y €49,500-€50,500. Cas qui révèle la formule Trade Buddy : 131/205 × 48.23 − 74/205 × 86.47
  = −0.39 alors que net/N = +0.03 (les trades à 0 comptent côté perte).
- **Dit** : DE40 « break-even after 205 trades ».

### 42:45 → 43:48 — EURJPY, EURUSD, GBPUSD — `s065_42m45s.jpg`, `s066_42m46s.jpg`, `s067_42m59s.jpg`, `s068_43m00s.jpg`, `s071…s074 (43:09)`, `s076…s080 (43:24-43:36)`, `s081_43m45s.jpg`, `s082_43m48s.jpg`

- **EURJPY** : heatmap 2025 OCT −€3,467 (−6.93 %) ; Sharpe −0.03 ; drawdown tooltip
  « 26.08.30 — −€7,938.12 (−15.88 %) » ; axe X depuis 25.10.07.
- **EURUSD** (s071-s074) : **dit** (43:10-43:14) « Euro dollar, this is actually one that I
  don't trade anymore » — une instance arrêtée reste dans l'analyse sans marqueur.
- **GBPUSD** (s076-s080) : DD €11,900.88 (Recovery **−0.69**, net négatif −8,201.71) ; Sharpe
  −0.05. Drawdown tooltips (s081, s082) « 24.05.26 — −€675.65 (−1.35 %) », « 26.04.06 —
  −€11,717.70 (−23.44 %) » : le creux du tooltip (11,717.70, série journalière) diffère du
  KPI (11,900.88, série par trade).
- **Dit** (43:55-44:01) : « I would always recommend to not only test a few months or years,
  but really make long-term backtests ».

### 44:03 → 45:26 — US30, sélection multi-symboles, USDJPY — `s088_44m03s.jpg`, `s091…s096 (44:14-44:25)`, `s097_44m29s.jpg`, `s098_44m31s.jpg`, `s099_44m40s.jpg`, `s101_44m50s.jpg`, `s103_45m17s.jpg`

- **RB × US30** (s088) : 221 / 43.9 % (97W / 124L) / PF 0.86 / DD €2,715.33 (Recovery
  **−0.56**) / −0.06 / +€96.33 −€87.69 / −€6.92 → point de contrôle : recovery négatif si
  net < 0, expectancy = net/N.
- **SYMBOL 3 / 5 / 4 / 1 / 0 selected** (s091-s096) : recomposition en direct, libellé « N
  selected », tout recalcule instantanément.
- **USDJPY** (s097, s098) : DD €23,373.20 (Recovery 0.25) ; drawdown (s099) creux ≈ −€23,400 ;
  tooltips (s101) « 26.01.31 — Balance €58,560 », (s103) « 25.05.20 — Balance €51,269 ».
- **Dit** (44:24-44:48) : USDJPY « glorious » puis « one of the biggest drawdowns in the whole
  account… it is still in this drawdown. It didn't recover at this point but it recovered
  more than 50 % » → lecture du **drawdown courant** et de la fraction récupérée (métrique
  absente de l'écran, reconstituée à l'œil).
- **Dit** (45:06-45:26) : « I did backtests for all of these strategies over at least the
  last 10 years… these drawdowns actually are completely normal ».

### 45:54 → 46:23 — XAUUSD et jeu des 7 charts — `s112_46m01s.jpg`, `s113_46m02s.jpg`, `s116_46m07s.jpg`, `s118…s123 (46:16-46:23)`

- **XAUUSD** (s112, s113) : DD €5,930.38 (Recovery 5.14), Sharpe 0.13 ; tooltips « 25.05.02 —
  €65,276 », « 25.08.07 — €66,929 » ; heatmap 3 années complètes, TOTAL +€30,491 (+60.98 %) ;
  weekday : 5 barres €4k-€10k ; distribution axe 40-100 ; tooltip TOTAL 2026 (s116)
  « 2026 — +€14,607.92 — 173 trades ».
- **SYMBOL 1 / 4 / 6 / 7 / 2 selected** (s118-s123).
- **Dit** (45:54-46:25) : « I trade this in 1 2 3 4 5 6 seven charts and only one is really
  making all of the profits » → seul XAUUSD porte le profit du Range Breakout ; USDJPY a
  contribué puis rendu une grande partie.

### 46:30 → 47:38 — ATR Candle Breakout, SUMMARY, retour All — `s126_46m30s.jpg`, `s127_46m33s.jpg … s131_47m12s.jpg`, `s132_47m16s.jpg`, `s133_47m17s.jpg`, `s134_47m19s.jpg`, `s135_47m28s.jpg`, `s136_47m29s.jpg`, `s137_47m30s.jpg`, `s138_47m34s.jpg`, `s139`, `s140_47m38s.jpg`

- **Bascule Range Breakout → ATR** (s126, s127).
- **KPI ATR** : 55 / 29.1 % (16W / 39L) / +€2,263.48 / 1.62 / €1,138.55 (Recovery 1.99) /
  0.19 / +€370.34 −€93.90 / +€41.15 ; axe X depuis 26.03.19 ; axe Y €49k-€52k (s137).
- **Dit** (46:51-47:01) : « we need one win out of four trades to be profitable » — tiré des
  tuiles AVG WIN 370 / AVG LOSS 90, pas de l'histogramme.
- **Drawdown ATR** (s132 vide, s133) : tooltip affiche « Balance €50,110 » même en mode
  drawdown (petit bug d'étiquette) ; axe 0 → −€1,200 (s136).
- **SUMMARY** (s134, seule vue complète du bloc) :
  - VOLUME : Total trades 55 · Long 29 · Short 26 · Winning 16 · Losing 39 · Win rate 29.1 % ·
    Long win rate 27.6 % (8/29) · Short win rate 30.8 % (8/26).
  - P&L : Net +€2,263.48 · Gross profit +€5,925.40 · Gross loss −€3,661.92 · Avg win +€370.34
    · Avg loss −€93.90 · Expectancy +€41.15 · Profit factor 1.62 · Best +€392.15 · Worst −€112.93.
  - RISK : Max drawdown €1,138.55 · Max DD % 2.26 % · Recovery factor 1.99 · Sharpe 0.19
    (Full period) · Sharpe (annualized, 252d) 1.45 (55 trades) · Sortino 0.30.
  - STREAKS & TIMING : Max win streak 5 · Max loss streak 12 · Avg holding time 12h 13m.
  - BALANCE & COSTS : Starting €50,000.00 · Final €52,263.48 · Total commission −€13.06 ·
    Total swap −€13.12 (libellés partiellement masqués par la webcam).
- **Dit** (47:22-47:27) : « the losing streak was 12, 12 trades losses next to each other. So
  that's trading » — seul chiffre du SUMMARY commenté, pour relativiser le drawdown.
- **Bas de page ATR** (s135) : distribution bins −€105 → €384 (bimodale : ≈ 24 trades vers
  −€71 / −€37, 4 trades vers +€367) ; weekday Mon ≈ +500, Tue ≈ +450, Wed ≈ −300, Thu ≈ +300,
  Fri ≈ +1,150 ; P&L BY SYMBOL : barre XAUUSD seule (≈ €2,263) ; P&L BY STRATEGY : barre
  « ATR Candle Breakout » seule (axe €0 / €500 / … €2,000).
- **Retour All** (s138-s140) : heatmap compte entier 3 années ; weekday et distribution compte
  entier (bins −€2,680, −€1,715, −€749, €216 … €6,008, pic ≈ 1,500 trades autour de 0).

### 48:03 — Myfxbook (contexte après Trade Buddy) — `s144_48m03s.jpg`

- **Lu** : Deposits €45,115.84 · Withdrawals €125,023.13 · Balance €19,751.54 · Drawdown
  77.98 % · Profit €99,537.31 · Interest −€1,204.15.
- **Lecture** : le Profit Myfxbook coïncide au centime avec le NET P&L Trade Buddy → le net
  Trade Buddy est bien profit + commission + swap ; « Interest » = swap cumulé du compte ; le
  DD Myfxbook (77.98 %, sur le solde réel après retraits) n'a rien à voir avec le DD Trade
  Buddy (22,050 ≈ 44 % de 50 000) : les **flux de capital** ne sont pas modélisés.

## 3. Formules reconstruites et vérifiées

Sur T = trades clos filtrés, N = |T|, W = net > 0, L = net < 0, Z = net = 0 (N = W + L + Z).

| Métrique | Formule Trade Buddy (vérifiée) | Preuve |
|---|---|---|
| net par trade | `profit + commission + swap` (commissions négatives dans l'export MT5) | XAUUSD 188.15 − 0.84 + 0 = 187.31 ; Myfxbook Profit = NET P&L |
| win_rate | `W / N` | DE40 131/205 = 63.9 % (pas 131/204) |
| avg_per_trade | `net / N` | 99,537.31 / 4,371 = 22.77 |
| profit_factor | `Σ net(W) / |Σ net(L)|` | 5,925.40 / 3,661.92 = 1.62 |
| avg_win / avg_loss | `gross_profit / W` ; `gross_loss / L` | ATR 370.34 / −93.90 |
| expectancy | `(W/N)·avg_win + ((N−W)/N)·avg_loss` — Z côté perte | 22.71 ≠ 22.77 (compte) ; 10.91 ≠ 11.02 (RB) ; DE40 −0.39 avec net +6.44 |
| max_drawdown | série `B_k = 50,000 + Σ net`, `max(P_k − B_k)` à granularité trade | GBPUSD 11,900.88 (KPI) vs 11,717.70 (tooltip journalier) |
| recovery_factor | `net / max_drawdown` (négatif si net < 0) | 99,537.31 / 22,050.64 = 4.51 ; −8,201.71 / 11,900.88 = −0.69 ; US30 −0.56 |
| drawdown % (tooltip) | `dd / starting_balance` — pas relatif au pic | 23,553.17 / 0.4711 = 50,000 (vérifié 4 fois) |
| Max DD % (SUMMARY) | **hypothèse** : DD max de la série journalière / 50,000 (≈ 1,130 / 50,000 = 2.26 %) | 1,138.55 / 50,000 = 2.28 % et / 50,110 = 2.27 % ne donnent pas 2.26 % ; un pic de 50,378 n'existe pas sur s128 |
| heatmap % | `pnl_mois / 50,000` non composé ; TOTAL année = Σ mois | 6,290 / 50,000 = 12.58 % ; 24,545 = 49.09 % |
| sharpe « Full period » | `mean(net_k) / std_pop(net_k)` sur le P&L par trade en devise | ATR 41.15 / 210.7 = 0.195 |
| sharpe « annualized » | `sharpe × √N` (N trades, pas 252 j) — **à ne pas copier** | 0.195 × √55 = 1.446 |
| sortino | `mean / downside_deviation`, variante exacte non retrouvée (0.30 ; candidats 0.52 / 0.36) | — |
| long/short win rate | `W_side / N_side` | 8/29 = 27.6 % ; 8/26 = 30.8 % |
| streaks | plus longue suite consécutive de W (resp. L) sur T trié par close_time | ATR 5 / 12 |
| final balance | `starting + net` | 50,000 + 2,263.48 = 52,263.48 |

## 4. Catalogue des fonctionnalités (F01-F27)

Priorité : P1 = ce que René regarde et commente ; P2 = affiché, jamais commenté ; P3 = non
montré ou non repris. « Existe dans tBot » lu sur `app/server/{state,services}.py`,
`ui/app.js`, `core/ledger/ledger.py` (2026-09-12). Lot = SPEC_analytics-trades §7.

| # | Fonctionnalité | Page Trade Buddy | Prio | Existe dans tBot | Effort | Lot / décision |
|---|---|---|---|---|---|---|
| F01 | Bandeau KPI 8 tuiles (trades L/S, win rate, net, PF, max DD + recovery, Sharpe, avg win/loss, expectancy) | Dashboard + Analysis | P1 | partiel — status.json relaie n_closed/cum_r/pnl_chf ; aucun KPI dérivé ; `v_tax_summary` inutilisable (compte Z en pertes) | S | L1 (AN-13, 9 tuiles, Sharpe → SUMMARY) |
| F02 | En-tête compte (nom, n°, broker, devise, starting balance, n trades) | Dashboard, Trades | P2 | partiel — cartes affichent capital/mode/pnl ; starting balance = `params.json.sizing.capital_initial` | S | L2 (AN-27) |
| F03 | Max drawdown + recovery factor (+ DD courant et % récupéré, dits à 44:39) | KPI + SUMMARY | P1 | non | M | L1 (AN-14) |
| F04 | Sharpe (full / annualisé) + Sortino | KPI + SUMMARY | P2 | non | M | L2 (AN-26, sur R) |
| F05 | Courbe de solde (aire, pointillé starting balance, axe daté, tooltip, animation) | Dashboard + Analysis | P1 | partiel — `curveSvg` polyline sans axe/tooltip | M | L1 (AN-15) |
| F06 | Courbe de drawdown (aire négative, bascule par cases) | Analysis | P1 | non | M | L1 (AN-16) |
| F07 | Heatmap P&L année × mois (€ + %, totaux, tooltip) | Analysis | P1 | partiel — `aggregates.month` liste plate | M | L1 (AN-19) |
| F08 | P&L par mois — barres | Dashboard | P2 | partiel — données, pas de barres | S | L2 (AN-20) |
| F09 | Donut WIN / LOSS | Dashboard | P3 | non | S | non repris (doublon tuile) |
| F10 | P&L par symbole — barres horizontales | Dashboard + Analysis | P1 | non — aucun agrégat par symbole | S | L1 (AN-21, par instance) |
| F11 | P&L par jour de semaine | Dashboard + Analysis | P2 | non | S | L2 (AN-23, + par heure) |
| F12 | Distribution des P&L par trade | Analysis | P2 | non | S | L2 (AN-24, en R) |
| F13 | P&L par stratégie — barres | Analysis | P2 | partiel — `pnl_chf` par carte | S | L2 (AN-22) |
| F14 | SUMMARY VOLUME / P&L / RISK | Analysis | P2 | partiel — `v_tax_summary` par année | S | L2 (AN-25) |
| F15 | SUMMARY streaks + holding time (« losing streak was 12 ») | Analysis | P1 | non | S | L1 (AN-25 SÉRIES) |
| F16 | SUMMARY BALANCE & COSTS | Analysis | P3 | partiel — commission/swap agrégés | S | L3 (AN-25 SOLDE & COÛTS) |
| F17 | Barre de 7 filtres, listes dépendantes, Clear, recalcul instantané | Analysis + Trades | P1 | partiel — `closed_trades()` filtre strategy/instance/mode/dates ; aucune UI | M | L1 (AN-4…AN-9) |
| F18 | Journal tabulaire 16 colonnes, paginé (déduit), éditable | Trades | P2 | partiel — `tradesTable` 50 lignes sans tri/pagination | M | L2 (AN-28/29, lecture seule) |
| F19 | Import MT5 (script + fichier 15 champs, dédoublonnage ticket) | Trades > modale | P1 | non (par conception, UI-7) | M | L1 sous forme **adaptateur lecture seule** journaux (D-AN-3) ; projection écrite = SPEC_ledger v1.1 |
| F20 | Catalogue magic → nom de stratégie, bucket UNASSIGNED | Strategies (non ouverte) | P3 | oui — manifest ; divergence magic **non** calculée par `build_niveaux` | S | L3 (groupe « magic divergent », AN-22) |
| F21 | Print / Save as PDF | Analysis | P3 | non | S | L3 (`@media print`, AN-32) |
| F22 | Thème clair + langue EN/DE | sidebar | P3 | non | S | non repris |
| F23 | Correlation | non ouverte | P3 | non | M | non repris (à spécifier sur demande) |
| F24 | Backtest comparison | non ouverte | P3 | partiel — schéma `mode`/`run_id`/`backtest_runs` prêt | M | non repris ici — spec propre recommandée (CUTOVER) |
| F25 | Monte Carlo | non ouverte | P3 | non | M | non repris |
| F26 | Logs / Settings | non ouvertes | P3 | oui (`/services`, manifest) | S | non repris |
| F27 | Positions ouvertes (absentes de Trade Buddy, vues dans MT5 s000) | — | P2 | partiel — `open_position` status.json | S | L2 (AN-30, bonus tBot) |

Décompte : P1 = 9 (F01, F03, F05, F06, F07, F10, F15, F17, F19) · P2 = 9 (F02, F04, F08,
F11, F12, F13, F14, F18, F27) · P3 = 9 (F09, F16, F20-F26). Lots : L1 = 9, L2 = 9, L3 = 3
retenues (F16, F20, F21) + 6 non reprises.

## 5. Manques de données côté tBot (et comment les combler)

| # | Manque | Impact | Obtention (décision SPEC_analytics-trades) |
|---|---|---|---|
| 1 | **Ledger vide** (0 ligne `trades`, `equity_snapshots`) ; données réelles dans `C:\db\tradingBot\{gold_forward,s13_forward,s20_forward,alexg_paper}\journal.csv` (gold 9 clos, s13 2 clos arm OBSERVATION, s20 0 clos / 2 ouverts, alexg 3 clos schéma étendu, macd_ai vide) | Sans source, page vide | Adaptateur lecture seule journaux → format `closed_trades()` (D-AN-3) ; projection écrite + index unique `(run_id, source_ref)` = SPEC_ledger v1.1 (pré-requis parallèle, pas bloquant) |
| 2 | **Starting balance** par instance absente du ledger (`manifest.capital_initial` n'existe pas ; `status.json.capital` est le capital courant) | Courbe, DD %, % mensuels | `studies/<étude>/params.json` → `sizing.capital_initial` (10 000, **par arm** pour s13/s20) ; repli `strategy_state.allocated_capital`, puis premier `account_balance` ; sinon base 0 et % à `null` (§3.3) |
| 3 | **Horodatage** `bar_time` naïf en heure serveur MT5 ; `_iso_utc` prend un naïf pour de l'UTC | weekday, mois, durée décalés de 2-3 h | Offset broker-wide +3 (été UE) / +2 (hiver), convention `core/data/source.py:25-30` ; garde-fou `bar_time_utc ≤ measured_at_utc` (§3.2) |
| 4 | **Commission / swap** absents des journaux (coût spread + slippage fondu dans `pnl_ccy`) | SOLDE & COÛTS | `commission = swap = 0` ; `edge_cost_ccy = 2 × edge_cost_of(spec) × risk_ccy / risk_distance` calculé depuis `params.json.spec` (§3.2) |
| 5 | **Devise** non nommée dans les journaux ni `params.json` | Scission par devise | Constante `CHF` de l'adaptateur (DF-9) ; jamais d'addition inter-devises |
| 6 | **Instance id** : `declared_instances()` traite XAUUSD comme paire → `S011.XAU-USD` (pas `S011.XAUUSD`) | Rattachement aux cartes UI | Réutiliser la fonction de `state.py`, pas une règle recopiée (§3.2) |
| 7 | **Filtres** symbol / side / weekday / magic / exit_reason absents de `closed_trades()` | F17 | Filtrage Python dans `analytics.py` (D-AN-2) |
| 8 | **Métriques dérivées** inexistantes (win rate, PF, avg, expectancy, DD, recovery, Sharpe, streaks, holding, best/worst, répartitions, distribution) ; `v_tax_summary` compte `net ≤ 0` en pertes | F01-F15 | Tout recalculé dans `analytics.py` depuis les lignes §3.1 (AN-13…AN-26) |
| 9 | **Série d'équité / drawdown** : `equity_snapshots` vide, `drawdown_pct` jamais écrit, `equity_curve()` sans filtre mode | F05, F06 | Série reconstruite par trade (base + cumul net), une seule série pour KPI / courbe / SUMMARY (D-AN-9) ; `equity_points` doit passer `mode` |
| 10 | **R multiple** non stocké | Tuile R, distribution, Sharpe | `meta_json.pnl_r` (journaux), repli `net_pnl / risk_amount` (§3.1) |
| 11 | **Durée et streaks** non stockées (`bars_held` du backtester non persisté) | F15 | `close_time − open_time` après conversion UTC ; suites consécutives (AN-25) |
| 12 | **Rendu UI** : `curveSvg` = polyline sans axe/tooltip/aire ; `tradesTable` 10 colonnes sans tri/pagination | F05-F13, F18 | Helpers SVG maison dans le seul `app.js` (D-AN-13) |
| 13 | **Visibilité s13 / s20** : `study_state()` ne lit pas le format `arms{}` ; `s20_forward` absent de `LEGACY_STUDIES` | Cartes fausses (s13) / absentes (s20) | Correction incluse en L1 (`state.py`) |
| 14 | **Divergence magic ≠ manifest** non calculée (UNASSIGNED) | F20 | Groupe « magic divergent » + `magic_ok` par ligne dans `analytics.py` (L3) |
| 15 | **Flux de capital** (dépôts / retraits) non modélisés — même limite que Trade Buddy | Mode LIVE futur | Hors scope jusqu'à TCK-006 (D-AN-18) |
| 16 | **P&L flottant / positions ouvertes** : Trade Buddy ne les a pas ; tBot les a dans status.json | F27 | Section positions ouvertes sans P&L flottant, hors statistiques (D-AN-17) |
| 17 | **MAE / MFE** : ni ledger ni journaux | non requis pour la parité | Calculables hors ligne par rejeu `bars_cache/<SYM>_<TF>_1855d.pkl` entre OPEN et CLOSE — noté, pas traité |
| 18 | **Historique broker réel / import MT5** | F19 côté Trade Buddy | Hors périmètre jusqu'à TCK-006 ; les 15 champs du format Trade Buddy ont tous une colonne `trades.*` (`ticket` NULL pour les forwards) |

## 6. Points de contrôle pour les tests (valeurs lues à l'écran)

Réutilisables comme oracles de formule (pas de données brutes disponibles, donc en tests
synthétiques équivalents) :

- Compte entier : N 4,371 · W 2,271 · L 2,099 · Z 1 · net 99,537.31 · PF 1.16 · DD 22,050.64 ·
  recovery 4.51 · avg win 312.35 · avg loss −290.52 · expectancy TB 22.71 vs net/N 22.77.
- Range Breakout : N 2,316 · W 1,154 · L 1,161 · Z 1 · expectancy TB 10.91 vs net/N 11.02.
- DE40 : N 205 · W 131 · L 74 · net +6.44 · PF 1.00 · expectancy TB −0.39 · win rate 63.9 %.
- TT × USTEC : N 70 · W 40 · L 30 · PF 1.76 · DD 2,127.52 · recovery 2.95 · avg +363.70 /
  −275.42 · expectancy +89.79 (= net/N, Z = 0).
- RB × US30 : N 221 · W 97 · L 124 · PF 0.86 · DD 2,715.33 · recovery −0.56 · expectancy −6.92.
- GBPUSD : net −8,201.71 · DD 11,900.88 · recovery −0.69.
- ATR : N 55 · L29/S26 · W 16 · L 39 · win rates 29.1 / 27.6 / 30.8 % · gross +5,925.40 /
  −3,661.92 · PF 1.62 · best +392.15 · worst −112.93 · DD 1,138.55 · recovery 1.99 · sharpe
  0.19 · annualisé TB 1.45 · sortino 0.30 · streaks 5 / 12 · holding 12h13 · final 52,263.48.
