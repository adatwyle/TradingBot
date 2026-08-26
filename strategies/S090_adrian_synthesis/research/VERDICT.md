# Verdict — s90_adrian_synthesis « fade de l'échec »

Source : synthèse des quatre mesures antérieures du motif (s91, s09 §2.7, s10, `studies/grid_per_entry`).
Protocole : `research/HYPOTHESIS.md`, **figé et commité (`f1e9d0c`) AVANT tout backtest** — grille 6 cellules, univers 17 instruments, falsifications F1-F8, règles de verdict écrites d'avance.
Données : MT5 Swissquote H1, snapshot figé 2021-07 → 2026-08-14 (17 849 à 31 594 barres/instrument), le même que l'étude grid.
Coûts : spread catalogue + slippage 0,5 pip, payés aux deux bouts, pour tout chiffre « réel ».
Moteur : commun R9, `engine_kwargs` explicites identiques stratégie/témoins (`max_positions=1, cooldown_bars=2, cb_losses=3, cb_cooldown_bars=24, max_hold_bars=None`).
R1 (causalité) : **PASSÉ** — CLI sur EURUSD (sauvé `backtests/causality.txt`) + XAUUSD + NIKKEI, complément runner sur USDCHF/NASDAQ/XAGUSD × 3 seuils × 2 coupures. Couche indicateur couverte (precompute → DataFrame).
R5 (conformité) : **CONFORME** (garantie structurelle — on_bar délègue ; `backtests/conformance.txt`).
Moteur/commit du run : `f1e9d0c`, `git status --porcelain core` propre (seule trace externe : `s93 conformance.txt`, session parallèle).
Log complet : `research/out/run_validation.txt` (53 min), rapports WF par instrument `research/out/wf_<SYM>.txt`.

---

## 1. Les falsifications déclarées, confrontées aux chiffres

| # | Condition figée | Mesuré | Déclenchée ? |
|---|---|---|---|
| **F1** — hasard, par cellule (témoin apparié 200 tirages, non conditionné) | 4 cellules ≥ p95 sur 102 : XAUUSD t3_sl1 (pct 96,5), XAUUSD t3_sl2 (95,5), NASDAQ t2_sl2 (95,0), AUDCAD t4_sl2 (99,5 ; 42 tr) | franchie par un noyau restreint |
| **F2** — généralité hors découverte (le juge) | R/t OOS NET de la cellule primaire, poolé sur les 8 instruments hors découverte économiquement viables : **−0,1485 [−0,2009 ; −0,0962], n = 1 337** — et **−0,0570 même à coût nul** | **OUI — le cœur du verdict** |
| **F3a** — ≥ 2 instruments hors découverte passent F1 | **0** instrument hors découverte ne passe F1 sur une cellule de seuil ≥ 3 (NASDAQ passe sur t2 = la sonde dose-réponse, pas le motif) | **OUI** |
| **F3b** — témoin conditionné à l'état (réserve grid §5.7) | EURUSD pct 25,0 / E_c −0,233 ; DAX pct 17,0 / E_c −0,106 → **issue 3 (artefact)**. XAUUSD t3_sl1 pct 98,5 / E_c −0,029 → issue 1 pour XAUUSD seul | mixte — voir §3 |
| **F4** — deux sens | Pool primaire : LONG −0,098 / SHORT −0,070 (découverte), LONG −0,130 / SHORT −0,159 (hors découverte) — les deux sens PERDENT | sans objet (rien à requalifier : tout est négatif) |
| **F5** — multi-graines | Les 4 cellules F1 sont stables (4-5/5 graines ≥ 95) | non déclenchée — le résidu n'est pas un artefact de graine |
| **F6** — effectifs | 1 337 trades poolés hors découverte ; 191 XAUUSD ; AUDCAD t4 = 42 tr (mince) | non déclenchée sur le verdict principal |
| **F7** — ablation coûts | Pool primaire viable à coût nul : **−0,0342** (n = 1 832) ; hors découverte coût nul **−0,0570** | **le péage n'est PAS l'explication : le signal est absent même gratuit** |
| **F8** — dose-réponse (prédiction centrale de H90) | R/t poolé viables, sl 1 : t2 −0,125 / t3 −0,131 / t4 −0,134 ; sl 2 : −0,052 / −0,065 / −0,064. **Plus profond n'est PAS meilleur.** Et la seule cellule multi-instrument passante est t2 (NASDAQ) — le seuil que H90 prédisait ≈ ≤ 0 | **OUI — le mécanisme causal est réfuté** |

## 2. La mesure centrale — le juge dit non

La question figée était : *l'effet existe-t-il hors des 3 instruments qui ont
servi à le découvrir ?* Réponse, cellule primaire (excursion ≥ 3 ATR, tp 1 ATR,
sl 1 ATR), walk-forward ancré, coûts réels :

