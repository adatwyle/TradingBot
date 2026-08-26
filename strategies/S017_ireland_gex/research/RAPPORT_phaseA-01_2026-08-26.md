# RAPPORT Phase A — session 01 — S017 ireland_gex — 2026-08-26

Session cc-S017 n°2. Statut : **RESEARCH** (inchangé). Collecte quotidienne désormais planifiée (tâche Windows 14:55 CH jours ouvrés → `C:\db\tradingBot\S017\`).

## 1. Fait

| Livrable | Chemin | État |
|---|---|---|
| Harnais Phase A incrémental | `research/phase_a.py` | **Une commande relançable** : recharge TOUS les jours snapshotés, mesure H1 (contacts niveaux vs 3 groupes placebo, horizons 15/30/60 min, IC Wilson 95 %), H2 (régime gamma vs RV/range/efficience, 1 pt/jour), comptage setups A+ (checklist 5 conditions + issue en R), réécrit `PHASE_A_LOG.md` |
| Bibliothèque partagée | `research/signal_lib.py` | Indicateurs, chargements, détection cassures paramétrée, inventaire snapshots GEX avec flags qualité, placebos déterministes (seed = date), IC Wilson — réutilisée par phase_a et étude 03 |
| Tests unitaires | `research/test_signal_lib.py` | **14/14 verts** (Wilson CI, walk R, first-touch multi-horizon, détection cassures) |
| Étude 03 (H3/H3b) | `research/etude_03_volume_cap.py` + `etude_03_volume_cap.md` | Balayage fenêtre volume `[vol_mult, vol_cap)` (16 fenêtres) + grille compression (16 définitions) sur 60 j / 134 cassures |
| Variante H3b déclarée AVANT mesure | `spec-strategie.md` §3.5 + §4, `manifest.yaml` (`vol_cap`) | Plafond de volume {none, 2.0, 2.5, 3.0} avec justification (étude 01 bootstrap) — conformité anti-overfitting |
| Squelette stratégie | `strategy.py` | Sous-classe `StrategyModule` du socle (import lecture seule), 5 conditions encodées dans un `_decide()` unique partagé backtest/live (R5 by design), métadonnées gamma− pour core/risk (R2), **selftest : invariant de troncature R1 OK sur 3 points de coupe**, 0 signal sur les données actuelles (attendu) |
| Durcissement collecte | `research/daily_snapshot.py` | Garde anti-écrasement : le snapshot canonique pré-market est désormais write-once (2e run du jour → auto-suffixe intraday) |
| Log incrémental | `research/PHASE_A_LOG.md` | Généré, conçu pour relecture directe par Adrian |

## 2. Mesuré (données du jour : 1 jour GEX, 60 j OHLCV)

**H1 / H2 / setups A+ (phase_a.py)** — plomberie validée de bout en bout, tous les verdicts étiquetés **n insuffisant** :
- H1 : 1 contact majeur (765 cassé avec pénétration 4.2 ATR — anecdote cohérente gamma−), 0 placebo touché sur le jour partiel.
- H2 : 1 jour négatif (RV 0.20 %, jour partiel 24 barres).
- Setups A+ : 0 sur 1 jour — attendu, la checklist est très sélective (la vidéo revendique 2-3/semaine).

**Étude 03 (134 cassures, 60 j)** — directions d'effet, rien d'établi (IC larges, 32 variantes balayées) :
- **H3b (plafond)** : tranche [1.5, 2.0)× → 57 % +1R (n=7) vs ≥2.0× → 27 % (n=11). La direction « spike extrême = épuisement » persiste depuis le bootstrap.
- Fenêtre élargie [1.2, 2.0)× : 44 % +1R (n=18) vs référence toutes cassures 33 % (n=134) — piste d'un `vol_mult` plus bas AVEC cap, à suivre.
- Compression : le défaut (6 barres ≤ 1.5×ATR) donne le meilleur taux du balayage (39 % sur cassures à volume) ; plus large ou plus étroit dilue.
- **Observation inattendue à suivre** : la sous-population 5min-EMA-alignée seule (sans GEX ni volume) sous-performe (21 % +1R, n=57, vs 33 % global). L'alignement n'a peut-être de valeur qu'en combinaison — ou pas. À re-mesurer à mesure que n grandit.

**Data quality** : le canonique du 2026-08-26 a été capturé 2× (09:18 puis 11:28 ET, la 2e a écrasé la 1re → flag `multi-capture` dans le log). Corrigé structurellement (write-once). Jour partiel (OHLCV arrêté à 11:25 ET au moment du snapshot).

**Validation croisée externe** : aucun dashboard GEX gratuit lisible par simple HTTP (GravityGEX/FlashAlpha = rendu JS, AlgoStorm = challenge Cloudflare, non contourné). Passé — la référence externe reste la géométrie des frames ITMatrix (bootstrap).

## 3. Verdicts provisoires

| Hypothèse | n | Verdict |
|---|---|---|
| H1 (réaction niveaux GEX vs placebo) | 1 contact majeur / 1 jour | **n insuffisant** — plomberie validée |
| H2 (régime vs volatilité réalisée) | 1 jour (0+/1−) | **n insuffisant** |
| H3 (volume ≥1.5× aide) | 18 avec / 116 sans | **n insuffisant** — direction favorable stable |
| H3b (plafond volume, déclarée ce jour) | 7 vs 11 | **n insuffisant** — direction favorable (2 mesures de suite) |
| H4 (système complet) | 0 setup | **non mesurable** (attend accumulation + TCK-003) |
| H5 (pinning) | — | **non mesuré** (attend ≥ 60 jours de cartes) |

## 4. Commande unique de ré-agrégation (hebdo ou à volonté)

```
cd C:\projects\tradingBot\strategies\S017_ireland_gex
python research/phase_a.py          # H1 + H2 + setups A+ -> research/PHASE_A_LOG.md
python research/etude_03_volume_cap.py   # optionnel : H3/H3b -> etude_03_volume_cap.md
```

Aucun argument, aucune préparation : chaque run recharge tout `C:\db\tradingBot\S017\` et réécrit les logs (git porte l'historique des runs).

## 5. Attentes aux jalons

**n ≥ 5 jours (≈ fin de semaine prochaine)** :
- Vérifier que chaque jour produit 2-5 niveaux majeurs et ≥ 1 contact (sinon, questionner `level_major_frac`/`level_top_k`).
- Premiers ratios P(hold) major vs placebo — bruit dominant, servent uniquement à roder l'agrégation.
- H2 : les deux régimes devraient commencer à apparaître ; si 5 jours 100 % négatifs, noter le biais d'échantillon.
- Setups A+ : 0-2 attendus au total ; chaque setup détecté est à inspecter manuellement (sanity de la checklist).

**n ≥ 20 jours (≈ fin septembre)** :
- ~50-100 contacts majeurs cumulés → première lecture H1 avec IC exploitables ; si P(hold|major) ≤ P(hold|placebo) de façon persistante, H1 est en difficulté — c'est le cœur de l'edge revendiqué.
- H3/H3b : n par tranche ×3 → décision possible sur la promotion du cap en défaut si la direction tient avec n ≥ 30 par tranche.
- Point de décision TCK-004 (achat historique GEX) : uniquement si H1 montre un signal.

## 6. Préconisation cc-S017 pour le jalon n ≥ 5 jours

Laisser tourner la collecte sans intervention ; relancer `phase_a.py` au jalon ; **aucune décision d'achat ni d'extension socle avant la première lecture H1 à n ≥ 20 jours**. Seule action externe utile d'ici là : livraison TCK-003 (extension socle) par cc-app, pour brancher `strategy.py` (déjà prêt, R1 validé) dès que possible.
