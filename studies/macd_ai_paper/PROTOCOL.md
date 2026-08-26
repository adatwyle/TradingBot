# PROTOCOLE — Essai à blanc « Daily MACD assisté par IA » (s12 + juge headless)

> **Ce fichier est un scellé.** Il est écrit **avant** le premier signal mesuré
> et avant le premier jugement du rejeu, et ne doit plus être modifié ensuite.
> Il fixe la configuration, les bras, les falsifications chiffrées et la façon
> dont le verdict sera rendu. Toute conclusion future se lit contre ce qui est
> écrit ici, et nulle part ailleurs. Motif repris de
> `studies/gold_forward/PROTOCOL.md` — la valeur entière du dispositif tient à
> l'impossibilité de tricher rétroactivement.

**Date de scellement** : 2026-08-16
**Origine** : mandat Adrian « Daily MACD assisté par IA — est-ce envisageable ? »
**Décision de lancer** : Adrian (session autonome de nuit).

---

## 0. LE CONTEXTE QUI CHANGE LA QUESTION — verdict mécanique tombé pendant la construction

`strategies/s12_prt_macd_meanrev/research/VERDICT.md` (commit `a28cf16`) :
**PAS D'EDGE**. −0,006 R/trade à spread nul sur SP500 10 ans, percentile 51,5
contre le témoin aléatoire, et sur 99 ans les jours en position font +0,8 %/an
contre +6,4 % au buy & hold (F3 : retirer ces jours AMÉLIORE le B&H).

**Le socle mécanique est mesuré mort.** La question testée ici n'est donc PAS
« la stratégie marche-t-elle » (réponse connue : non) mais :

> **Une session Claude Code, jouant le gestionnaire de risque sur des dossiers
> factuels, peut-elle extraire un sous-ensemble profitable d'un flux de
> candidats dont l'espérance moyenne est mesurée nulle/négative ?**

Précédent direct : `strategies/s93_alexg_ai_judge/research/VERDICT.md` — un
juge IA sur une grille rituelle (flux fxalexg H1) a répondu **NON** (percentile
88,5 < seuil 95, structure interne du grading contradictoire). Ce dispositif
doit pouvoir rendre le même verdict honnêtement si c'est la réalité.

## 0bis. LE PROBLÈME DE FRÉQUENCE — chiffré, et la hiérarchie qui en découle

Cellule scellée sur MT5 D1 (2016→2026) : SP500 56 signaux, NASDAQ 53, DAX 56
— soit **~15 signaux/an sur les trois indices réunis** (~5/an sur SP500 seul :
un dispositif mono-instrument mettrait ~8 ans à atteindre N=40). Même à trois
flux, N=40 décisions IA ≈ **3 ans de forward**. Le runner temps réel seul ne
peut PAS répondre en temps utile.

**Hiérarchie du dispositif — écrite d'avance :**

