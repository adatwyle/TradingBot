# VERDICT — s13_macd_fx « MACD Forex Design Search »

Mandat Adrian : « teste le Daily MACD mean reversion sur des paires forex » +
« développe une stratégie MACD gagnante sur des paires forex — débrouille-toi
pour la rendre gagnante ». Lecture exécutée : exploration large et honnête de
l'espace de conception, protections à la hauteur de la largeur — pas de
fabrication de vert (cf. ANALYSIS §0).

Protocole gelé et commité AVANT tout backtest : `research/FALSIFICATION.md`
(commit `6405c80`). Liste close des candidates commitée AVANT l'ouverture du
hold-out (commit `5fbedec`). R1 PASSÉ (couche indicateur incluse) et R5 PASSÉ
— 36/36 sur 3 paires × 6 jeux de paramètres couvrant les 3 familles × 2 sens
(`backtests/causality.txt`, `backtests/conformance.txt`).

Données : MT5 Swissquote D1, 2006-08 → 2026-08-15 (≈ 6 200 barres/paire),
9 paires (GBPUSD absent du catalogue broker — exclu, signalé). Coûts réels =
spread catalogue + slippage 0,5 pip par bout. Moteur commun R9,
`engine_kwargs` identiques stratégie/témoin. **Hold-out scellé : 18 derniers
mois (≥ 2025-02-16, 466 barres/paire), jamais chargé pendant l'exploration,
ouvert UNE fois sur 3 candidates.**

---

## 1. L'exploration, en une table

756 cellules (9 paires × {A mean-reversion s12 transposé 48 ; B croisement
8+4 ; C extrême-MACD 24}), WF ancré 4 fenêtres sur l'exploration seule
(2006 → 2025-02-15), témoin apparié 200 tirages sur les 151 cellules les
mieux classées éligibles (F5 : ≥ 60 trades OOS, ≥ 100 plein échantillon).

R/trade OOS net, TOUTES cellules confondues (méd / moy) :

| Famille | LONG | SHORT | Lecture |
|---|---|---|---|
| A `mr` (s12 transposé) | −0,011 / −0,010 (210 c.) | −0,007 / −0,025 (216 c.) | **la transposition directe de s12 ne marche pas non plus en FX** |
| B `cross` (référence) | −0,034 / −0,039 (36 c.) | −0,063 / −0,040 (36 c.) | morte, comme prévu par 3 sources + nos verdicts trend |
| B `hold` (momentum 20 j) | −0,064 / −0,048 (18 c.) | −0,001 / −0,005 (18 c.) | idem |
| C `ext` (percentile MACD/ATR) | **+0,041 / +0,062 (108 c.)** | −0,026 / −0,008 (108 c.) | la SEULE poche large positive — côté LONG uniquement |

27 cellules ≥ p95 témoin (sur 151 armées — elles-mêmes présélectionnées
top-3 par famille×sens, donc chiffre optimiste par construction). Fait
notable AVANT toute sélection fine : **la même cellule `ext long lookback 252
q 0,10` est ≥ p95 sur EURJPY (100), AUDCAD (100), EURCHF (97-98,5) et sa
voisine lb126 sur EURUSD (97,5)** — une cohérence trans-paires qu'aucun de
nos dossiers précédents (s90 inclus) n'avait montrée.

## 2. Instruction des candidates (règle écrite d'avance, 6 cellules)

Classement figé : percentile témoin DESC puis R/t OOS DESC. F2 = coût nul,
F3 = voisinage (±1 cran), F4 = 5 graines, F8 = transfert à froid 8 autres
paires (détail : `backtests/candidates.txt`).

| Cellule | F2 coût 0 | F3 voisins | F4 graines | F8 poolé (n) | Sort |
|---|---|---|---|---|---|
| EURJPY ext-L lb252 q0,1 atr1,5 | +0,099 R/t | 4/4, méd +0,126 | 5/5 ≥ 95 | **+0,021 (1 187)** | survivante |
| AUDCAD ext-L lb252 q0,1 atr1,5 | +0,139 R/t | 4/4, méd +0,083 | 5/5 ≥ 95 | **+0,020 (1 226)** | survivante |
| EURCHF mr-S n3 rf sym3 | +0,057 R/t | 5/5, méd +0,061 | 5/5 ≥ 95 | −0,027 (2 018) | survivante |
| EURCHF ext-L lb252 sym3 | +0,041 | **2/4, méd −0,016** | 5/5 | −0,003 | **F3 — éliminée** |
| EURJPY ext-S lb126 atr1,5 | +0,067 | 4/4 | 5/5 | **−0,073 — suspicion** | non retenue (rang 5) |
| EURJPY ext-L lb126 atr1,5 | +0,091 | 4/4 | 5/5 | −0,017 | non retenue (rang 6) |

Liste close du hold-out (commit `5fbedec`) : EURJPY ext-L, AUDCAD ext-L,
EURCHF mr-S.

## 3. F7 — le hold-out scellé (ouvert une fois, 2025-02-16 → 2026-08-15)

| Candidate | net | témoin hold-out | beta long aléatoire | Verdict F7 |
|---|---|---|---|---|
| EURJPY ext-L | **+0,491 R/t** × 10 tr (WR 80 %) | percentile **74,0** | +0,321 R/t | **DÉCLENCHÉE** — positif mais indistinguable d'un long au hasard sur la période |
| **AUDCAD ext-L** | **+0,580 R/t** × 11 tr (WR 81,8 %) | percentile **96,0** | +0,105 R/t | **PASSE** (net > 0 ET ≥ 90) |
| EURCHF mr-S | −0,041 R/t × 11 tr | percentile 24,0 | — | **DÉCLENCHÉE** |

## 4. Variante session (UNE, déclarée — informative)

