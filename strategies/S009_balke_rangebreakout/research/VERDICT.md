# Verdict — s09_balke_rangebreakout « Session Range Breakout » (René Balke)

Source : René Balke (BM Trading), réglages exacts publiés, pertes publiées.
Données : MT5 Swissquote H1, 2021-07-18 → 2026-08-16, 30 024-31 594 barres.
Grille : 24 cellules USDJPY + 6 XAUUSD + 2 GBPUSD + 1 EURJPY — **figée dans
FALSIFICATION.md avant le premier backtest**, fenêtres = SES réglages tradés.
R1 : **PASSÉ** sur les 4 instruments, couche indicateur réellement inspectée
(precompute → DataFrame). R5 : **CONFORME** (0 divergence / 400 barres).
Sortie temporelle : **max_hold_bars transmis** au walk-forward ET au bras
témoin (engine_kwargs, commit 2188ac6) — le mur s91 §7.1 est levé.
Effectifs : 409-694 trades OOS par instrument (F6 : passée partout).

---

## 1. Ce que la source affirme

- **USDJPY 3-6h, SL = range opposé, pas de TP, clôture 18h, 1 breakout/jour**
  (transcript `03`, 10 ans Dukascopy) : 50k → 800k+, PF 1,27, WR < 50 %,
  gain moyen 2 888 vs perte moyenne 1 800 → **≈ +0,15 R/trade net**.
- 2 breakouts = +20 % de profit total, PF plus faible (`04`).
- XAUUSD 3:05-6:05, SL 1 % : « +15 k€ en 1 an » (`06`).
- GBPUSD 4:00-11:30, SL = range : backtest 10 ans PF 1,15, **live −8 778 € sur
  ~360 trades** depuis fin mars 2024 (`15`) — sa perte, documentée par lui.

## 2. Ce que nous mesurons

### 2.1 Walk-forward ancré + bras témoin (la référence depuis l'audit D2/D3)

| Instrument | config | honest R OOS | trades OOS | percentile témoin (200 tirages) |
|---|---|---|---|---|
| USDJPY | **SA config live** (1 brk, 3-6, SL range) | **−7,01 R** | 511 | **66,5** |
| USDJPY | 2 brk, 3-6, SL range | +25,07 R | 641 | 93,5 [EFFECTIF TÉMOIN ÉCARTÉ] |
| USDJPY | 2 brk, 3-5, SL range | +26,55 R | 694 | 97,0 [EFFECTIF TÉMOIN ÉCARTÉ] |
| XAUUSD | SA config (SL 1 %, filtre 0,15-0,85) | +15,33 R | 409 | 72,0 |
| XAUUSD | SL range, sans filtre | +5,17 R | 504 | 49,5 |
| GBPUSD | **SA config** (4-12, SL range) | **−17,10 R** | 428 | 52,5 |
| EURJPY | config défaut | −30,68 R | 513 | 55,5 |

**F1 (témoin mesuré, config par défaut USDJPY) : DÉCLENCHÉE** — percentile
66,5, très en dessous du seuil 95 déclaré. La config qu'il trade en live fait
ce que ferait un tirage au sort à dispositif de risque identique.

STRICT (archive, convention ininterprétable) : 1/24 USDJPY, 0 partout ailleurs.

### 2.2 F4 — Ablation du spread : le même mur que s91, au chiffre près

Config par défaut USDJPY, tranche de test 60-100 % (512 trades) :

```
    edge brut (spread nul)   +0,0637 R/trade
    péage mesuré             +0,0774 R/trade
    net                      −0,0137 R/trade      brut/péage = 0,82  (seuil déclaré : ≥ 1,5)
```

**F4 : DÉCLENCHÉE.** Plein échantillon : brut +0,0869, péage +0,0898 — le
péage consomme 100 % du signal. Sur 24 cellules USDJPY : réel 8/24 positives
(moy −0,0067), spread nul 20/24 positives (moy +0,0318). Il y a un signal
brut ; il vaut le prix du spread. **C'est exactement le diagnostic s91.**

L'économie a priori l'annonçait : SL = range USDJPY ≈ 31 pips → drag 9,1 %.
Le « stop large » du package n'existe qu'en variante SL 1 % (drag 1,9 %) —
mais en SL 1 % le signal brut tombe à +0,013-0,017 R/trade (le R est dilué
par la distance 5× plus grande) : net ≈ −0,007 à −0,004. **Les deux variantes
de SL échouent par les deux bouts opposés du même rapport signal/coût.**

### 2.3 F2 — Contrôle long/short : le claim USDJPY est du beta yen