1. **Couche 1 — rejeu à l'aveugle accéléré** (`replay_*`) : les candidats
   HISTORIQUES de la cellule scellée (MT5 3 indices 2016→2026 + LONGHIST
   SP500 1927→2015 et NASDAQ 1971→2015, coupés à 2016 pour ne pas recouvrir
   MT5), anonymisés selon le motif s93 (id opaque, ordre mélangé graine
   20260816, pas de dates, prix en unités d'ATR), jugés par sous-agents avec
   LE MÊME prompt gestionnaire de risque que le runner. Sous-échantillon
   déterministe de 400 candidats max (graine 20260816). C'est CETTE couche
   qui répond à la question d'Adrian cette semaine.
2. **Couche 2 — runner temps réel** (`run_paper.py`) : la confirmation
   prospective. **À armer SEULEMENT si la couche 1 montre un signal**
   (percentile ≥ 95, § 4). Sans signal en couche 1, l'armement est un
   gaspillage mesuré d'avance.

---

## 1. Configuration FIGÉE

Source unique : `studies/macd_ai_paper/params.json`.

### 1.1 Le scellé cryptographique

```
SHA-256(params.json) = 36b635bd775bef284456000d73ca7c39ff420551d27265a7fd382cb372a20a5b
```

Répliqué dans `PARAMS_SHA256` de `run_paper.py` (partagé par tous les
scripts). Refus de tourner si divergence (exit 3). Le test
`test_paper_step.py::test_hash_du_vrai_fichier_scelle_correspond` casse à la
moindre divergence.

### 1.2 Contenu (copie de lecture — `params.json` fait foi)

| Élément | Valeur |
|---|---|
| Stratégie | `s12_prt_macd_meanrev` — le code de `strategies/s12_prt_macd_meanrev/strategy.py` est IMPORTÉ (R5, une seule implémentation du signal) |
| Cellule | `range_len 20 · pos_max 0,20 · no_friday false · sl_atr 3,0 · close_down true · macd_rel false` — les règles du mandat (dont `close < close[1]`) ; stop 3 ATR (variante gérée : un « sans stop » 10 ATR rend le sizing à 1 % dérisoire et l'essai illisible) |
| Instruments / TF | **SP500, NASDAQ, DAX / D1** (barres MT5 Swissquote) — trois flux pour la fréquence, § 0bis |
| Spread | catalogue `core/data/instruments.py` (SP500 5, NASDAQ 8, DAX 8 pips de 0,1), demi-spread payé à chaque extrémité ; slippage 0 (déclaré optimiste, comme gold_forward) |
| Exécution | conventions du moteur commun répliquées : entrée au close du signal + coût ; stop unilatéral, gap payé à l'ouverture ; la cible ne profite pas du gap ; SL prime sur TP ; coût aussi en sortie ; une position par bras et par instrument ; cooldown 2 barres ; circuit breaker 3 pertes → 24 barres |
| Compte virtuel | 10 000 par bras, risque de base 1 %/trade via `RiskLayer` (`core/risk/guards.py`) — l'IA propose, la couche risque dispose |
| Bornes IA | `size ∈ [0;1]` (fraction du 1 %), `sl_adjust ∈ [0,5;1]`, `tp_adjust ∈ [0,5;1]` (resserrage seulement) — clampées par `clamp_decision` PUIS re-bornées par RiskLayer (défense en profondeur, le prompt n'est jamais la seule barrière) |
| Juge headless | `claude -p "<prompt>" --output-format json` (syntaxe vérifiée sur claude 2.1.152) ; timeout 120 s ; UNE relance ; échec persistant → bras IA **N/A pour ce signal**, témoins jamais affectés |

Note de convergence : `close_down=true` est l'addendum de fidélité de s12
(défaut du manifest : false). La cellule scellée ici est autonome ; si s12
évolue, ce scellé ne bouge pas.

---

## 2. LES TROIS BRAS — journalisés à chaque signal

| Bras | Décision d'entrée | Taille / niveaux |
|---|---|---|
| **MECH** | prend tout signal (quand flat sur l'instrument) | base : 1 %, niveaux stratégie |
| **AI** | la session headless : `take/skip` | `size × 1 %`, SL/TP resserrés dans les bornes |
| **RND** | tirage au **taux historique du bras IA** (`takes/décisions`, recalculé à la volée ; 1,0 avant la première décision), déterministe par (graine 20260816, instrument, barre) | base : 1 %, niveaux stratégie |

Plus **SHADOW** (comptable, pas un compte) : chaque signal ouvre un
contrefactuel à configuration de base, sans blocage ni cooldown — le R par
signal qui alimente F1 et F2 indépendamment de l'état des comptes.

Panne du CLI (`is_error`, timeout, JSON illisible, 401…) : décision `na`
journalisée, non comptée comme décision, taux RND inchangé, MECH/RND
continuent. **Une panne d'IA ne fausse jamais les témoins.**

---

## 3. Ce qui est mesuré, et comment

**Journal** : `C:\db\tbot\macd_ai_paper\journal.csv` — append-only à chaîne de
hachage (chaque ligne porte le SHA-256 du fichier avant elle), double
horodatage (barre + mesure), vérifié avant toute écriture (exit 4 si altéré).
Événements : `DECISION` (IA : take/skip/na + taille + ajustements + raison une
phrase ; RND : take/skip + taux + tirage), `OPEN`/`CLOSE` par bras,
`SHADOW_OPEN`/`SHADOW_CLOSE`. État par bras dans `state.json`, lecture dans
`status.json`.

**Idempotence** : un curseur par instrument ; deux passages sur les mêmes
barres n'ajoutent rien et **ne rappellent pas le juge**. MT5 indisponible →
exit 2, journal intact. Instrument partiellement indisponible → sauté ce
passage, curseur immobile.

**Premier passage = pose du scellé** : aucun signal historique n'entre au
journal. Aucun trade au premier passage est le comportement attendu.

---

## 4. LES FALSIFICATIONS — chiffrées d'avance, c'est le cœur

### Couche 1 — rejeu à l'aveugle accéléré (`replay_measure.py`)

Mesure : R **net** par candidat (outcome indépendant aux conventions moteur,
précédent s93), somme des R des candidats PRIS par le juge, percentile contre
**1000 tirages aléatoires de même effectif** dans le même pool (graine 20260816).

* **F1-rejeu (centrale)** : sur n ≥ 40 candidats jugés, percentile **< 80** →
  la sélection IA n'ajoute rien à l'aléatoire de même taux. **NO-GO armement
  du runner.** (Rappel s93 : 88,5 était un échec contre un seuil à 95 ; ici le
  seuil de rejet est 80 et le seuil de signal reste **≥ 95** — entre les deux :
  zone grise, décision Adrian documentée requise, pas d'armement par défaut.)
* Lectures imposées en regard : prendre-tout (le socle : attendu ≈ négatif),
  split MT5 seul / LONGHIST seul, sizing gradué (corrélation taille/R),
  resserrage SL/TP (delta R des pris, base vs ajusté). Un juge qui prend tout
  ou ne prend rien → **NON CONCLUSIF** (sélection non informative).

### Couche 2 — runner temps réel (`report_paper.py`)

* **F1** : dès **40 décisions IA** dont les shadows sont clos : la somme des R
  shadow des signaux pris, au percentile **< 80** de 1000 tirages de même
  effectif parmi les signaux décidés (graine 20260816) → **l'IA n'ajoute
  rien. ARRÊT.**
* **F2** : dès **40 shadows clos** : R cumulé **sans coût** < 0 → le socle est
  mort aussi en prospectif — **ARRÊT** (rien à sélectionner dans un flux mort).
* **F3 (temps)** : **< 40 décisions IA après 12 mois** → **NON CONCLUSIF, on
  ferme.**
* Les courbes de compte des trois bras (MECH/AI/RND, monnaie) sont la lecture
  d'ensemble ; la mesure de vérité reste le R et le percentile de sélection.

### Invariance

**Aucun paramètre ne peut changer en cours de route.** Toute modification de
`params.json`, des bornes, du prompt du juge, des conventions d'exécution ou
des seuils ci-dessus **invalide l'essai** : redémarrage à zéro, nouveau scellé,
nouveau journal. Le hash § 1.1 rend l'événement visible ; ce paragraphe le
rend inexcusable. (Exception unique : bug démontré du moteur commun corrigé
dans `core/` — invalidation déclarée, pas contournée.)

---

## 5. Verdict — procédure

1. **Couche 1 d'abord** : `replay_measure.py` imprime les chiffres et la ligne
   de falsification atteinte. Le verdict de couche 1 est consigné dans le
   rapport de session et conditionne l'armement.
2. Si armement (décision Adrian) : la couche 2 court jusqu'à F1/F2/F3. Le
   verdict final sera un `VERDICT_PAPER.md` écrit **à l'arrêt seulement**,
   adossé ligne à ligne aux critères § 4, journal en annexe.
3. Un succès de couche 1 seul ne promeut RIEN en réel : il autorise seulement
   la couche 2. Un succès de couche 2 ouvre une **discussion** (pas une
   promotion) — décision Adrian, avec rappel du slippage non modélisé et du
   verdict mécanique § 0.

---

## 6. Armement (décision Adrian — non exécuté par le dispositif)

**Conditionné au signal de couche 1 (§ 4).** Le Planificateur de tâches
exécute `run_paper.bat` une fois par jour, après la clôture de la barre D1
(le passage est idempotent — un horaire matinal mesure la veille sans risque) :

```bat
schtasks /Create /TN "TBOT_macd_ai_paper" ^
  /TR "C:\Datas\Projects\TradingBot_9.0.0.x\studies\macd_ai_paper\run_paper.bat" ^
  /SC DAILY /ST 07:10 /F
```

Vérifier : `schtasks /Query /TN "TBOT_macd_ai_paper"`.
Désarmer : `schtasks /Delete /TN "TBOT_macd_ai_paper" /F`.

Conditions de fonctionnement : MT5 ouvert et connecté (sinon exit 2, rattrapage
au passage suivant — les barres manquées sont rejouées depuis le curseur) ;
CLI `claude` authentifié (`claude /login` — un 401 rend le bras IA N/A, les
témoins continuent). Lecture à la demande :
`python -m studies.macd_ai_paper.report_paper`.

---

## 7. Fichiers du dispositif

| Fichier | Rôle |
|---|---|
| `PROTOCOL.md` | **Ce scellé.** Ne plus modifier. |
| `params.json` | Configuration figée — hash § 1.1. Ne plus modifier. |
| `paper_step.py` | Le pas : scellé, journal chaîné, 3 bras + shadow, conventions moteur, sizing RiskLayer. |
| `ai_judge.py` | Le juge headless : prompt (partagé rejeu/runner), invocation CLI, extraction JSON, N/A propre. |
| `run_paper.py` | CLI du pas quotidien (codes de sortie en tête) + `--test-judge`. |
| `report_paper.py` | Lecture couche 2 contre les falsifications § 4. |
| `replay_common.py` | Datasets, candidats (code s12 importé), outcome indépendant aux conventions moteur. |
| `replay_extract.py` | Anonymisation motif s93 → batches + mapping (jamais montré au juge). |
| `replay_measure.py` | Mesure couche 1 contre F1-rejeu. |
| `run_paper.bat` | Enveloppe Planificateur. **Ne pas armer sans signal couche 1.** |
| `test_paper_step.py` | Idempotence (juge compris), append-only, scellé, panne CLI, gap, préséance SL/TP, tailles/clamp, RND déterministe. |

Périmètre d'écriture : `studies/macd_ai_paper/` et
`C:\db\tbot\macd_ai_paper\` uniquement. Rien dans `core/`, rien dans
`strategies/`. Aucun ordre réel, jamais.
