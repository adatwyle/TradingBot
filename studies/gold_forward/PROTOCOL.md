# PROTOCOLE — forward-test scellé du résidu or (s11 / XAUUSD H1)

> **Ce fichier est un scellé.** Il est écrit **avant** le premier signal mesuré
> et ne doit plus être modifié ensuite. Il fixe la configuration, les critères
> d'arrêt et la façon dont le verdict sera rendu. Toute conclusion future se
> lit contre ce qui est écrit ici, et nulle part ailleurs. La valeur entière de
> ce test tient à l'impossibilité de tricher rétroactivement — c'est le seul
> test que `studies/gold/VERDICT.md` § 8 déclare capable de trancher.

**Date de scellement** : 2026-08-16
**Dépôt au scellement** : commit `0a55bf9`
**Origine** : `studies/gold/VERDICT.md` — statut `NON CONCLUSIF`, recommandation
« si l'or doit être instruit plus loin, que ce soit par un forward-test scellé
≥ 100 trades avec critère d'arrêt écrit d'avance — pas par une mesure de plus
sur les mêmes 30 024 barres ». Décision de lancer ce dispositif : Adrian.

---

## 1. Ce qui est testé — et ce qui ne l'est pas

**L'hypothèse** : la configuration résiduelle de l'or, survivante de cinq
protocoles de falsification sur 2021-2026 (+0,226 R/trade, 400 trades,
percentile 99,8-100 au bras témoin), produit une espérance positive **hors de
l'échantillon qui l'a sélectionnée**. C'est la seule mesure non conditionnée à
la sélection (VERDICT § 6 : le biais de sélection des 1024 cellules n'est pas
quantifiable rétrospectivement).