| Config défaut, réel | R/trade | n | total |
|---|---|---|---|
| USDJPY LONG | **+0,0306** | 736 | +22,5 R |
| USDJPY SHORT | **−0,0483** | 544 | −26,3 R |

**F2 : DÉCLENCHÉE.** Tout le positif est côté long, sur la paire à +4 932
pips de dérive (carry yen). Le témoin le confirme sans stratégie : une entrée
LONG au hasard bat une entrée SHORT au hasard de +0,060 R/trade sur ces
barres. Son equity 10 ans USDJPY sans TP qui tient jusqu'au soir est, sur
notre période, majoritairement de la tendance capturée — pas un edge de
cassure. EURJPY, même signature en pire (long +0,013 / short −0,129) : c'est
la paire où il a perdu −2,5 k€, et notre harnais l'aurait dit d'avance.

### 2.4 F3 — Permutation horaire : l'ancrage de session n'est pas démontré porteur

À instrument constant, spread nul, géométrie figée (post-hoc, hors manifest) :

| variante | full R/t | train | **test** | n |
|---|---|---|---|---|
| 3-6h (la sienne) | +0,0869 | +0,1023 | **+0,0637** | 1280 |
| ctrl 9-12h | +0,0590 | +0,0797 | **+0,0275** | 1222 |
| ctrl 12-15h | +0,0518 | +0,0412 | **+0,0672** | 1081 |

**F3 : PARTIELLEMENT DÉCLENCHÉE.** L'ancrage 3-6h bat le contrôle 9-12h
(+0,036 OOS) mais PAS le contrôle 12-15h (−0,004 OOS). En plein échantillon
l'ancrage domine (+0,028/+0,035) ; hors échantillon l'avantage dépend du
témoin choisi. Contraste avec s91, où la porte horaire battait NETTEMENT les
fenêtres témoins ET le 24h/24. Ici, une part du « breakout de session » est
un simple « breakout + tenue longue » — la famille que s11 a tuée.

### 2.5 F5 — Conformité inverse GBPUSD : le test gagnant-gagnant, gagné

Sa config exacte (4-11:30 ≈ 4-12h, SL = range, 1 breakout, sans filtre,
clôture 18h), sa date de mise en live (fin mars 2024), sa perte (−8 778 €,
~360 trades, risque 500 €/trade ⇒ ≈ −17,6 R) :

| Période | trades | R | à 500 €/trade |
|---|---|---|---|
| pré-live (2021-07 → 2024-03) | 555 | **−36,72 R** | −18 362 € |
| post-live (2024-04 → 2026-08) | 502 | **−23,74 R** | −11 872 € |

Et le walk-forward complet sur sa config : **4 fenêtres OOS sur 4 négatives**
(−17,10 R, 428 trades), percentile témoin 52,5, aucune année positive sur 6.

**Triple lecture, toutes favorables à notre harnais :**
1. **Rejet ex ante** : appliqué à ses réglages, notre dispositif (WF + témoin)
   dit NON avant le premier euro — ce que son plein échantillon 10 ans
   Dukascopy (PF 1,15) ne disait pas. Le harnais détecte ce que son compte a
   payé pour apprendre.
2. **Le post-live colle au réel** : −0,047 R/trade mesuré vs ≈ −0,049 R/trade
   vécu par son compte (−17,6 R / 360). Deux mesures indépendantes du même
   phénomène, mêmes ordres de grandeur.
3. **Écart honnête à déclarer** : sur NOTRE pré-live (2021-2024), sa config
   perd déjà (−36,7 R) alors que son backtest Dukascopy du même segment était
   positif. Causes candidates, non départageables sans ses données : entrée
   au close H1 vs stop order M1 (notre dégradation déclarée — la plus
   probable : sur un range de 47 pips GBPUSD, 30-60 min de retard d'entrée
   coûtent cher), borne 11:30 vs 12h, données/spread différents. Cet écart ne
   change pas la conclusion F5 (les DEUX périodes sont négatives chez nous,
   et son live confirme le post) mais interdit de dire que nous avons
   « reproduit son backtest » : nous avons reproduit sa STRATÉGIE, dégradée
   H1, et elle perd partout.

### 2.6 Stabilité annuelle (USDJPY, sa config) — aucune

2021 −9,5 R · 2022 **+33,0** · 2023 **−35,9** · 2024 +19,2 · 2025 +12,0 ·
2026 −22,5. Total : **−3,7 R sur 1 280 trades** (−0,0029 R/trade). Trois
années sur six négatives, amplitude ±35 R : c'est un actif à variance, pas un
revenu.

### 2.7 Le résidu 2-breakouts — mesuré, non revendiqué