| pool | R/t OOS réel | IC 95 % | n | coût nul |
|---|---|---|---|---|
| découverte (EURUSD/XAUUSD/DAX) | −0,0819 | [−0,1680 ; +0,0042] | 495 | +0,0274 |
| **hors découverte viables (LE JUGE)** | **−0,1485** | **[−0,2009 ; −0,0962]** | **1 337** | **−0,0570** |
| hors découverte tous | −0,2203 | [−0,2581 ; −0,1825] | 2 344 | −0,0266 |
| univers viable entier | −0,1306 | [−0,1753 ; −0,0858] | 1 832 | −0,0342 |

Par instrument (primaire, réel) : **15 négatifs sur 17**. Seuls positifs :
XAUUSD (+0,0938 × 191, pct 96,5) et NASDAQ (+0,0173 × 215, pct 87,5 —
indistinguable du hasard). Chaque instrument hors découverte viable est
individuellement négatif ou sous le témoin : USDJPY −0,243, EURJPY −0,240,
SP500 −0,139, FTSE −0,222, NIKKEI −0,313, XAGUSD −0,107, WTIUSD −0,077,
NASDAQ +0,017 (pct 87,5).

L'IC 95 % du juge exclut zéro de très loin, sur 1 337 trades — et le même
pool reste négatif À COÛT NUL. Ce n'est pas le péage qui tue le motif (le
scénario s91) : **le signal lui-même n'existe pas en dehors de l'ensemble de
découverte.**

## 3. Le résidu XAUUSD — réel, mais un seul instrument

Ce qui survit à tout : **XAUUSD t3_sl1 = exactement la cellule de l'étude
grid** (+17,92 R, +0,0938 R/t × 191 — chiffre identique, mêmes barres, même
construction : la cohérence des chemins est vérifiée, ce n'est pas une
réplication indépendante). Elle passe le témoin non conditionné (96,5),
5/5 graines (96,5-99,0), et — seule de tout le dossier — le témoin
CONDITIONNÉ à l'état d'excursion (pct méd 98,5 sur 5 graines) : sur l'or, le
palier précis ajoute de la valeur au-delà du simple fait d'être dans
l'excursion. Sa voisine t3_sl2 est cohérente (+0,0425, pct 95,5 non
conditionné, 93,5 conditionné). Réserve : l'effectif des témoins conditionnés
est écarté (le moteur exécute ~25 % de tirages en moins — les barres d'état
sont agglutinées) ; le percentile conditionné se lit avec cette méfiance.

Mais la règle écrite d'avance est sans ambiguïté : **un seul instrument =
anecdote, pas motif** (F2/F3a ; déjà la règle de l'étude grid). Et XAUUSD
appartient à l'ensemble de DÉCOUVERTE : c'est précisément la cellule qui a
fait « passer » l'étude n°4. La retenir seule maintenant serait la définition
de la sélection post-hoc que ce protocole était construit pour interdire.

Les deux autres vedettes s'effondrent dès qu'on les traduit en géométrie
défendable :
- **EURUSD** : son « pass » grid était r3_G1 — stop à 6 ESPACEMENTS, le proxy
  déclaré du « pas de stop » du grid, exclu a priori de s90 comme
  indéfendable en production. En RR 1:1 honnête : **−0,2077 R/t × 214**,
  pct 51,5 — rigoureusement rien.
- **DAX** : son « pass » grid était r3_G3_s0.5 = seuil réel 1,5 ATR — SOUS le
  seuil de sur-extension de H90. À 3 ATR : **−0,1561 × 90**, pct 26,5. Et
  son témoin conditionné dit « artefact » (pct 17, E_c −0,106).

## 4. VERDICT

# PAS D'EDGE — le motif « fade de l'échec » est CLOS

1. **F2 déclenchée** : sur les 8 instruments hors découverte économiquement
   viables — le test que les quatre apparitions n'avaient jamais subi — la
   règle perd −0,15 R/trade net (IC 95 % excluant zéro, 1 337 trades) et
   perd encore à coût nul. L'effet n'est pas général. Par les règles figées
   d'avance : le verdict est PAS D'EDGE et il CLÔT le motif.
2. **F8 déclenchée — le mécanisme causal est réfuté** : H90 prédisait que la
   qualité par trade croît avec la profondeur de l'excursion. Mesuré : plate
   à légèrement DÉCROISSANTE (−0,125 → −0,131 → −0,134), et la seule cellule
   passante multi-instrument est au seuil 2 ATR (NASDAQ), celui que H90
   donnait perdant. Il n'y a pas de « sur-extension qui se rétracte » —
   il y a du bruit, et un cas particulier doré.
3. **La réserve §5.7 de l'étude grid est instruite et tranche CONTRE le
   motif** : au témoin conditionné à l'état d'excursion, EURUSD (pct 25) et
   DAX (pct 17) sont des artefacts du témoin non conditionné ; l'état
   d'excursion lui-même est PERDANT en entrée aléatoire partout (E_c < 0 sur
   les 6 cibles testées, toutes graines).

### 4.1 Les quatre apparitions, relues avec ce résultat

