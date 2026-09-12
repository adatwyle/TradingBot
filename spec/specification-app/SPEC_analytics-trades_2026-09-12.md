# SPEC — Analyse des trades (module « analyse », parité Trade Buddy)

**Version** : 1.0.0 — 2026-09-12 · **Auteur** : cc-spec (rédaction initiale cc-support sur directive Adrian 2026-09-12, à contresigner par cc-spec) · **Statut** : prête pour implémentation — les défauts §9 restent modifiables par Adrian sans nouvelle version tant que L1 n'est pas livré
**Sources** : directive Adrian 2026-09-12 (« à partir de 37:10 René Balke visualise son TradeBuddy — passe à travers chaque image, analyse les fonctionnalités développées et développe-les sur l'UI tBot ») ; inventaire écran par écran `docs/sources/renebalke/TRADEBUDDY_analyse-ecrans_2026-09-12.md` (28 captures, vidéo [qgsi-u0kOVw] 36:50 → 48:06) ; SPEC_ui-dynamique (D-UI-1…5, UI-7, UI-8) ; SPEC_ledger (LG-10…14) ; input-adrian 03, 04, 05 ; journaux forward `C:\db\tradingBot\<étude>\journal.csv`.
**Implémente** : `app/server/analytics.py` (nouveau), `app/server/journal_adapter.py` (nouveau), `app/server/app.py` (+ routes), `app/server/ui/analytics.html` (nouveau), `app/server/ui/app.js` + `style.css` (helpers SVG), liens `<nav>` des trois shells existants, `app/tests/test_server_analytics.py` + `app/tests/test_server_journal_adapter.py` (nouveaux).
**Amende** : SPEC_ui-dynamique UI-7/UI-8 (liste des routes et des shells : +1 page `/analytics`, +3 routes API, 4 shells) — amendement v1.1 porté par la présente spec, pas de réécriture de SPEC_ui-dynamique.

## 1. Objectif

Donner à tBot l'équivalent de Trade Buddy (bmtrading.de, outil de René Balke) : une page
« analyse » où **tout sous-ensemble de trades clos** (période × mode × stratégie × instance
× symbole × sens × jour × raison de sortie) est rejoué instantanément en KPI, courbe de
solde / drawdown, heatmap mensuelle, répartitions et bloc de synthèse — la lecture que
René fait en 10 minutes de son compte (stratégie → symbole → drawdown → losing streak),
disponible sur les stratégies tBot dès aujourd'hui, ledger vide compris, grâce à un
adaptateur **lecture seule** sur les journaux forward.

Ce que tBot ajoute par rapport à Trade Buddy : le R multiple (stop obligatoire, R3),
la raison de sortie, le drawdown courant et sa fraction récupérée, les streaks courants,
les positions ouvertes, la séparation stricte des modes et des devises.

Ce que tBot ne reprend pas (décision, pas oubli) : import MT5 par fichier, édition /
suppression de trades, bouton PDF, thème clair, langue DE, pages Correlation / Backtest
comparison / Monte Carlo (contenu jamais montré — à spécifier séparément sur demande Adrian).

## 2. Décisions tranchées

| # | Décision | Motivation (1 ligne) |
|---|----------|----------------------|
| D-AN-1 | Une **page globale** `/analytics` (shell `ui/analytics.html`, `<body data-page="analytics">`) + lien `analyse` dans les 3 `<nav>` existants ; la page stratégie gagne un lien « analyse détaillée » pré-filtré | Trade Buddy vit par ses filtres : une seule page recalculée vaut mieux que des vues par stratégie figées ; la page stratégie reste le drill-down d'état, l'analyse le drill-down de performance. |
| D-AN-2 | Calculs **en Python, à chaque requête**, dans `server/analytics.py` sur des lignes au format `Ledger.closed_trades()` ; pas de SQL analytique, pas d'extension du ledger en v1 | UI-1 (pas de cache), volume < 10 k trades pour des années, formules lisibles et testables unitairement ; le ledger reste le socle (INDEX inv. 6) sans grossir. |
| D-AN-3 | **Adaptateur journaux forward** `server/journal_adapter.py` : lit `db_dir()/<étude>/journal.csv` + `project_root()/studies/<étude>/params.json` + manifest et produit des lignes au format `closed_trades()` en mémoire — **n'écrit jamais** (ni ledger, ni journal) | Le ledger est vide (0 ligne) ; la seule donnée réelle est dans 4 journaux CSV ; l'UI doit être utile sans attendre la projection écrite (SPEC_ledger v1.1, ticket séparé) ; UI-7 impose la lecture seule. |
| D-AN-4 | Source `auto` = **union** ledger ∪ journaux, dédoublonnée sur `(run_id, source_ref)` (`source_ref` = `trade_id` du journal) — la ligne ledger prime | Quand la projection écrite existera, les trades passeront côté ledger sans doublon ni bascule ; avant, tout vient des journaux. |
| D-AN-5 | Filtre **`mode` à choix unique**, défaut `PAPER` ; BACKTEST / PAPER / LIVE ne sont **jamais** additionnés ; un « compte » Trade Buddy ≡ `mode` × `currency` | Une courbe qui mélange backtest et paper ment (CUTOVER.md, « BACKTESTED = mesuré, pas validé »). |
| D-AN-6 | Tout résultat est **scindé par devise** (`by_currency: {"CHF": {...}}`), jamais additionné (LG-14) ; devise des journaux forward = constante `CHF` de l'adaptateur | Règle ledger existante ; les journaux ne nomment pas la devise, status.json parle `pnl_chf`. |
| D-AN-7 | **Trades à net = 0** : comptés dans N, ni gagnants ni perdants ; `win_rate = W / N` ; `expectancy = net / N` | Convention Trade Buddy pour N et W (vérifié 131/205) ; son expectancy compte les zéros côté perte (22.71 ≠ 22.77) — tBot prend le net/N, plus honnête, et documente l'écart. |
| D-AN-8 | **Base de la courbe filtrée** : `curve_base=auto` → « capital » si toutes les instances du sous-ensemble ont une starting balance connue (§3.3), sinon « zéro » (cumul net) ; override `zero` / `capital` explicite | Trade Buddy rejoue tout sous-ensemble depuis 50 000 € fixes : comparable mais synthétique ; tBot n'invente pas un capital pour un sous-ensemble, et l'affiche quand il est réel. |
| D-AN-9 | **Drawdown** à granularité trade (même série pour le KPI et la courbe) ; `dd_pct` **relatif au pic** ; tooltips et SUMMARY cohérents avec le KPI | Trade Buddy diverge entre KPI (par trade) et tooltip (par jour, / starting balance) — l'écart GBPUSD 11 900 vs 11 717 en témoigne ; tBot ne doit pas avoir deux drawdowns. |
| D-AN-10 | **Sharpe / Sortino sur le R par trade** (`pnl_r`), écart-type d'échantillon, annualisation × √(trades par an) ; nul si moins de 20 trades ou R indisponible | Trade Buddy annualise × √N trades (formule à ne pas copier) ; le R est toujours défini en tBot (stop obligatoire) et rend les stratégies comparables entre elles. |
| D-AN-11 | **Clé jour de semaine / heure** = `open_time` (jour d'entrée) par défaut, `weekday_key=close` en option | Les stratégies tBot sont EOD / intraday (Range Breakout, GEX) : le jour d'entrée est celui de la décision. |
| D-AN-12 | **Distribution en R** (bins fixes de 0,5 R sur [−3 R, +5 R], bornes ouvertes) par défaut, distribution en devise (16 bins équirépartis) en bascule | Le R est la mesure native tBot ; les bins fixes rendent deux stratégies comparables. |
| D-AN-13 | Graphiques = **SVG maison dans le seul `app.js`** (D-UI-3, UI-8) : `lineChart`, `areaChart`, `barChart`, `heatmapTable`, `kpiTiles` ; aucune lib, aucun `http(s)://` | Test bloquant `test_assets_served_without_cdn` ; continuité de style (sombre, monospace). |
| D-AN-14 | Filtres portés par la **query string** (repeated keys) et reflétés dans l'URL (`history.replaceState`) ; polling 10 s, re-rendu seulement si le JSON a changé | F5-proof, partageable, sans état serveur ; évite de rejouer l'animation à chaque poll. |
| D-AN-15 | Journal des trades = **lecture seule, paginé côté serveur** (`page`, `limit` défaut 200, max 1000), tri serveur `close_time desc` fixe, tri client sur la page courante | UI-7 : ni édition, ni suppression, ni import ; le ledger est append-only. |
| D-AN-16 | Serveur **jamais en 500** : ledger absent, journal absent, illisible ou chaîne altérée ⇒ sous-ensemble vide + `warnings[]` explicites | Règle existante (`app.py:50-51`) ; un journal altéré doit se lire comme alerte, pas comme panne. |
| D-AN-17 | Positions ouvertes (ledger `close_time IS NULL` + journaux OPEN sans CLOSE) affichées dans une section dédiée, **hors** de toutes les statistiques | Trade Buddy ne montre que le clôturé ; tBot supervise du vivant (status.json) — l'analyse le montre sans le mélanger au réalisé. |
| D-AN-18 | Flux de capital (dépôts / retraits) **hors scope** jusqu'au pont broker (TCK-006) ; la courbe est toujours « capital initial + cumul net » | Même limite que Trade Buddy (courbe ≈ 149 537 € vs solde MT5 19 738 €) ; sans compte réel, rien à modéliser. |

## 3. Contrat de données

### 3.1 Ligne de trade (format unique d'entrée des calculs)

Toutes les fonctions de `analytics.py` consomment une `list[dict]` dont chaque élément
porte **exactement** les clés de `Ledger.closed_trades()` (31 colonnes + `instance_id`,
SPEC_ledger LG-10) plus deux clés ajoutées par la couche source :

- `source` : `"ledger"` | `"journal"` ;
- `source_ref` : `str` — clé d'idempotence (`ticket` ou `id` côté ledger ; `trade_id` côté journal) ;
- `pnl_r` : `float | None` — R multiple : `meta_json.pnl_r` si présent (journaux), sinon
  `net_pnl / risk_amount` si `risk_amount` > 0, sinon `None` ;
- `arm` : `str | None` — `meta_json.arm` (`PRIMARY` / `OBSERVATION` / `MECH` / `SHADOW`), `None` côté ledger sans meta.

`meta_json` est décodé en dict (`{}` si NULL ou invalide — jamais d'exception).

### 3.2 Adaptateur journaux forward (`server/journal_adapter.py`, lecture seule)

- **Catalogue fixe** (code, pas de fichier de config) : `(dossier étude, strategy_id)` =
  `gold_forward→S011`, `s13_forward→S013`, `s20_forward→S020`, `alexg_paper→S093`,
  `macd_ai_paper→S012` ; `s14_sentiment` exclu (pas de journal de trades). Le catalogue
  est exposé par `STUDIES` et réutilisé pour aligner `LEGACY_STUDIES` de `state.py`
  (s20 y manque aujourd'hui — correction incluse dans L1).
- **Entrées lues** (jamais écrites) : `db_dir()/<étude>/journal.csv`,
  `db_dir()/<étude>/state.json` (`started_at`), `project_root()/studies/<étude>/params.json`
  (`sizing.capital_initial`, `spec.symbol` ou `instrument`, `timeframe`,
  `spec.{spread_pips,pip,slippage_pips}`), `project_root()/strategies/S0NN_*/manifest.yaml`
  (`magic_number`, `version`). Fichier absent ⇒ étude ignorée + warning ; jamais de création.
- **Intégrité** : la chaîne SHA-256 (`chain`) est vérifiée en lecture (même algorithme que
  `verify_journal` des études, réimplémenté sans importer le code d'étude) ; chaîne rompue ⇒
  lignes servies quand même, `warnings` contient `journal altéré : <étude>` et
  `source.studies[<étude>].chain_ok = false`.
- **Événements** : `OPEN` / `CLOSE` uniquement ; `SHADOW_OPEN`, `SHADOW_CLOSE`, `DECISION`
  (alexg) ignorés. Appariement sur `trade_id` + `symbol` + `arm` (colonnes absentes
  = constante étude). `OPEN` sans `CLOSE` ⇒ position ouverte (§3.4).
- **Instance** : `instance_id` dérivé de `symbol` par la **même règle** que
  `declared_instances()` (`state.py:139-161`, `_PAIR_RE = ^[A-Z]{6}$` ⇒ `S011.XAU-USD`,
  `S013.EUR-JPY`, `S020.USD-JPY`) — la fonction est importée, pas recopiée.
- **Horodatage** : `bar_time` (naïf, heure serveur MT5) → UTC par soustraction de
  l'offset broker : **+3 h en heure d'été européenne, +2 h sinon** (règle UE : dernier
  dimanche de mars 01:00 UTC → dernier dimanche d'octobre 01:00 UTC), constante
  `SERVER_OFFSET_RULE` injectable pour les tests ; garde-fou `bar_time_utc ≤ measured_at_utc`
  sinon warning (ligne conservée). Convention identique à `core/data/source.py:25-30`.
- **Mapping** (une ligne `trades` par paire OPEN/CLOSE) : `strategy_id` (catalogue) ;
  `instance_id` (règle ci-dessus) ; `strategy_version` = `version` manifest sinon `"study"` ;
  `magic_number` = manifest sinon `0` ; `mode = "PAPER"` ; `run_id` = dossier étude ;
  `symbol` ; `timeframe` (params) ; `ticket = None` ; `side` ; `volume_lots = size_lots` ;
  `open_time` = `bar_time`(OPEN) UTC ; `open_price = entry_price` ; `close_time` =
  `bar_time`(CLOSE) UTC ; `close_price = exit_price` ; `stop_price` ; `target_price` ;
  `exit_reason` (`SL`/`TP`, sinon `MANUAL`) ; `gross_pnl = net_pnl = pnl_ccy` ;
  `commission = swap = 0` ; `currency = "CHF"` ; `signal_reason` = `reason` (alexg) sinon
  `None` ; `risk_distance = |entry_price − stop_price|` ; `risk_amount = risk_ccy` ;
  `account_balance = capital_after`(OPEN) ; `meta_json = {arm, trade_id, pnl_r,
  capital_after, measured_at_utc_open, measured_at_utc_close, edge_cost_ccy, chain_ok}` ;
  `source = "journal"` ; `source_ref = trade_id`.
- **Coût de bord** : `edge_cost_ccy = 2 × (spread_pips × pip / 2 + slippage_pips × pip) ×
  risk_ccy / risk_distance` calculé depuis `params.json.spec` (formule `edge_cost_of`,
  `forward_step.py:297-300`, payé aux deux extrémités) ; `None` si `spec` incomplet.
- **Starting balance** : `capital_initial(instance_id) = params.json.sizing.capital_initial`
  (10 000 pour gold, s13, s20 — **par arm**, donc par instance) ; horodatage de départ =
  `state.json.started_at`.
- API : `journal_closed_trades(*, studies=None) -> list[dict]`,
  `journal_open_trades(*, studies=None) -> list[dict]`,
  `journal_capital_initial() -> dict[instance_id, float]`,
  `journal_report() -> {studies:{<étude>:{strategy_id, rows, closed, open, chain_ok, path}}, warnings:[…]}`.

### 3.3 Starting balance (base des % et de la courbe « capital »)

Résolution par instance, dans l'ordre : (1) `journal_capital_initial()` ; (2) ledger
`strategy_state.allocated_capital` si non nul (par stratégie, appliqué à ses instances) ;
(3) `account_balance` du **premier** trade clos de l'instance (ordre `open_time`) s'il est
non nul ; (4) inconnue. Une stratégie à N instances a pour base la **somme** des bases de
ses instances (s13/s20 : 10 000 par arm, jamais 10 000 pour la stratégie).

### 3.4 Position ouverte (D-AN-17)

`{source, strategy_id, instance_id, mode, symbol, side, open_time, open_price, stop_price,
target_price, volume_lots, risk_amount, arm, age_h}` ; jamais de P&L flottant (non
calculable sans cotation — le status.json de l'instance reste la source du vivant).

### 3.5 Conventions transverses

- Dates de filtre `from` / `to` : **date locale inclusive** sur `close_time` (LG-10, `_to_local`).
- Buckets mois / jour / weekday / heure : date locale (`local_tz` seam), jamais UTC brut.
- Tri de référence de toutes les séries : `close_time` croissant, puis `id`/`source_ref`.
- Arrondis : montants à 2 décimales, ratios à 2, R à 2, pourcentages à 2 — **à la sortie
  JSON seulement**, jamais dans les calculs intermédiaires.
- Aucun résultat n'additionne deux devises, deux modes ou le clôturé et l'ouvert.

## 4. Exigences — navigation, filtres, sources

### Navigation

- **AN-1** — Route `GET /analytics` → `send_from_directory(UI_DIR, "analytics.html")` ;
  lien `<a href="/analytics">analyse</a>` ajouté dans les trois shells existants
  (`index.html`, `strategy.html`, `services.html`) et dans le nouveau shell. UI-8 devient :
  4 shells + un seul `app.js` + `style.css`.
- **AN-2** — Page stratégie : sous le titre, lien « analyse détaillée » →
  `/analytics?mode=<mode courant de la stratégie>&strategy=<S0NN>` ; par instance, lien →
  `…&instance=<S0NN.XXX-YYY>`.
- **AN-3** — Bandeau UI-6 (`#stamp`, `#conn`) présent sur `/analytics` ; polling 10 s ;
  le front compare le JSON reçu au précédent (`JSON.stringify`) et ne re-rend que s'il diffère.

### Filtres (F17)

- **AN-4** — Paramètres de `GET /api/analytics` et `GET /api/analytics/trades`, tous
  optionnels, **repeated keys** pour les multi-valeurs (`?strategy=S011&strategy=S013`) :

  | Paramètre | Cardinalité | Domaine | Défaut | Prédicat |
  |---|---|---|---|---|
  | `mode` | 1 | `BACKTEST` / `PAPER` / `LIVE` | `PAPER` | `trade.mode == mode` |
  | `strategy` | n | `S0NN` | tous | `strategy_id ∈` |
  | `instance` | n | `S0NN.XXX-YYY` | tous | `instance_id ∈` |
  | `symbol` | n | ex. `XAUUSD` | tous | `symbol ∈` |
  | `side` | n | `LONG` / `SHORT` | tous | `side ∈` |
  | `weekday` | n | `mon`…`sun` | tous | `weekday(clé AN-6) ∈` |
  | `exit_reason` | n | `SL`/`TP`/`TRAIL`/`MANUAL`/`HALT`/`EOD` | tous | `exit_reason ∈` |
  | `arm` | n | `PRIMARY`/`OBSERVATION`/`MECH`/`SHADOW`/`none` | tous | `arm ∈` (`none` = sans arm) |
  | `magic` | n | entier | tous | `magic_number ∈` |
  | `from`, `to` | 1 | `YYYY-MM-DD` | ouvert | date locale de `close_time` ∈ [from, to] |
  | `source` | 1 | `auto` / `ledger` / `journals` | `auto` | D-AN-4 |
  | `curve_base` | 1 | `auto` / `zero` / `capital` | `auto` | D-AN-8 |
  | `weekday_key` | 1 | `open` / `close` | `open` | D-AN-11 |
  | `dist_unit` | 1 | `r` / `ccy` | `r` | D-AN-12 |

  Valeur hors domaine ⇒ `400` JSON `{"error": "paramètre invalide : <nom>=<valeur>"}` —
  seule exception à « jamais d'erreur » (une URL fausse n'est pas une panne de supervision).
- **AN-5** — Prédicat **AND** entre paramètres, **OR** à l'intérieur d'un paramètre ;
  aucune valeur = pas de contrainte (« All »).
- **AN-6** — `weekday(trade)` = jour local de `open_time` si `weekday_key=open`, de
  `close_time` si `close`. Même clé pour le filtre et pour la répartition F11.
- **AN-7** — **Listes dépendantes** : `filters.options.<param>` = valeurs distinctes du
  sous-ensemble filtré par **tous les autres** paramètres (Trade Buddy : seuls DE40/US30/
  USTEC proposés sous Go Long). Ordre : `strategy`, `instance`, `symbol` alphabétiques ;
  `weekday` lun→dim ; `exit_reason`, `side`, `arm` dans l'ordre du domaine.
- **AN-8** — Front : barre de filtres en tête de page (mode = boutons radio ; multi =
  `<details>` à cases à cocher, libellé « tous » ou « N choisis » ; dates = `<input type=date>` ;
  bouton « effacer les filtres » qui ne remet **pas** `mode` à zéro). Tout changement
  réécrit l'URL (`history.replaceState`) et relance un fetch immédiat.
- **AN-9** — Filtre de statut d'instance (bonus, absent de Trade Buddy) : les instances
  `RETIRED` (manifest) apparaissent dans les options avec suffixe ` (retired)` et restent
  incluses par défaut (René garde EURUSD arrêté dans son analyse, 43:10).

### Sources

- **AN-10** — `source=auto` : lignes ledger (`open_ledger()` de `state.py`, `None` ⇒ aucune
  ligne, **jamais de création de DB**) ∪ lignes journaux ; doublon `(run_id, source_ref)` ⇒
  ligne ledger conservée, journal écartée, compteur `source.dedup`.
- **AN-11** — `source.ledger_rows`, `source.journal_rows`, `source.studies{}` (rapport §3.2)
  et `warnings[]` sont toujours présents dans la réponse ; ledger absent ⇒
  `warnings ∋ "ledger absent"`, pas d'erreur.
- **AN-12** — Le serveur ne lit jamais `secrets/`, ne lit jamais la valeur d'un token, ne
  crée ni dossier ni fichier, n'exécute aucun code d'étude (`forward_step.py` n'est pas importé).

## 5. Exigences — fonctionnalités (catalogue F01-F27)

Priorité = lot de livraison (§7). « Trade Buddy » rappelle ce qui est reproduit,
« tBot » ce qui est ajouté. Toutes les formules s'appliquent au sous-ensemble filtré
**d'une devise** ; T = trades clos triés (§3.5), N = |T|, W = {net > 0}, L = {net < 0},
Z = {net = 0} (N = W + L + Z).

### 5.1 Bandeau KPI — F01 (P1) + F03 (P1) + F04 (P2)

- **AN-13** — 9 tuiles, dans cet ordre, valeur principale + sous-libellé, classe `pos`/`neg`
  selon signe (vert/rouge, palette `style.css`) :

  | Tuile | Valeur | Sous-libellé | Formule |
  |---|---|---|---|
  | TRADES | N | `L n · S n` | comptage par `side` |
  | TAUX DE GAIN | `win_rate` | `W / L` (et `· Z à 0` si Z > 0) | `W / N` (0 si N = 0) |
  | P&L NET | `net_pnl` | `Ø par trade` | `Σ net` ; `net / N` |
  | PROFIT FACTOR | `profit_factor` | `gains / pertes` | `gross_profit / |gross_loss|` ; `null` si L = 0 (affiché `∞`) |
  | DRAWDOWN MAX | `max_drawdown` | `récup. x` | §AN-14 ; `recovery = net / max_drawdown` (`null` si DD = 0) |
  | DD COURANT | `current_drawdown` | `récupéré p %` | §AN-14 |
  | GAIN MOY. / PERTE MOY. | `avg_win` `avg_loss` | — | `gross_profit / W` ; `gross_loss / L` (`null` si W ou L = 0) |
  | ESPÉRANCE | `expectancy` | `par trade` | `net / N` (D-AN-7 ; **pas** la formule Trade Buddy) |
  | R MOYEN (tBot) | `avg_r` | `Σ R` | `Σ pnl_r / N_r` sur les trades à R connu ; `sum_r` |

  Sharpe (F04) n'est **pas** une tuile (jamais commenté par René) : il vit dans SUMMARY (AN-26).
- **AN-14** — Série de solde et drawdown (F03, F05, F06) : `B_0 = base` (`capital` connu
  ou 0 selon `curve_base`), `B_k = B_{k−1} + net_k` ; `P_k = max(B_0..B_k)` ;
  `dd_k = B_k − P_k ≤ 0` ; `dd_pct_k = dd_k / P_k` si `P_k > 0` sinon `null` ;
  `max_drawdown = max_k(P_k − B_k)` ; `max_dd_pct = (P − B)/P` au **même** indice k que
  `max_drawdown` ; `current_drawdown = P_N − B_N` ; `recovered_pct = 1 − current_drawdown /
  max_drawdown` **si le creux du DD max n'a pas encore été effacé**, sinon `null`
  (René, 44:39 : « still in this drawdown… recovered more than 50 % ») ; `dd_duration_days`
  (pic → creux du DD max) et `recovery_days` (creux → premier retour au pic, `null` si en cours).
  Le KPI, la courbe et le SUMMARY partagent **cette** série (D-AN-9). En base zéro, les
  `%` sont `null` (pas de pic significatif) et la tuile affiche « — ».

### 5.2 PERFORMANCE — courbe de solde F05 (P1) et drawdown F06 (P1)

- **AN-15** — Un graphique `lineChart` 100 % largeur × 260 px : série `balance` (aire
  dégradée bleue `--blue`), ligne pointillée horizontale à `base` libellée (`10 000 CHF`
  ou `0`), axe Y auto (min/max de la série, pas rond, 5 graduations), axe X = 8 dates
  `yy.mm.dd` équiréparties entre première et dernière `close_time` locale, tooltip DOM au
  survol (ligne verticale + point + `dd.mm.yy — solde 10 179.06 CHF`). Cases à cocher
  « solde » / « drawdown » exclusives-tolérantes comme Trade Buddy (les deux décochées
  = zone vide « rien à tracer »).
- **AN-16** — Série `drawdown` : `areaChart` rouge (`--red`) sous 0, axe Y négatif auto,
  tooltip `dd.mm.yy — drawdown −1 138.55 CHF (−2.27 %)` avec le `dd_pct` **relatif au pic**
  (D-AN-9). Retour à 0 = nouveau plus haut.
- **AN-17** — Points = un par trade clos ; au-delà de 2 000 points, décimation « dernier
  solde du jour » côté serveur (`curve.decimated = true`). Animation de tracé (transition
  CSS `stroke-dashoffset` 400 ms) uniquement quand les filtres changent (D-AN-14).
- **AN-18** — Payload : `curve: {base, base_kind: "capital"|"zero", points: [[iso_utc,
  balance, drawdown, dd_pct], …], decimated}`.

### 5.3 P&L PAR MOIS — heatmap F07 (P1) et barres F08 (P2)

- **AN-19** — `heatmapTable` : lignes = années présentes, colonnes JAN…DÉC + TOTAL, ligne
  TOTAL en bas ; cellule = montant arrondi (ligne 1) + `%` (ligne 2) + `Σ R` (ligne 3, tBot),
  fond vert/rouge d'intensité proportionnelle à `|montant| / max|montant|` (4 paliers CSS),
  « – » si 0 trade. Tooltip cellule : `2026 juin · +7 719.62 CHF · 147 trades · +3.2 R`.
  Formules : `pnl(y,m) = Σ net` des trades dont `close_time` local ∈ (y,m) ; `n(y,m)` ;
  `r(y,m) = Σ pnl_r` ; `pct(y,m) = pnl / base` **non composé** si `base_kind = capital`,
  sinon `null` (affiché « — ») ; TOTAL année = Σ mois ; **TOTAL colonne-mois = Σ années**
  (Trade Buddy laisse ces cellules vides — tBot les calcule) ; TOTAL×TOTAL = Σ global
  (= `net_pnl` F01, test AN-T6).
- **AN-20** — `barChart` vertical signé « P&L par mois » (F08) sous la heatmap, une barre
  par mois calendaire de la plage (mois sans trade = barre nulle), étiquettes d'axe un
  mois sur deux `yy.mm`, tooltip montant + n trades. Mêmes données que AN-19
  (`by_month: [{month, n_trades, net, sum_r, pct}]`).

### 5.4 Répartitions — F10 (P1), F13 (P2), F11 (P2), F12 (P2)

- **AN-21** — « P&L par instance » (F10, équivalent « by symbol ») : `barChart` horizontal
  signé trié par net décroissant, une barre par `instance_id` (repli `symbol` si
  `instance_id` NULL), étiquette = instance + net + `n · win %` ; tableau repliable
  dessous `{instance, symbol, n_trades, win_rate, net, profit_factor, sum_r, max_drawdown}`
  (DD calculé sur la sous-série de l'instance, base = sa starting balance ou 0).
  Payload `by_instance: [...]` ; `by_symbol: [...]` identique groupé sur `symbol`.
- **AN-22** — « P&L par stratégie » (F13) : `barChart` vertical signé par `strategy_id`,
  étiquette `S0NN · display_name` (manifest, repli id), sous-barres par instance (empilées
  signées). Payload `by_strategy: [{strategy_id, display_name, n_trades, net, sum_r,
  instances: [...]}]`. Trades dont `magic_number` ≠ manifest ⇒ groupe supplémentaire
  `magic divergent` (équivalent UNASSIGNED, F20 — calcul dans `analytics.py`,
  `build_niveaux` ne le fait pas).
- **AN-23** — « P&L par jour de semaine » (F11) : 7 barres lun…dim (clé AN-6) + « P&L
  par heure d'entrée » (tBot) : 24 barres, heure locale de `open_time`. Payload
  `by_weekday: [{weekday, n_trades, net, sum_r, win_rate}]`, `by_hour: [...]`.
- **AN-24** — « Distribution » (F12) : histogramme bleu `barChart` ; `dist_unit=r` : bins
  fixes `[-3,-2.5)…[4.5,5)` + `< −3` + `≥ 5` ; `dist_unit=ccy` : 16 bins équirépartis
  `[min, max]` (bin unique si min = max). Payload `distribution: {unit, bins: [{lo, hi,
  n}], n_without_r}`. Aucune narration Trade Buddy n'y est associée (« one win out of
  four » vient des tuiles).

### 5.5 SUMMARY — F14 (P2), F15 (P1), F16 (P3), F04 (P2)

- **AN-25** — Bloc `summary` en 5 colonnes clé/valeur (`.kv`), rendu sous les répartitions :

  | Colonne | Clés | Formules |
  |---|---|---|
  | VOLUME | `total, long, short, wins, losses, zeros, win_rate, long_win_rate, short_win_rate` | `long_win_rate = W_long / N_long` (`null` si 0) |
  | P&L | `net, gross_profit, gross_loss, avg_win, avg_loss, expectancy, profit_factor, best_trade, worst_trade, best_r, worst_r, sum_r, avg_r, pct_trades_ge_1r, sum_risk` | `best = max(net)`, `worst = min(net)` ; `pct_trades_ge_1r = |{pnl_r ≥ 1}| / N_r` ; `sum_risk = Σ risk_amount` |
  | RISQUE | `max_drawdown, max_dd_pct, recovery_factor, current_drawdown, recovered_pct, dd_duration_days, recovery_days, sharpe_r, sharpe_r_annual, sortino_r` | AN-14 ; AN-26 |
  | SÉRIES & DURÉE (F15) | `max_win_streak, max_loss_streak, current_streak: {kind, len}, avg_holding_h, median_holding_h, max_holding_h` | streaks sur T trié ; **Z casse les deux séries** ; `holding = close_time − open_time` en heures décimales |
  | SOLDE & COÛTS (F16) | `base, final_balance, total_commission, total_swap, total_edge_cost` | `final = base + net` (`null` si base inconnue) ; `Σ commission`, `Σ swap`, `Σ meta_json.edge_cost_ccy` (journaux) |

- **AN-26** — Sharpe / Sortino (F04, D-AN-10) sur `R = {pnl_r connus}` : `sharpe_r =
  mean(R) / std_sample(R)` ; `sortino_r = mean(R) / sqrt(mean(min(r,0)²))` ;
  `sharpe_r_annual = sharpe_r × sqrt(N_r / years)` avec `years = (dernière − première
  close_time) / 365.25 j` ; tous `null` si `N_r < 20`, `years < 30/365.25`, ou dénominateur 0.
  Sous-libellé UI : « par trade (R) · annualisé sur n trades/an ».

### 5.6 En-tête compte — F02 (P2)

- **AN-27** — Sous le titre « Analyse » : `<mode> · <n stratégies> stratégies ·
  <n instances> instances · <devise> · capital initial <Σ base ou « inconnu »> · <N> trades
  clos · source <ledger|journaux|mixte>`. Nom lisible = `display_name` manifest ; le
  « compte » Trade Buddy est remplacé par `mode` × `currency` (D-AN-5/6). Les tuiles KPI
  ne sont **jamais** masquées par un menu déroulant (défaut d'empilement Trade Buddy à
  ne pas reproduire).

### 5.7 Journal des trades — F18 (P2)

- **AN-28** — `GET /api/analytics/trades` : mêmes filtres AN-4 + `page` (≥ 1, défaut 1),
  `limit` (1…1000, défaut 200) ; réponse `{generated, version, total, page, limit,
  rows: [...]}` triée `close_time desc` ; `rows[i]` = ligne §3.1 sans `meta_json` brut
  mais avec `pnl_r`, `arm`, `source`, `holding_h`, `edge_cost_ccy`, `magic_ok` (bool).
- **AN-29** — Front : tableau `table.grid` sous le SUMMARY, colonnes `id/ticket, instance,
  sens (badge), lots, ouverture, clôture, prix ouv., prix clôt., stop, cible, sortie, brut,
  comm., swap, net, R, durée, arm, source` ; tri client par clic d'en-tête sur la page
  courante ; pagination « ‹ 1–200 / 4 371 › » ; recherche client (`<input>`) filtrant la
  page courante sur `instance`, `symbol`, `signal_reason`. Aucune action par ligne (UI-7).

### 5.8 Positions ouvertes — F27 (P2, tBot)

- **AN-30** — Section « positions ouvertes » entre SUMMARY et journal : tableau §3.4 filtré
  par `mode`, `strategy`, `instance`, `symbol`, `arm` (les autres filtres ne s'appliquent
  pas) ; vide ⇒ ligne « aucune ». Payload `open_positions: [...]` hors `by_currency`.

### 5.9 Bandeau KPI de la vue d'ensemble — F01 sur `/` (P2)

- **AN-31** — `GET /api/analytics/kpi` → `{generated, version, PAPER: {<ccy>: kpi}, LIVE:
  {<ccy>: kpi}}` (AN-13, sans filtre, source `auto`) ; la page `/` affiche au-dessus des
  niveaux un bandeau par mode non vide (`kpiTiles` réduit : trades, taux, net, PF, DD max,
  R moyen) avec lien « analyse » ; `/api/state` reste inchangé.

### 5.10 Impression — F21 (P3)

- **AN-32** — Feuille `@media print` dans `style.css` : fond blanc, texte noir, `nav`,
  `#conn`, barre de filtres et pagination masqués, SVG conservés ; pas de bouton
  (Ctrl+P). Le titre imprimé reprend l'en-tête AN-27 et l'URL des filtres.

### 5.11 Non repris (décisions)

- **AN-33** — F09 donut (doublon de la tuile), F19 import MT5 (le ledger est alimenté par
  les stratégies et par la projection ; historique broker réel = TCK-006), F22 thème clair /
  DE, F23 Correlation, F24 Backtest comparison, F25 Monte Carlo, F26 Logs / Settings
  (`/services` et `manifest.yaml` couvrent déjà) : **hors périmètre**. F23-F25 n'ont jamais
  été montrées ; F24 est jugée très pertinente pour tBot (`CUTOVER.md`) et fera l'objet
  d'une spec propre sur demande Adrian, avec `mode=BACKTEST` + `run_id` déjà prêts.

## 6. API JSON

### 6.1 `GET /api/analytics`

```json
{
  "generated": "2026-09-12T18:40:03Z", "version": "1.1.2",
  "filters": {
    "applied": {"mode": "PAPER", "strategy": ["S011"], "instance": [], "symbol": [], "side": [],
                "weekday": [], "exit_reason": [], "arm": [], "magic": [], "from": null, "to": null,
                "source": "auto", "curve_base": "auto", "weekday_key": "open", "dist_unit": "r"},
    "options": {"strategy": [{"id": "S011", "display_name": "…", "retired": false}], "instance": ["S011.XAU-USD"],
                "symbol": ["XAUUSD"], "side": ["LONG", "SHORT"], "weekday": ["mon", "tue", "wed", "thu", "fri"],
                "exit_reason": ["SL", "TP"], "arm": ["PRIMARY"], "magic": [130011]}
  },
  "source": {"ledger_rows": 0, "journal_rows": 9, "dedup": 0, "ledger_present": true,
             "studies": {"gold_forward": {"strategy_id": "S011", "closed": 9, "open": 0, "chain_ok": true}}},
  "header": {"mode": "PAPER", "n_strategies": 1, "n_instances": 1, "n_trades": 9,
             "base": {"CHF": 10000.0}, "base_kind": "capital", "source_kind": "journaux"},
  "by_currency": {
    "CHF": {
      "kpi": {"total_trades": 9, "long": 5, "short": 4, "wins": 4, "losses": 5, "zeros": 0, "win_rate": 0.44,
              "net_pnl": 179.06, "avg_per_trade": 19.9, "gross_profit": 0.0, "gross_loss": 0.0, "profit_factor": 1.34,
              "avg_win": 0.0, "avg_loss": 0.0, "expectancy": 19.9, "avg_r": 0.21, "sum_r": 1.91,
              "max_drawdown": 0.0, "max_dd_pct": 0.0, "recovery_factor": 0.0, "current_drawdown": 0.0,
              "recovered_pct": null, "dd_duration_days": 0, "recovery_days": null},
      "curve": {"base": 10000.0, "base_kind": "capital", "decimated": false,
                "points": [["2026-08-18T14:00:00Z", 9899.47, -100.53, -0.0101]]},
      "heatmap": {"years": [2026], "cells": {"2026-08": {"net": 0.0, "n_trades": 4, "sum_r": 0.0, "pct": 0.0}},
                  "year_totals": {"2026": {"net": 0.0, "n_trades": 9, "sum_r": 0.0, "pct": 0.0}},
                  "month_totals": {"08": {"net": 0.0, "n_trades": 4}}, "total": {"net": 179.06, "n_trades": 9, "sum_r": 1.91, "pct": 0.0179}},
      "by_month": [], "by_instance": [], "by_symbol": [], "by_strategy": [], "by_weekday": [], "by_hour": [],
      "distribution": {"unit": "r", "bins": [{"lo": -1.0, "hi": -0.5, "n": 5}], "n_without_r": 0},
      "summary": {"volume": {}, "pnl": {}, "risk": {}, "streaks": {}, "balance": {}}
    }
  },
  "open_positions": [],
  "warnings": []
}
```

(Valeurs à 0.0 ci-dessus = exemple de forme, pas de contenu.) Sous-ensemble vide ⇒
`by_currency: {}` et `header.n_trades = 0`, code 200.

### 6.2 `GET /api/analytics/trades` — §AN-28. 
### 6.3 `GET /api/analytics/kpi` — §AN-31.
### 6.4 `GET /analytics` — shell (AN-1). Toute méthode autre que GET ⇒ 405 (UI-7).

Fonctions Python exposées (toutes pures, testables sans Flask) : `analytics.filter_rows(rows,
filters)`, `analytics.options(rows, filters)`, `analytics.kpi(rows)`, `analytics.curve(rows,
base)`, `analytics.heatmap(rows, base)`, `analytics.by_key(rows, key)`, `analytics.distribution(rows,
unit)`, `analytics.summary(rows, base)`, `analytics.streaks(rows)`, `analytics.build_analytics(args)
-> dict`, `analytics.build_trades_page(args) -> dict`, `analytics.build_kpi() -> dict`,
`analytics.parse_filters(args) -> Filters | ValueError`.

## 7. Lots de livraison

Chaque lot : `VERSION` BUILD +1, `CHANGELOG.md` « Non publié », tests verts (`pytest app -q`),
zéro `http(s)://` dans `ui/`. Un lot n'est pas commencé tant que le précédent n'est pas
mergé sur `dev`.

### L1 — parité de la démo (P1 : F01, F03, F05, F06, F07, F10, F15, F17, F19*) — 9 fonctionnalités

*F19 (import) est livré sous sa forme tBot = adaptateur lecture seule D-AN-3, pas un import.

| Fichier | Action |
|---|---|
| `app/server/journal_adapter.py` | **créer** — §3.2 (catalogue, lecture CSV/params/manifest, chaîne, offset UTC, mapping, ouvertes) |
| `app/server/analytics.py` | **créer** — §3.1, AN-4…AN-7, AN-10, AN-11, AN-13, AN-14, AN-15…AN-19, AN-21, streaks AN-25 (colonne SÉRIES), `build_analytics` |
| `app/server/state.py` | **modifier** — `LEGACY_STUDIES` aligné sur `journal_adapter.STUDIES` (+ s20_forward) ; `study_state()` lit aussi le format `arms{}` de s13/s20 (n_closed_total, capital sommés + par arm) |
| `app/server/app.py` | **modifier** — `GET /analytics`, `GET /api/analytics` (400 sur filtre invalide, sinon jamais d'erreur) |
| `app/server/ui/analytics.html` | **créer** — shell (filtres, kpi, performance, heatmap, instances, summary-streaks, warnings) |
| `app/server/ui/index.html`, `strategy.html`, `services.html` | **modifier** — lien `analyse` ; lien « analyse détaillée » page stratégie (AN-2) |
| `app/server/ui/app.js` | **modifier** — `refreshAnalytics`, `filterBar`, `kpiTiles`, `lineChart`, `areaChart`, `barChart` (h/v signé), `heatmapTable`, `tooltip` DOM, `history.replaceState`, re-rendu sur changement |
| `app/server/ui/style.css` | **modifier** — `.kpi-tiles`, `.filters`, `.heat-1…4`, `.tooltip`, `.chart` |
| `app/tests/test_server_journal_adapter.py` | **créer** — AN-T1…T4 |
| `app/tests/test_server_analytics.py` | **créer** — AN-T5…T11, T15, T16 |
| `app/tests/test_server_services.py` | **modifier** — `test_html_pages_served` + `test_assets_served_without_cdn` couvrent `/analytics` |
| `spec/specification-app/INDEX.md`, `CHANGELOG.md`, `VERSION` | ligne 7 (déjà ajoutée), entrée, bump |

### L2 — lecture complète (P2 : F02, F04, F08, F11, F12, F13, F14, F18, F27) — 9 fonctionnalités

| Fichier | Action |
|---|---|
| `app/server/analytics.py` | **modifier** — AN-20, AN-22, AN-23, AN-24, AN-25 (VOLUME, P&L, RISQUE), AN-26, AN-27, `build_trades_page`, `build_kpi`, `open_positions` |
| `app/server/app.py` | **modifier** — `GET /api/analytics/trades`, `GET /api/analytics/kpi` |
| `app/server/ui/analytics.html`, `index.html` | **modifier** — sections par stratégie / weekday / heure / distribution / summary complet / positions ouvertes / journal ; bandeau KPI sur `/` (AN-31) |
| `app/server/ui/app.js`, `style.css` | **modifier** — `barChart` empilé, `summaryBlock`, `tradesJournal` (tri client, pagination, recherche), `kpiTiles` réduit sur index |
| `app/tests/test_server_analytics.py` | **modifier** — AN-T12…T14, T17, T18 |

### L3 — finitions (P3 retenues : F16, F20, F21) — 3 fonctionnalités ; 6 non reprises (F09, F22-F26, AN-33)

| Fichier | Action |
|---|---|
| `app/server/analytics.py` | **modifier** — colonne SOLDE & COÛTS (AN-25), groupe `magic divergent` (AN-22, F20), `magic_ok` par ligne |
| `app/server/ui/style.css` | **modifier** — `@media print` (AN-32) |
| `app/server/ui/app.js` | **modifier** — rendu SOLDE & COÛTS, badge `magic ≠ manifest` |
| `app/tests/test_server_analytics.py` | **modifier** — AN-T19, T20 |

### Hors lots, pré-requis parallèle (autre spec, autre ticket)

SPEC_ledger v1.1 : migration v3 `source_ref TEXT` + `UNIQUE(run_id, source_ref)` ;
script de projection **écrite** journaux → ledger (`open_trade`/`record_trade` +
`record_equity_snapshot` par CLOSE + `strategy_state.allocated_capital`). Le jour où elle
tourne, `source=auto` bascule seul (D-AN-4) sans changement d'UI.

## 8. Tests attendus (cc-app)

Fixtures : étendre `conftest.ui_env` d'un helper `write_journal(study, rows, *, chain=True,
params=…, state=…)` produisant un `journal.csv` + `params.json` + `state.json` jetables ;
étendre `_seed_ledger` en `seed_ledger(path, trades=[…])` acceptant plusieurs instances,
modes, devises, mois et trades à 0. Jeu de référence **J5** (une devise, base 1 000) :
nets `+100, −50, 0, +30, −20` clos les 3, 4, 5, 8, 9 du mois (lun, mar, mer, lun, mar),
`pnl_r` `+2, −1, 0, +0.6, −0.4` ⇒ N = 5, W = 2, L = 2, Z = 1, `win_rate` 0.40, net 60,
`avg_per_trade` 12, `gross_profit` 130, `gross_loss` −70, `profit_factor` 1.857,
`avg_win` 65, `avg_loss` −35, `expectancy` 12 (Trade Buddy donnerait 5 — test négatif),
solde 1 100 / 1 050 / 1 050 / 1 080 / 1 060, pic 1 100, `max_drawdown` 50 au 2ᵉ trade,
`max_dd_pct` 0.0455, `recovery_factor` 1.2, `current_drawdown` 40, `recovered_pct` 0.20,
`max_win_streak` 1, `max_loss_streak` 1, `current_streak` `{loss, 1}`, `sum_r` 1.2, `avg_r` 0.24.

- **AN-T1** — Adaptateur : journal gold synthétique (2 OPEN/CLOSE + 1 OPEN seul) ⇒ 2 lignes
  clos au format §3.1 (`instance_id = S011.XAU-USD`, `mode = PAPER`, `currency = CHF`,
  `account_balance` = `capital_after` de l'OPEN, `meta_json.pnl_r` conservé, `edge_cost_ccy`
  = valeur calculée depuis `spec`) + 1 position ouverte.
- **AN-T2** — Adaptateur : `bar_time` `2026-07-01 16:00` (été) ⇒ `open_time` `13:00Z` ;
  `2026-12-01 16:00` ⇒ `14:00Z` ; `bar_time_utc > measured_at_utc` ⇒ warning, ligne conservée.
- **AN-T3** — Adaptateur : chaîne SHA rompue ⇒ lignes servies + `chain_ok = false` +
  warning ; journal absent ⇒ étude absente du rapport + warning ; `params.json` absent ⇒
  étude ignorée ; **aucun fichier créé** dans `db_dir()` ni `project_root()` après l'appel.
- **AN-T4** — Adaptateur : journal s13 (colonnes `arm`, `symbol`, arm OBSERVATION) et
  alexg (événements SHADOW_*/DECISION ignorés, `reason` → `signal_reason`) ⇒ instances
  `S013.EUR-JPY` / `S093.…`, `arm` porté en meta.
- **AN-T5** — `kpi(J5)` = valeurs de référence ; N = 0 ⇒ toutes valeurs 0/`null`, jamais
  de division par zéro ; L = 0 ⇒ `profit_factor = null`.
- **AN-T6** — `curve(J5, base=1000)` = série de référence ; `heatmap` : TOTAL×TOTAL = 60,
  `pct` = 0.06, colonne-mois = Σ années sur un jeu à 2 années ; base 0 ⇒ `pct = null`.
- **AN-T7** — Filtres : AND entre paramètres, OR intra ; `from`/`to` inclusifs en date
  locale (trade à 23:30 UTC compte le bon jour local, `local_tz` seam) ; `weekday_key`
  `open` vs `close` change le bucket d'un trade ouvert lundi clos mardi ; valeur hors
  domaine ⇒ 400 JSON.
- **AN-T8** — Options dépendantes : deux stratégies à symboles disjoints ⇒ `options.symbol`
  ne liste que ceux de la stratégie choisie, `options.strategy` liste toujours les deux.
- **AN-T9** — Modes et devises : trades PAPER + BACKTEST + CHF + EUR ⇒ `mode=PAPER`
  n'inclut aucun BACKTEST ; `by_currency` a deux clés sans addition croisée.
- **AN-T10** — Source : ledger + journal portant le même `(run_id, source_ref)` ⇒ une seule
  ligne (ledger), `source.dedup = 1` ; ledger absent ⇒ journaux seuls + warning ; **la DB
  n'est pas créée** ; `source=ledger` ignore les journaux.
- **AN-T11** — Routes : `/analytics` 200 HTML sans `http(s)://` ; `/api/analytics` 200 sur
  un layout vide (`by_currency = {}`) ; `POST /api/analytics` ⇒ 405 ; lien `analyse`
  présent dans les 4 shells ; `/api/strategy/S020` ne 404 plus (LEGACY_STUDIES).
- **AN-T12** — `by_key` instance / stratégie / weekday / heure sur un jeu à 2 stratégies ×
  2 instances : sommes = net global ; tri décroissant ; `magic divergent` groupé à part.
- **AN-T13** — `distribution` R : bins fixes, bornes ouvertes (`< −3`, `≥ 5`), `n_without_r`
  compte les trades sans R ; devise : 16 bins, min = max ⇒ 1 bin.
- **AN-T14** — `summary(J5)` : `long_win_rate`, `best/worst`, `best_r/worst_r`,
  `pct_trades_ge_1r` = 0.20 (1 trade ≥ +1 R sur N_r = 5), `avg_holding_h` ; Sharpe/Sortino `null` sous 20 trades ; sur 40 trades synthétiques de
  R connu : `sharpe_r` = valeur calculée à la main, `sharpe_r_annual = sharpe_r × sqrt(N_r/years)`.
- **AN-T15** — Streaks : `+,+,0,−,−,−,+` ⇒ `max_win 2`, `max_loss 3`, `current {win,1}` ;
  Z casse la série.
- **AN-T16** — Drawdown : `recovered_pct` `null` quand le pic est retrouvé ; `dd_duration_days`
  et `recovery_days` sur un jeu pic→creux→nouveau pic ; KPI = min de la colonne `drawdown`
  de `curve.points` (même série).
- **AN-T17** — `/api/analytics/trades` : `total`, pagination (`page=2&limit=2` sur 5 trades
  ⇒ 2 lignes), `limit=5000` ⇒ 400, tri `close_time desc`, `pnl_r`/`holding_h`/`magic_ok` présents.
- **AN-T18** — `open_positions` : ledger `close_time NULL` + journal OPEN seul ⇒ 2 entrées,
  aucune n'apparaît dans `kpi.total_trades` ; `/api/analytics/kpi` sépare PAPER et LIVE.
- **AN-T19** — SOLDE & COÛTS : `final_balance = base + net`, `total_edge_cost = Σ meta`,
  `null` si base inconnue.
- **AN-T20** — F20 : trade `magic_number = 999` sur S011 (manifest 130011) ⇒ `magic_ok = false`,
  groupe `magic divergent` dans `by_strategy`.

## 9. Défauts retenus — Adrian peut changer

Chaque ligne est une décision **déjà prise** (zéro TBD) ; la changer avant L1 ne coûte
qu'une ligne ici. Les cinq premières sont les plus discutables.

| # | Défaut retenu | Alternative écartée | Réf. |
|---|---|---|---|
| DF-1 | `expectancy = net / N` ; `win_rate = W / N` ; Z ni W ni L | Formule Trade Buddy (Z côté perte) ; win rate sur W + L | D-AN-7 |
| DF-2 | Courbe filtrée : base « capital » si connue pour toutes les instances, sinon cumul depuis 0 ; `dd_pct` relatif au **pic** | Starting balance virtuelle fixe (Trade Buddy) ; `%` / capital initial | D-AN-8, D-AN-9 |
| DF-3 | Sharpe / Sortino sur le **R par trade**, annualisé × √(trades/an), `null` < 20 trades | Rendements journaliers du solde × √252 (exige une base connue) ; formule Trade Buddy × √N | D-AN-10 |
| DF-4 | Arms `OBSERVATION` / `SHADOW` **inclus** par défaut (filtre `arm` et badge) | Exclus par défaut (PRIMARY seul) — s13 n'aurait aucun trade visible | AN-4 |
| DF-5 | Jour de semaine / heure sur `open_time` (`weekday_key=open`) | `close_time` (choix Trade Buddy présumé) | D-AN-11 |
| DF-6 | Mode par défaut `PAPER`, choix unique, jamais fusionné | PAPER + LIVE côte à côte ; « tous modes » | D-AN-5 |
| DF-7 | `source=auto` = union ledger ∪ journaux dédoublonnée | Ledger si non vide sinon journaux (bascule) | D-AN-4 |
| DF-8 | Offset broker = règle DST UE fixe (+3 / +2) | `calibrate_server_offset()` sur `bars_cache` à chaque requête (I/O lourd, non déterministe en test) | §3.2 |
| DF-9 | Devise des journaux = `CHF` constante adaptateur | Champ `currency` ajouté à `params.json` (touche un scellé) | D-AN-6 |
| DF-10 | Heatmap : `%` / base fixe non composé + totaux colonne-mois calculés | `%` / solde de début de mois ; cellules mois vides (Trade Buddy) | AN-19 |
| DF-11 | Distribution en R, bins fixes 0,5 R sur [−3, +5] | 16 bins équirépartis en devise (Trade Buddy) | D-AN-12 |
| DF-12 | Sharpe hors tuiles (SUMMARY) ; 9ᵉ tuile R MOYEN | 8 tuiles Trade Buddy strictes | AN-13 |
| DF-13 | Balance / drawdown en bascule (cases), pas superposés | Deux axes superposés | AN-15 |
| DF-14 | Journal paginé serveur 200 (max 1 000), tri serveur fixe, tri client par page | Tri serveur par colonne | D-AN-15 |
| DF-15 | Pas d'en-tête sticky sur `/analytics` (Trade Buddy l'a) | Sticky | AN-8 |
| DF-16 | Zéro net casse les streaks | Zéro neutre (série continue) | AN-25 |
| DF-17 | `recovered_pct` seulement tant que le creux du DD max n'est pas effacé | Toujours calculé sur le DD courant | AN-14 |
| DF-18 | Positions ouvertes sans P&L flottant | Cotation via `bars_cache` (I/O, périmé) | D-AN-17 |
| DF-19 | Bandeau KPI de `/` via une route dédiée `/api/analytics/kpi` | Enrichir `/api/state` | AN-31 |
| DF-20 | F24 Backtest comparison différée à une spec propre | L'inclure en L3 sur `mode=BACKTEST` | AN-33 |

## 10. Hors scope

Import de fichiers, écriture du ledger (projection écrite, SPEC_ledger v1.1), flux de
capital réels (TCK-006), MAE/MFE (calculables par rejeu `bars_cache/`, non requis pour la
parité), Correlation / Backtest comparison / Monte Carlo (jamais montrés), notes manuelles
sur un trade (UI-7 : viendraient de `meta_json` côté stratégie), thème clair, langue DE.
