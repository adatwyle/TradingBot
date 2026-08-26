# spec-strategie — S017 ireland_gex

**Version** : 1.0.0 — 2026-08-26 (session de fondation cc-S017)
**Statut** : RESEARCH (manifest.yaml = source de vérité)
**Source** : Nick Ireland, « Why I stopped trading price action & only use gamma exposure » (YouTube, 22.06.2026) — transcript + 22 frames dans `sources/video/`.
**Instrument** : SPY (validation du signal sur le sous-jacent d'abord ; couche options éventuelle = phase ultérieure, cf. §8).

---

## 1. Principe

Les market makers (dealers) vendent la majorité des options SPY et delta-hedgent mécaniquement leurs books. Le **gamma exposure (GEX)** par strike mesure l'intensité de ce hedging forcé autour de chaque niveau de prix :

- Les strikes à forte concentration de gamma deviennent des **niveaux de réaction** (rebond, aimant/pinning, ou accélération en cas de cassure à fort volume — flip résistance→support).
- Le **signe du gamma net** des dealers définit le régime du jour : gamma positif → hedging contre le marché → volatilité comprimée, tendances propres ; gamma négatif → hedging avec le marché → mouvements amplifiés, retournements violents.

La stratégie ne trade **que** lorsque le prix est au contact d'un niveau GEX majeur identifié en pré-market, dans le sens de la tendance EMA alignée daily/5min, sur cassure de compression confirmée par le volume. Tout le reste (« no man's land ») est interdit, quelle que soit la qualité du pattern.

Edge revendiqué : contrairement aux niveaux de price action (arbitraires), les niveaux GEX découlent d'une **obligation mécanique** des dealers, connue avant l'ouverture. C'est l'hypothèse centrale à falsifier (H1).

## 2. Données d'entrée

| Donnée | Source V1 (gratuite) | Fréquence | Notes |
|---|---|---|---|
| Chaîne d'options SPY (OI, IV, strikes, expirations) | CBOE delayed `cdn.cboe.com/api/global/delayed_quotes/options/SPY.json` | 1×/jour pré-market (+ snapshots intraday optionnels) | Différé ~15 min — suffisant : la carte se construit en pré-market |
| Carte GEX par strike | **Calcul maison** (méthodologie Perfiliev, cf. §3.1) | Dérivée de la chaîne | Réf. lecture : repo `Matteo-Ferrara/gex-tracker` |
| OHLCV SPY 5 min + daily | yfinance (fallback : Stooq daily) | 5 min : ~60 jours d'historique max ; daily : illimité | Limite structurelle yfinance intraday |
| GEX historique (backtest) | À acquérir — cf. §9 (ticket) | — | Non disponible gratuitement en profondeur |