| Apparition | Ce qu'elle mesurait | Relecture |
|---|---|---|
| s91 (fade asiatique) | brut +0,05 R/t, tué par le péage | cohérent : ici aussi le brut poolé est ≤ 0 à coût nul hors or — s91 était déjà l'absence d'edge exploitable |
| s09 §2.7 (retournement +0,089 × 367) | percentile 93,5-97 avec effectif témoin écarté | jamais passé p95 proprement — reste ce qu'il était : non concluant |
| s10 (résidu NIKKEI) | seul au-dessus du hasard dans son dossier | ici NIKKEI est le PIRE instrument du pool (−0,313 × 131, pct 1,5) : le résidu s10 ne se transfère pas — c'était une cellule sur 210 |
| grid n°4 (la « décisive ») | 3 instruments ≥ p95 | 1 seule des 3 cellules survit à une géométrie défendable (XAUUSD) ; EURUSD tenait au stop 6 espacements, DAX au seuil 1,5 ATR. La « convergence de 4 chemins » était une convergence de sélections |

Les chiffres sont COHÉRENTS entre les 4 chemins et avec ce dossier : partout
un brut mince ou nul en moyenne, partout une ou deux cellules brillantes sur
des dizaines regardées, jamais deux fois la même. C'est la signature de la
sélection, pas d'un phénomène.

### 4.2 Ce qui aurait fait dire autre chose (auto-contrôle)

Si le pool hors découverte avait été positif net (même +0,01 R/t) avec ≥ 2
instruments passant leur témoin, le verdict était EDGE CANDIDAT et la seule
étape suivante un forward-test scellé façon gold_forward — le paragraphe de
proposition était prêt. Si le pool avait été positif brut mais négatif net,
le verdict était « signal réel non exploitable » (l'issue s91). Aucun des
deux ne s'est produit : le pool est négatif brut ET net. Il n'y a pas de
version de ces chiffres qui soutienne le motif.

### 4.3 Conséquences

- **Le motif « fade de l'échec » est clos.** Aucune cinquième instruction
  sans donnée NOUVELLE (autre broker/coûts, autre granularité, autre
  période) — pas une cinquième relecture des mêmes barres.
- **s90 reste RESEARCH, non promue.** La stratégie est correcte, validée
  R1/R5, et son verdict est : ne pas trader.
- **Le résidu XAUUSD est consigné, pas revendiqué** : une cellule stable
  multi-graines qui bat même le témoin conditionné, sur UN instrument de
  l'ensemble de découverte. La seule suite honnête, SI Adrian veut la payer,
  serait de l'observer en forward scellé comme pur test d'hypothèse
  (motif gold_forward, zéro argent) — **non proposée comme candidate
  production** : les règles figées de ce dossier la classent anecdote, et la
  probabilité a priori qu'une cellule de découverte tienne en forward est
  exactement ce que ce dossier vient de mesurer partout ailleurs : nulle.
- Pour le mandat de la nuit (« trouver une stratégie passable en
  production ») : **ce dossier répond NON pour le meilleur candidat du
  projet.** C'est le livrable : la voie la plus prometteuse du corpus est
  fermée proprement, avec le protocole le plus dur qu'on ait appliqué.

## 5. Limites

1. **Folds emboîtés** — les 4 fenêtres OOS ne sont pas indépendantes
   (METHODOLOGY §9). Vrai pour la clôture aussi ; mais elle repose sur un
   signe net à 1 337 trades, pas sur une nuance.
2. **Mono-régime** — 5,1 ans sans krach ; le verdict porte sur l'espérance,
   la seule chose que ces données savent mesurer.
3. **Effectif des témoins conditionnés écarté** (~75 % des trades de
   référence exécutés) : leurs percentiles sont indicatifs. Ils ne portent
   pas le verdict (F2/F8 suffisent) ; ils ne font qu'éclairer le résidu.
4. **6 forex sur 17 instruments sont morts sur papier** (drag > 25 % à cible
   1 ATR) : pour eux, seule la lecture à coût nul informe — elle est
   négative ou nulle partout sauf accidents isolés.
5. La cellule NASDAQ t2_sl2 (+0,0243 × 426, pct 95,0, 4/5 graines, mais
   pct conditionné 92,5 et E_c < 0) est un franchissement limite sur la
   sonde dose-réponse — 1 cellule sur 102, attendue ~5 par hasard sous la
   convention. Consignée, non instruite : elle contredit H90 au lieu de la
   soutenir.

## 6. Fichiers produits

| Fichier | Contenu |
|---|---|
| `research/HYPOTHESIS.md` | Protocole figé avant exécution (commit `f1e9d0c`) : H90, règle complète, univers, F1-F8, mapping F3b, règles de verdict |
| `research/ANALYSIS.md` | Source, reformulation, composants, risques |
| `strategy.py` | `StrategyModule` conforme, magic 130090, precompute → DataFrame |
| `manifest.yaml` | R7 — source de vérité (statut RESEARCH, verdict référencé) |
| `research/run_validation.py` | P0 économie → P6 témoin conditionné |
| `research/out/run_validation.txt` | Log complet (P0-P6, 53 min) |
| `research/out/wf_<SYM>.txt` | 17 rapports walk-forward détaillés |
| `backtests/causality.txt` | R1 CLI (EURUSD) |
| `backtests/conformance.txt` | R5 CLI |
| `research/VERDICT.md` | Ce document |