Son ablation `04` disait : la 2e cassure ajoute du volume, PF plus faible.
Notre mesure au R/trade dit l'inverse : **le trade #2 (retournement) est la
meilleure cellule du dossier** — +0,0888 R/trade × 367 trades réel, quand le
trade #1 fait −0,0029 × 1 280. Les configs 2-breakouts sont les seules à
approcher le témoin (percentiles 93,5-97,0) — **sous le seuil de 95 pour
l'une, dessus pour l'autre, avec [EFFECTIF TÉMOIN ÉCARTÉ] (le moteur exécute
~18 % de tirages aléatoires en moins que la stratégie) et une sélection
post-hoc parmi 24 cellules : percentile optimiste, non concluant.**

À noter ce que ce trade #2 EST : le prix a cassé un côté du range de nuit, a
échoué, et a retraversé tout le range. Acheter cette traversée, c'est fader
l'extension ratée de la fenêtre de faible liquidité — **structurellement le
trade de s91, retrouvé par le chemin inverse.** Deux dossiers indépendants
convergent vers le même résidu : « l'échec d'un mouvement né dans la fenêtre
mince est plus informatif que le mouvement lui-même ». Résidu à consigner
pour s90, pas un edge démontré.

## 3. L'écart avec la source, et son explication

| | Lui (claim) | Nous (mesuré) |
|---|---|---|
| USDJPY net | ≈ +0,15 R/trade (10 ans, in-sample, Dukascopy M1/tick) | **−0,003 R/trade** plein échantillon réel ; −7 R OOS ; brut spread nul +0,064 OOS |
| GBPUSD | backtest 10 ans PF 1,15, live −8,8 k€ | négatif partout, ex ante et ex post |
| XAUUSD | « +15 k€/an » | +0,035 R/trade réel toutes cellules positives, MAIS percentile témoin ≤ 72 : indistinguable d'un tirage au sort au même dispositif de risque sur un or en tendance (beta mesuré +0,142 R/trade) |

Explication de l'écart, par ordre de contribution mesurable :
1. **Beta yen** (F2) : son côté long portait la période — un backtest sans
   contrôle directionnel prend la tendance pour de l'edge.
2. **Sur-ajustement in-sample** (F5) : il optimise 10-15 ans plein
   échantillon puis trade l'optimum ; GBPUSD montre ce que ça coûte, et notre
   WF le détecte ex ante.
3. **Le péage** (F4) : même à supposer son signal réel, brut/péage = 0,8-1,0
   chez Swissquote H1 — il manque le même facteur ~1,5 que s91.
4. **Notre dégradation** (entrée close H1 vs stop order M1) : réelle,
   déclarée, défavorable au signal — elle explique une partie de l'écart
   pré-live GBPUSD (§2.5.3) mais pas F1/F2/F5, qui sont structurels.

## 4. VERDICT

# PAS D'EDGE

(pour la version reproductible chez nous : H1 Swissquote, entrée au close,
sortie temporelle approximée — dégradations déclarées en Phase 1)

1. **F1 déclenchée** : sa config live USDJPY au percentile 66,5 du témoin
   mesuré (511 trades OOS). Le moment d'entrée n'apporte rien.
2. **F2 déclenchée** : le positif est entièrement côté long sur la paire en
   carry — beta, pas edge. EURJPY : même signature, sa perte le confirme.
3. **F4 déclenchée** : brut/péage = 0,82 hors échantillon (seuil 1,5). SL
   large ⇒ signal dilué ; SL étroit ⇒ drag 9 %. Le rapport signal/coût est
   verrouillé des deux côtés.
4. **F3 partielle** : l'ancrage session ne bat pas systématiquement une
   fenêtre témoin hors échantillon.
5. **F5 : notre harnais est validé sur un cas réel à 8 778 €** — il rejette
   ex ante ce que son compte a payé, et notre post-live (−0,047 R/t) colle à
   son live (−0,049 R/t).
6. Effectifs 409-694 trades OOS : c'est un négatif **mesuré** (F6 passée).

**Recommandation : ne pas promouvoir. Statut RESEARCH maintenu.**

### 4.1 La réponse à la question centrale de la mission

**NON — le package Balke ne fait pas passer l'effet de session au-dessus du
seuil des coûts, et les deux mesures convergent.** s91 (fade) : brut OOS
+0,04-0,05, péage 0,06-0,10. s09 (breakout) : brut OOS +0,064, péage 0,077.
Même objet, même amplitude (~+0,05 R/trade brut), même déficit (facteur
~1,2-1,5), mesuré par deux exploitations OPPOSÉES de la même structure
horaire. **L'effet de session est réel, reproductible… et enterré des deux
côtés, fade ET breakout, chez un broker retail H1 forex.** La famille
breakout est close sous ses deux formes (glissante s11, ancrée s09). Ce qui
reste du corpus Balke : le protocole de conformance (A1) et la leçon
d'exécution (A2) — et le résidu du trade de retournement (§2.7).