Toutes les données vivantes sous `C:\db\tradingBot\S017\` (RULE db-separation).

## 3. Définitions opérationnelles (testables)

Chaque terme flou de la vidéo reçoit ici UNE définition mesurable, avec paramètre nommé (plages dans `manifest.yaml`).

### 3.1 GEX par strike (calcul)

Pour chaque option de la chaîne (méthodologie Perfiliev « naïve », hypothèse standard : dealers long les calls vendus par le public, short les puts) :

```
GEX_call(K) = +gamma × OI × 100 × S² × 0.01     (par contrat call au strike K)
GEX_put(K)  = −gamma × OI × 100 × S² × 0.01     (par contrat put au strike K)
GEX(K)      = Σ expirations [ GEX_call(K) + GEX_put(K) ]     (en $ par mouvement de 1 % du spot)
```

- `S` = spot SPY ; `gamma` = gamma Black-Scholes fourni par CBOE (sinon recalculé depuis IV).
- **Périmètre expirations** : `gex_expiry_window` jours (défaut : toutes ; variante 0DTE/weekly only — la vidéo colore par expiration proche, frames 02/16/19).
- `GEX_net = Σ_K GEX(K)` ; profil cumulé `C(K) = Σ_{k≤K} GEX(k)` → **gamma flip** = strike où C change de signe.

### 3.2 « Niveau GEX majeur » (condition 1)

Un strike K est un **niveau majeur** du jour si, sur la carte pré-market :

```
|GEX(K)| ≥ level_major_frac × max_K' |GEX(K')|          (défaut 0.50)
ET rang de |GEX(K)| ≤ level_top_k                        (défaut 5)
ET |K − spot_open| ≤ level_universe_pct × spot           (défaut 2 %)
```

**« Prix à/proche du niveau »** : `|price − K| ≤ near_level_pct × price` (défaut 0.10 % ≈ 0.75 $ sur SPY 750). En dehors → no man's land → **aucun trade** (règle d'exclusion primaire).

Référence vidéo : niveaux 750 (60 M$ cumulés) / 755 (180 M$) / 745 (>100 M$) — le seuil absolu en $ n'est PAS utilisé comme définition (dépend du régime de marché) ; c'est le seuil relatif qui est testé.

### 3.3 « Environnement gamma positif / négatif » (condition 2)

Régime du jour figé en pré-market :

- **Défaut (`regime_mode: net`)** : gamma positif si `GEX_net > 0`, négatif sinon.
- Variantes à tester : `flip` (spot au-dessus du gamma flip = positif) ; `local` (signe du GEX au niveau majeur le plus proche, comme la vidéo qui qualifie chaque niveau individuellement : « 750 négatif, 755 positif »).

Conséquences (gestion, pas signal) :
| Régime | Taille | Sortie |
|---|---|---|
| Positif | 100 % | Target complet 2R (niveau GEX suivant si plus proche) |
| Négatif | × `neg_gamma_size_factor` (défaut 0.5, plage 0.5-0.7) | Partiel `neg_gamma_partial_frac` (défaut 50 %) à 1R, solde à 2R |

### 3.4 « Séquence EMA avec bon espacement » (condition 3)

EMA 9/21/50 sur close. Séquence haussière : `EMA9 > EMA21 > EMA50` ; baissière : inverse.

**« Bon espacement »** (anti-chop), normalisé par l'ATR(14) du même timeframe :

```
spread_ok = min(EMA9−EMA21, EMA21−EMA50) / ATR14 ≥ ema_spread_min
```
Défauts : `ema_spread_min_5m = 0.15`, `ema_spread_min_daily = 0.30`. EMAs entassées (spread < seuil) → pas de trade.

**« Alignement daily / 5min »** : la séquence (sens) ET le spread_ok doivent être vrais sur les DEUX timeframes, la barre daily utilisée étant la **dernière clôturée** (J−1 — jamais la barre du jour en cours, R1 causalité). Haussier aligné → longs uniquement ; baissier aligné → shorts uniquement ; divergence → pas de trade.

### 3.5 « Compression / flag » et « cassure à volume nettement supérieur » (condition 4)

**Compression** sur 5 min : fenêtre des `compress_bars` dernières barres closes (défaut 6, plage 4-12) telle que :

```
(max(high) − min(low)) sur la fenêtre ≤ compress_range_atr × ATR14   (défaut 1.5)
ET la fenêtre chevauche un niveau majeur : distance(min(low)..max(high), K) ≤ near_level_pct
```

**Cassure** (long) : première barre close dont `close > max(high fenêtre)`.

**« Volume nettement supérieur »** :

```
volume(barre de cassure) ≥ vol_mult × SMA20(volume)     (défaut 1.5, plage 1.2-2.5)
```

Pas de spike de volume → skip systématique (la vidéo montre le fake-out évité, frame 15). Fenêtre d'entrée : uniquement pendant la session régulière US (15:30-22:00 CH), premières `entry_cutoff_min` minutes optionnellement exclues/limitées (plage à tester).

**Variante déclarée 2026-08-26 (avant mesure) — plafond de volume (`vol_cap`)** : l'étude 01 bootstrap (134 cassures, n par tranche faible) suggère que les spikes extrêmes (> 2× SMA20) suivent MOINS bien que la tranche 1.5-2× — interprétation candidate : volume extrême = épuisement/news, pas confirmation. Hypothèse dérivée **H3b** (§4) : la fenêtre de volume est bornée des deux côtés :

```
vol_mult × SMA20 ≤ volume(cassure) < vol_cap × SMA20    (vol_cap : none | 2.0 | 2.5 | 3.0)
```

Défaut V1 : `vol_cap = none` (fidèle à la vidéo) ; la variante est mesurée en Phase A (étude 03) et ne devient un défaut que si l'effet persiste avec n suffisant.

### 3.6 Risque et sorties (condition 5)

Conformément à R2, la stratégie n'émet que `entry / stop / target` — la taille appartient à `core/risk/` :

- **Stop structurel** : long → `min(low fenêtre compression, EMA50_5m) − stop_buffer_atr × ATR14` (défaut buffer 0.25). Short symétrique. Jamais déplacé (R3, set & forget).
- **Target** : niveau GEX majeur suivant dans le sens du trade ; s'il n'y en a pas à ≥ 2R, target = 2R.
- **Filtre RR** : trade rejeté si `(target − entry)/(entry − stop) < rr_min` (défaut 2.0).
- Modulation gamma négatif : cf. §3.3 (métadonnée de signal à destination de la couche risque).

### 3.7 Checklist d'entrée (les 5 vertes = setup A+)

1. Prix au contact d'un niveau GEX majeur (§3.2) — sinon RIEN
2. Régime gamma identifié (§3.3) — module la gestion
3. Séquences EMA alignées daily+5min avec spread (§3.4) — donne le sens
4. Compression au niveau + cassure à volume (§3.5) — déclenche
5. RR ≥ 2 avec stop structurel (§3.6) — sinon on passe

## 4. Hypothèses falsifiables (déclarées avant toute mesure)

| # | Hypothèse | Test | Critère de falsification |
|---|---|---|---|
| **H1** | Les niveaux GEX majeurs produisent des réactions de prix mesurables : au premier contact intraday, la probabilité de rejet/rebond et l'excursion opposée dans les 30-60 min sont supérieures à celles de **niveaux placebo** (strikes ronds non-majeurs, niveaux décalés de ±half-strike) | Event study contacts réels vs placebo, même jour même méthode | Pas de différence (effet ≤ placebo + bruit) sur ≥ 100 contacts |
| **H2** | Le régime gamma net pré-market prédit la volatilité réalisée du jour : RV(gamma−) > RV(gamma+) | Comparaison RV intraday 5min par régime | Différence nulle ou inversée sur ≥ 60 jours |
| **H3** | Les cassures de compression AVEC volume ≥ 1.5× ont un taux de suivi (atteinte de +1R avant le stop) supérieur aux cassures SANS volume | Comparaison appariée des deux populations de cassures | Taux de suivi équivalent (le filtre volume n'apporte rien) |
| **H3b** (déclarée 2026-08-26, dérivée de l'étude 01 — §3.5) | La fenêtre bornée `[vol_mult, vol_cap)` suit mieux que `≥ vol_mult` sans plafond : les spikes extrêmes (≥ 2×) sont de l'épuisement, pas de la confirmation | Balayage `vol_cap` ∈ {none, 2.0, 2.5, 3.0} sur les mêmes populations de cassures (étude 03) | La tranche haute (≥ 2×) suit aussi bien ou mieux que 1.5-2× sur n ≥ 30 par tranche |
| **H4** | Le système complet (5 conditions) a une expectancy nette positive après coûts sur SPY spot | Backtest via backtester commun (R9) sur historique GEX suffisant | Expectancy ≤ 0 après coûts, ou nombre de trades < 30 (non conclusif, pas validé) |
| **H5** | Pinning : les jours gamma positif, la clôture est attirée par le plus gros niveau positif (distance close→niveau inférieure à celle d'un modèle nul de marche aléatoire) | Distance normalisée close vs niveau, jours + vs − | Pas d'effet d'attraction mesurable |

**Anti-data-mining** : les défauts §3 sont figés AVANT mesure ; toute exploration de plage est reportée avec le nombre de variantes testées (correction pour comparaisons multiples dans l'interprétation, cf. `docs/METHODOLOGY.md` du socle — un pass sur 19 trades n'est pas une preuve).

## 5. Protocole de mesure

**Phase A — Études de signal (`research/`, sans moteur de backtest — R9)** :
1. Collecte quotidienne automatisable : snapshot chaîne CBOE + carte GEX calculée + OHLCV (pipeline `research/daily_snapshot.py` → `C:\db\tradingBot\S017\`).
2. H1/H5 sur données accumulées + tout historique GEX gratuit accessible ; H2/H3 mesurables dès ~60 jours d'OHLCV 5min (H3 ne dépend pas du GEX).
3. Chaque étude : script reproductible + résultats datés dans `research/`.

**Phase B — Backtest (R9)** : nécessite (a) historique GEX profond (§9), (b) backtester commun supportant SPY 5min + série exogène par jour — évaluation faite en session de fondation, ticket d'extension si besoin. Anchored walk-forward, coûts inclus, invariant de causalité R1 archivé.

**Phase C — PAPER** : uniquement sur décision Adrian (R4/R10), après checklist d'admission complète.

## 6. Ce que la stratégie ne fait PAS

- Pas de trade hors niveau GEX majeur, hors alignement EMA, sans volume de cassure, ou avec RR < 2 (4 vetos indépendants).
- Pas de calcul de taille ni lecture de solde (R2). Pas de stop déplacé (R3). Pas de moteur de backtest privé (R9).
- Pas d'overnight : positions fermées en fin de session US au plus tard (day trading — `eod_close: true`).

## 7. Limites connues / risques de l'edge

- **Méthodologie GEX naïve** : l'hypothèse « dealers long calls / short puts » est une approximation ; le positionnement réel est inobservable. ITMatrix/vidéo utilisent des variantes propriétaires (leur carte sépare par expiration et cumule le volume) — notre carte maison peut diverger de celle que Nick Ireland lit.
- **Différé 15 min CBOE** : sans impact pour la carte pré-market ; limite les recalculs intraday.
- **Survivorship du contenu YouTube** : 2 trades démontrés gagnants + 1 fake-out évité ≠ preuve. D'où H1-H5.
- **yfinance 5min ≈ 60 jours** : profondeur intraday gratuite faible — l'accumulation quotidienne du pipeline devient l'actif de recherche.

## 8. Sous-jacent vs options

La vidéo trade des calls/puts courts (levier + convexité). La **logique du signal est entièrement sur le sous-jacent** ; V1 valide le signal sur SPY spot (mesurable proprement, comparable via le backtester commun). Si H4 validée, une couche d'exécution options (choix strike/DTE, coûts IV) sera spécifiée séparément — décision Adrian.

## 9. Question ouverte matérielle

**Historique GEX profond pour backtest** : non disponible gratuitement (CBOE delayed = présent uniquement ; FlashAlpha free = limité ; ITMatrix API 119.99 $/mois = live + historique complet). Traité par ticket avec préconisation chiffrée (cf. `tickets/`). En attendant : Phase A sur données accumulées + H2/H3 qui n'exigent pas d'historique GEX.