**Ce test ne mesure pas** : la propriété qui expliquerait l'edge (aucune n'a
été identifiée), le transfert à d'autres instruments (0/2 à froid), ni le côté
short isolément (l'IC restera large). Il mesure UNE chose : prospectivement,
cette règle figée bat-elle, ou non, une entrée aléatoire à dispositif de
risque identique sur les mêmes barres.

---

## 2. Configuration FIGÉE

Source unique : `studies/gold_forward/params.json` — le fichier que
`run_forward.py` charge et vérifie à chaque passage.

### 2.1 Le scellé cryptographique

```
SHA-256(params.json) = 225fa9ab188450fa44883d404d797267251c6a945f23ea8c5e0e48be5583ed2f
```

Ce hash est répliqué dans la constante `PARAMS_SHA256` de `run_forward.py`.
Le script **refuse de tourner** si le fichier ne correspond plus (exit 3).
Modifier `params.json`, la constante, ou les deux, laisse une trace dans
l'historique git — c'est le but. Le test
`test_forward_step.py::test_hash_du_vrai_fichier_scelle_correspond` casse à la
moindre divergence.

### 2.2 Contenu (copie de lecture — `params.json` fait foi)

| Élément | Valeur | Provenance |
|---|---|---|
| Stratégie | `s11_legacy_breakout`, code au commit courant du dépôt | `strategies/s11_legacy_breakout/strategy.py` |
| Instrument / TF | **XAUUSD / H1** (barres MT5 Swissquote, heure serveur) | périmètre de l'étude |
| Cellule | `adx_min 20 · donchian 40 · er_min 0,00 · fr_max 1,00 · tp_m 4,0` | résidu figé, `studies/gold/HYPOTHESIS.md` § F1 |
| Paramètres fixes | `sl_m 1,5 · atr_vol_ratio 0,8 · adx_rising_lookback 5 · rsi_long_max 75 · rsi_short_min 25` | valeurs historiques s11, hors grille |
| Spread | **25 pips** (pip 0,01), payé demi-spread à chaque extrémité | catalogue `core/data/instruments.py` |
| Slippage | **0** — comme l'étude et le témoin. Assumé : les chiffres restent comparables au dossier `studies/gold/`, et sont optimistes d'un montant inconnu. Un verdict SUCCÈS devra le rappeler avant toute discussion de promotion. | catalogue |
| Exécution | moteur commun : entrée au close de la barre de signal ; stop **unilatéral** (gap payé à l'ouverture) ; cible sans faveur de gap ; SL prime sur TP dans la même barre ; position unique ; cooldown 2 barres ; circuit breaker 3 pertes → 24 barres ; `max_hold_bars` aucun | `core/backtest/engine.py`, répliqué ligne à ligne dans `forward_step.py` et vérifié par tests |

### 2.3 Sizing virtuel

1 % de risque par trade sur un capital fictif initial de **10 000**, dimensionné
par la logique de `core/risk/guards.py` (`RiskLayer.evaluate`,
`max_position_pct = 0,01`, une position par instrument). Le journal parle donc
en R **et** en monnaie. **La mesure de vérité reste le R** : la monnaie est une
lecture, le capital virtuel n'entre dans aucun critère d'arrêt.

---

## 3. LES CRITÈRES D'ARRÊT — chiffrés d'avance, c'est le cœur

Le témoin est le **bras à entrée aléatoire** de
`core/backtest/anchored_wf.py::control_arm` : 200 tirages, graine figée
20260816, même effectif, même répartition long/short, mêmes stops/cibles en
ATR, mêmes barres, même spread, mêmes contraintes de moteur
(`engine_kwargs` identiques à la stratégie). Recalculé par
`report_forward.py` **sur la fenêtre écoulée du forward** (du scellé à la
dernière barre mesurée).

### a) Arrêt-échec
Dès que **≥ 40 trades** sont clôturés : si le **R cumulé** du forward passe
**sous le percentile 20** de la distribution du témoin recalculée sur la même
fenêtre → **STOP DÉFINITIF**. Verdict : « pas d'edge confirmé en prospectif ».
Pas de deuxième chance, pas de « on attend encore un peu ».

### b) Arrêt-succès
**≥ 100 trades** clôturés **ET** percentile **≥ 95** contre le témoin →
**promotion en discussion**. La discussion — pas la promotion : la décision est
à Adrian, et devra affronter ce que ce test ne mesure pas (§ 1) plus le
slippage non modélisé (§ 2.2).

### c) Arrêt-temps
**< 40 trades clôturés après 12 mois** (soit une fréquence effondrée par
rapport aux ~78 trades/an observés) → **NON CONCLUSIF, on ferme**. Un régime
qui ne produit plus le signal n'est pas un régime où le signal se mesure.

### d) Invariance
**Aucun paramètre ne peut changer en cours de route.** Toute modification de
`params.json`, de la cellule, du spread de valorisation, des conventions
d'exécution ou des critères ci-dessus **invalide le test** : redémarrage à
zéro, nouveau scellé, nouveau journal. Le hash § 2.1 rend l'événement visible ;
ce paragraphe le rend inexcusable. (Exception unique : un bug démontré du
moteur commun corrigé dans `core/` — auquel cas l'invalidation est déclarée,
pas contournée : le test repart à zéro sur le moteur corrigé.)

**Ordre de préséance** : (a) et (b) sont évalués à chaque lecture ; si les deux
sont simultanément vrais (impossible par construction : percentile < 20 et
≥ 95 s'excluent), le dispositif est bogué et le test est invalide. (c) n'est
évalué qu'à défaut de (a)/(b).

---

## 4. Ce qui est mesuré, et comment le verdict sera rendu

**Mesuré** : chaque signal de la cellule figée sur barres H1 clôturées,
exécuté virtuellement aux conventions du moteur commun ; date/heure de barre,
sens, prix d'entrée (coût inclus), stop, cible, taille, sortie (SL/TP), R,
monnaie. Une position encore ouverte est valorisée au dernier close dans
`status.json` (lecture) mais **n'entre pas** dans le R cumulé des critères.

**Rendu** : par `report_forward.py`, qui affiche — effectif TOUJOURS en
regard — le R cumulé, le R moyen avec IC 95 %, le percentile témoin, et LA
phrase : soit « AUCUN critère d'arrêt atteint — continuer », soit le critère
atteint. Le verdict final sera un `VERDICT_FORWARD.md` écrit **à l'arrêt du
test seulement**, adossé ligne par ligne aux critères § 3, journal en annexe.

**Intégrité — trois couches** :
1. `journal.csv` est **append-only à chaîne de hachage** : chaque ligne porte
   le SHA-256 du fichier tel qu'il était avant elle. Modifier, insérer ou
   supprimer une ligne passée casse tous les maillons suivants et le pas
   suivant refuse de tourner (exit 4).
2. Chaque ligne porte **deux horodatages** : la barre (heure serveur) et la
   **mesure** (`measured_at_utc`, quand le script a tourné). Un trade mesuré
   avant sa barre, ou des mesures non monotones, sont un antidatage visible.
3. La couche externe est **git** : protocole, hash et code committés avant le
   premier signal. Un falsificateur qui réécrit journal + état + git réécrit
   l'histoire d'un dépôt — c'est détectable par les remotes et c'est hors du
   modèle de menace d'un test qu'on se fait à soi-même.

**Données et état** (jamais dans l'arborescence de code — convention projet) :

```
C:\db\tbot\gold_forward\
├── journal.csv      # append-only, chaîné — LA pièce du dossier
├── state.json       # curseur, position ouverte, capital, empreinte journal
├── status.json      # dernière lecture (effectifs, R, distance aux critères)
└── run.log          # sorties des passages planifiés
```

---

## 5. Le pas de mesure

`run_forward.py` est **idempotent** : exécutable chaque heure ou chaque jour,
sans effet si aucune barre nouvelle. À chaque passage : vérification du scellé
(hash) et de la chaîne du journal **avant toute écriture** ; chargement des
barres fraîches (`core.data.source.load_bars`, cache ≤ 1 h) ; retrait de la
barre en formation ; recalcul des signaux avec les paramètres scellés (même
code que le backtest — R5, pas de deuxième implémentation) ; consommation des
seules barres postérieures au curseur ; suivi des positions ouvertes ; append
au journal ; réécriture de `status.json`.

MT5 indisponible → exit 2, message dans `run.log`, journal intact, nouvel
essai au passage suivant. Les trous de mesure sont sans effet : les barres
manquées sont rejouées au passage suivant à partir du curseur (les signaux
sont recalculés sur l'historique complet, l'exécution virtuelle est
déterministe sur barres closes).

**Premier passage** : pose du scellé. Le curseur est placé sur la dernière
barre close ; **aucun signal historique n'entre au journal**. Aucun trade au
premier passage est le comportement attendu.

**Note de lisibilité assumée** : la fenêtre de barres MT5 est glissante
(~5 ans) ; l'ADX (EMA) a une mémoire théoriquement infinie, donc deux
fenêtres décalées peuvent différer d'un epsilon sur les indicateurs. Avec
400 barres de warmup et des signaux pris à des milliers de barres du bord,
l'effet est négligeable — et seuls les signaux **postérieurs au curseur** sont
jamais consommés : le journal passé ne peut pas être réécrit par ce mécanisme.

---

## 6. Armement (décision Adrian — non exécuté par le dispositif)

Le Planificateur de tâches Windows exécute `run_forward.bat` chaque heure.
**Commande à exécuter par Adrian, et par lui seul** (invite de commandes) :

```bat
schtasks /Create /TN "TBOT_gold_forward" ^
  /TR "C:\Datas\Projects\TradingBot_9.0.0.x\studies\gold_forward\run_forward.bat" ^
  /SC HOURLY /MO 1 /ST 00:07 /F
```

Vérifier : `schtasks /Query /TN "TBOT_gold_forward"`.
Désarmer (à l'arrêt du test) : `schtasks /Delete /TN "TBOT_gold_forward" /F`.

Le décalage :07 évite de mesurer pile à la clôture de barre (barre en
formation retirée de toute façon). MT5 doit être ouvert et connecté sur le
poste pour que le passage voie des barres fraîches ; sinon le passage log
« MT5 indisponible » et réessaie l'heure suivante — sans conséquence autre
qu'un retard de mesure.

La lecture se fait à la demande : `python -m studies.gold_forward.report_forward`.

---

## 7. Fichiers du dispositif

| Fichier | Rôle |
|---|---|
| `PROTOCOL.md` | **Ce scellé.** Ne plus modifier. |
| `params.json` | Configuration figée — hash § 2.1. Ne plus modifier. |
| `forward_step.py` | Logique du pas : scellé, journal chaîné, exécution aux conventions moteur, sizing `RiskLayer`. |
| `run_forward.py` | CLI du pas de mesure (codes de sortie documentés en tête). |
| `report_forward.py` | Lecture contre les critères § 3, témoin recalculé. |
| `run_forward.bat` | Enveloppe pour le Planificateur de tâches. |
| `test_forward_step.py` | Idempotence, append-only, refus sur hash, gap payé, préséance SL/TP, cooldown, cohérence R/monnaie. |

Périmètre d'écriture : `studies/gold_forward/` et `C:\db\tbot\gold_forward\`
uniquement. Rien dans `core/`, rien dans `strategies/`.