## 5. Ce qui est transférable vers s90_adrian_synthesis

1. **La frontière signal/coût de l'effet de session est confirmée par une 2e
   mesure indépendante : ~+0,05-0,06 R/trade brut, péage 0,06-0,10.** Toute
   exploitation H1 forex retail de l'heure seule est sous l'eau d'un facteur
   ~1,5. La seule voie reste l'instrument à faible péage relatif (s91 §5.1) —
   XAUUSD a ici le meilleur rapport (drag 3,3 %) et est le seul instrument
   positif toutes cellules à spread réel, mais ne dépasse pas son témoin :
   sur l'or, le péage n'est plus le tueur, c'est le beta qui absorbe tout.
2. **Le résidu retournement** (§2.7) : troisième apparition du motif « fade
   de l'échec de la fenêtre mince » (s91 fade brut positif ; s09 trade #2
   +0,089 R/t ; les configs 2-brk seules à approcher p95). Si s90 teste une
   chose issue de ce dossier, c'est celle-là — avec témoin à effectif
   corrigé.
3. **F5 comme méthode** : rejouer la config exacte d'un tiers sur sa période
   pré/post live est le test de validation du harnais le moins cher qui
   existe. À refaire pour toute source qui publie ses pertes.
4. **Leçon d'économie a priori** : « stop large donc drag faible » doit se
   VÉRIFIER — SL = range de nuit est un stop ÉTROIT (30 pips USDJPY). Le
   drag se calcule avant de coder (dix lignes, METHODOLOGY §2).

## 6. Limites de ce test

1. **Entrée au close H1** au lieu du stop order M1 au bord du range : la
   dégradation la plus sérieuse. Elle retarde l'entrée jusqu'à 1h et paie un
   prix pire que le bord. Une réfutation de cette version ne réfute pas la
   version M1 exécutée chez IC Trading — mais F2 (beta) et F5 (son propre
   live GBPUSD négatif) ne dépendent pas de cette dégradation.
2. **Sortie 18h approximée par max_hold_bars fixe** (11-12 barres) : 38 %
   seulement des sorties USDJPY tombent à 17-19h (méd 17h, p90 20h — les
   sorties précoces sont des SL, normales ; les tardives sont la dérive
   déclarée). Le témoin subit la même règle : la comparaison est équitable,
   mais la fidélité à « 18h pile » est partielle.
3. **5,1 ans, un seul régime macro** (vs ses 10 ans) : le carry yen domine
   la période — d'où la place centrale donnée au témoin directionnel.
4. **Percentiles témoin optimistes** sur cellules sélectionnées (max-of-24) ;
   [EFFECTIF TÉMOIN ÉCARTÉ] sur les cellules 2-breakouts (écart ~18 %).
5. **Slippage 0** (hypothèse la plus favorable) : tout slippage réaliste
   aggrave le verdict, comme s91 §2.10 l'a chiffré.
6. Bornes non pleines (4:30, 11:30, 3:05, 18:55) arrondies à l'heure ;
   déclaré par cellule. Fuseau calibré (GMT+3 = IC), pas garanti barre à
   barre à travers les bascules DST.
7. Je suis le reproducteur ET l'évaluateur ; falsifications figées avant le
   premier backtest (FALSIFICATION.md), grille jamais modifiée après lecture
   des résultats. Le contrôle F3 est post-hoc et déclaré tel.

## 7. Fichiers produits

| Fichier | Contenu |
|---|---|
| `research/economics.py` / `.txt` | Phase 1 : fuseau (GMT+3), taille de range, drag, heures de cassure |
| `research/ANALYSIS.md` | Phase 1 : méthode, reproductibilité, dégradations déclarées |
| `research/FALSIFICATION.md` | F1-F6 + grille, **figées avant tout backtest** |
| `strategy.py` / `manifest.yaml` | Implémentation R1-R10, magic 130009 |
| `backtests/causality.txt` | R1 archivé (4 coupures, couche indicateur inspectée) |
| `backtests/conformance.txt` | R5 archivé (0 divergence / 400 barres) |
| `backtests/run_wf.py` / `anchored_wf_{USDJPY,XAUUSD,GBPUSD,EURJPY}.txt` | WF ancré + bras témoin (engine_kwargs transmis aux deux) |
| `backtests/diagnostics.py` / `diagnostics.txt` | Ablation spread (F4), long/short (F2), permutation (F3), F5 pré/post live, stabilité annuelle, 1 vs 2 breakouts |