Le motif candidat porté en H4 (lookback 1512 ≈ 252 j) est NÉGATIF net plein
échantillon sur les deux paires (−0,021 à −0,090 R/t), fenêtre Londres/NY ou
pas (`backtests/session_variant.txt`). Confirmation directe de s91 : le
péage intra-journalier mange tout. **Le motif n'existe qu'en D1.**

## 5. VERDICT

# EDGE CANDIDAT (faible) — une survivante : AUDCAD `ext` long, D1

Config : MACD/ATR sous son 10e percentile glissant 252 j → LONG au close,
cible +1,5 ATR, stop −1,5 ATR, D1, coûts réels. Chiffres d'exploration :
+0,093 R/t net × 130 trades (≈ 7/an), OOS 4/4 fenêtres positives,
percentile témoin 100 (5/5 graines), voisinage 4/4, transfert à froid POOLÉ
POSITIF sur les 8 autres paires (+0,020 R/t × 1 226 — du jamais vu dans nos
dossiers), hold-out scellé +0,58 R/t × 11, percentile 96.

**Pourquoi « faible » — dit avant tout enthousiasme :**
1. **11 trades de hold-out.** Le percentile 96 est réel mais l'IC d'un
   effectif pareil est énorme. C'est un signal, pas une preuve.
2. La jumelle EURJPY (même config, même percentile 100 en exploration) fait
   +0,49 R/t au hold-out mais percentile 74 : sur sa période, un long au
   hasard faisait +0,32 R/t. Une des deux jumelles n'a PAS battu son beta.
3. Le côté SHORT de la même famille est négatif : le motif n'est pas
   symétrique, ce qui affaiblit le récit « retour à la moyenne » pur.
4. ~7 trades/an par paire : tout déploiement réel est lent à se juger.

**Ce qui est solide, dit aussi :** la famille a une largeur inhabituelle
(poche positive sur 108 cellules AVANT sélection, cohérence trans-paires en
exploration ET transfert à froid net positif), toutes les falsifications
gelées ont été appliquées, et la survivante a passé le seul test qu'elle ne
pouvait pas sur-ajuster : 18 mois de données jamais vues.

### La réponse à Adrian

Une stratégie MACD forex « rendue gagnante » en ajustant jusqu'au vert
n'existe pas — 756 cellules le confirment (A et B sont mortes, le côté short
de C aussi). Ce qui existe : **un candidat étroit et honnête**, AUDCAD D1
extrême-MACD long, avec les chiffres ci-dessus. La suite proposée, calquée
sur le motif gold_forward : **forward scellé, zéro argent** — observer la
config figée (magic 130013, AUDCAD + EURJPY en observation d'hypothèse) sur
les 6-12 prochains mois, verdict aux règles écrites d'avance. PAS de
promotion PAPER/LIVE — décision d'Adrian (R10). À ~7 trades/an, il faudra
accepter que le forward soit lent, ou l'étendre au panier des 9 paires
(l'espérance poolée +0,020 R/t net est positive mais 4× plus mince).

### Comparaison explicite à s12 (la demande initiale)

La transposition FX du motif s12 (famille A) répond NON, comme s12 sur
indices : R/t OOS médian négatif dans les deux sens, aucune cellule A
survivante au hold-out. Ce que le FX change : (a) le témoin n'a plus le beta
séculier long à absorber, le jugement est plus propre ; (b) le short devient
testable — il ne sauve rien ; (c) la seule vie détectée vient d'un
DÉCLENCHEUR différent (extrême de distribution, pas séquence de baisses).
Le verdict s12 « le terrain D1 est bon, le signal était mauvais » est
confirmé : même terrain, autre signal, résultat partiellement différent.

## 6. Limites

1. **Effectif hold-out (11 trades)** — la limite dominante, non négociable.
2. Les 4 fenêtres OOS sont emboîtées (METHODOLOGY §9) ; le hold-out est la
   seule tranche vraiment indépendante.
3. La sélection de la survivante parmi 756 cellules reste de la sélection :
   percentile 96 sur hold-out APRÈS une sélection aussi large vaut moins que
   96 « naïf ». C'est précisément pourquoi la proposition est un forward
   scellé et pas un déploiement.
4. EURCHF traverse un régime administré (2011-2015) dans l'exploration ; les
   cellules EURCHF (toutes éliminées de toute façon) se lisaient avec ça.
5. Cible « reprise » sym statique (dégradation héritée s12, déclarée) — ne
   concerne pas la survivante (sortie ATR).
6. Spread catalogue constant sur 20 ans : les coûts 2006-2012 réels étaient
   plus larges ; le sens de l'erreur est optimiste pour les vieilles
   fenêtres, le hold-out (conditions actuelles) n'est pas concerné.

## 7. Fichiers produits

| Fichier | Contenu |
|---|---|
| `research/ANALYSIS.md` | Cadrage, état de l'art interne, familles, différences vs s90 |
| `research/FALSIFICATION.md` | Gel pré-backtest : hold-out scellé, grilles, F1-F8, règle de sélection |
| `strategy.py` | 3 familles × 2 sens, magic 130013, precompute → DataFrame (R1) |
| `backtests/run_validation.py` + `causality.txt`, `conformance.txt` | R1/R5 PASS 36/36 |
| `backtests/run_explore.py` + `explore_<PAIR>.txt` × 9 + `explore_summary.csv` | 756 cellules, WF + témoins |
| `backtests/run_candidates.py` + `candidates.txt` | F2/F3/F4/F8 sur 6 cellules |
| `backtests/run_holdout.py` + `holdout.txt` | F7 — ouverture unique du scellé |
| `backtests/run_session_variant.py` + `session_variant.txt` | Variante H4/session (négative) |
| `research/VERDICT.md` | Ce document |
