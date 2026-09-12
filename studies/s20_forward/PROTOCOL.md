# PROTOCOLE — forward-test scellé S020 (MACD cross + filtre zéro, René Balke) / EURUSD H1

> **Ce fichier est un scellé.** Il est écrit **avant** le premier signal mesuré et ne
> doit plus être modifié ensuite. Il fixe la configuration, les critères d'arrêt et la
> façon dont le verdict sera rendu. Toute conclusion future se lit contre ce qui est
> écrit ici, et nulle part ailleurs.

**Date de scellement** : 2026-09-12 12:49:50 UTC
**Dépôt au scellement** : commit `26a81f0`
**Barre de scellé** : 2026-09-09 23:00 (heure serveur) — dernière barre H1 close du
cache au moment de la pose ; MT5 hors ligne ce jour-là (fabrique arrêtée depuis le
reboot du 10.09). **Tout ce qui précède cette barre est de l'histoire ; tout ce qui la
suit sera mesuré**, y compris les barres écoulées entre la pose et le retour de MT5 —
le journal porte l'horodatage de mesure à côté de l'horodatage de barre, le décalage
est visible, jamais caché.
**Origine** : `strategies/S020_balke_macd_cross/research/VERDICT.md` — réussite au
sens des critères de `FALSIFICATION.md` sur EURUSD H1 ; étape suivante prévue : forward
scellé. **Décision de lancer : Adrian, 2026-09-12** (« GO forward scellé EURUSD »).

---

## 1. Ce qui est testé — et ce qui ne l'est pas

**L'hypothèse** : la cellule retenue — croisement MACD(12,26,9)/signal, achat seulement
si la MACD est sous zéro, vente seulement si elle est au-dessus, stop à 1 % du prix
d'entrée, cible à 2 % — produit sur EURUSD H1 une espérance positive **hors de
l'échantillon qui l'a sélectionnée** (2021-08 → 2026-09 : +0,155 R/trade sur 129 trades,
percentile témoin 98, cinq années positives sur six).

**Deux bras, un seul comptable** :
- **EURUSD — PRINCIPAL** : seul bras lu par les critères d'arrêt.
- **USDJPY — OBSERVATION** : même cellule, journalisé à l'identique, jamais compté dans
  le verdict. Il teste l'hypothèse de transfert (USDJPY était le second instrument
  positif de la mesure : +17,8 R plein échantillon, mais **0 cellule STRICT**).

**Ce test ne mesure pas** : la démo de l'auteur (indices en intraday — non mesurés
faute de MT5 ; conclusion ouverte), le transfert à GBPUSD (négatif en mesure), ni les
pistes d'auto-amélioration de la stratégie (à instruire à part, jamais en modifiant ce
scellé). Il mesure UNE chose : prospectivement, cette règle figée bat-elle, ou non, une
entrée aléatoire à dispositif de risque identique sur les mêmes barres.

---

## 2. Configuration FIGÉE

Source unique : `studies/s20_forward/params.json`, chargé et vérifié à chaque passage.

### 2.1 Le scellé cryptographique

```
SHA-256(params.json) = 5fd385aae7af0ad59b98bd44e44bbcc8b458624fc7f2998f5d26302843419290
```

Répliqué dans la constante `PARAMS_SHA256` de `run_forward.py`. Le script **refuse de
tourner** si le fichier ne correspond plus (exit 3). Le test
`test_forward_step.py::test_hash_du_vrai_fichier_scelle_correspond` casse à la moindre
divergence.

### 2.2 Contenu (copie de lecture — `params.json` fait foi)

| Élément | Valeur | Provenance |
|---|---|---|
| Stratégie | `S020_balke_macd_cross`, code au commit courant | `strategies/S020_balke_macd_cross/strategy.py` |
| Instruments / TF | **EURUSD (principal), USDJPY (observation) / H1** | VERDICT S020 |
| Cellule | `zero_filter true · sl_pct 0,01 · tp_pct 0,02 · side_mode both` | cellule retenue, VERDICT § 2 |
| Spread | EURUSD **1,9 pips**, USDJPY **2,8 pips** (catalogue ; mesuré 1,8 / 1,9 — pas de sous-estimation) | `core/data/instruments.py` |
| Slippage | **0** — comme la mesure et le témoin. Optimiste d'un montant inconnu ; un verdict SUCCÈS devra le rappeler avant toute discussion de promotion. | convention dépôt |
| Exécution | moteur commun : entrée au close de la barre de signal ; stop unilatéral (gap payé à l'ouverture) ; cible sans faveur de gap ; SL prime sur TP ; **position unique ; refroidissement 2 barres ; coupe-circuit 3 pertes → 24 barres** (règles communes contre les pertes consécutives) | `core/backtest/engine.py`, répliqué dans `forward_step.py` et testé |
| Sizing virtuel | 1 % de risque par trade sur 10 000 fictifs, par `core/risk/guards.py` | convention dépôt |

**Pourquoi le circuit breaker ici alors que s13 l'avait désarmé** : S020 a été
*mesurée* avec ces engine_kwargs (`backtests/run_wf.py`). Le forward rejoue la mesure ;
changer les règles d'exécution entre la mesure et le forward reviendrait à tester
autre chose.

### 2.3 Rappel sur la position

Le journal parle en R **et** en monnaie. **La mesure de vérité reste le R** : la monnaie
est une lecture, le capital virtuel n'entre dans aucun critère d'arrêt.

---

## 3. LES CRITÈRES D'ARRÊT — chiffrés d'avance, c'est le cœur

Témoin : **bras à entrée aléatoire** de `core/backtest/anchored_wf.py::control_arm` —
200 tirages, graine figée 20260912, même effectif, même répartition long/short, mêmes
stops/cibles, mêmes barres, même spread, mêmes engine_kwargs. Recalculé par
`report_forward.py` **sur la fenêtre écoulée du forward**, bras principal uniquement.

**Les seuils sont adaptés à la fréquence mesurée de la règle** — ≈ 25 trades par an sur
EURUSD (129 en cinq ans). Reprendre les 40/100 de `gold_forward` (≈ 78 trades/an)
aurait mis le verdict à quatre ans. Le prix d'une règle lente est un effectif plus
faible ; le témoin, qui compare à effectif égal, reste l'argument.

### a) Arrêt-échec
Dès que **≥ 30 trades** sont clôturés sur EURUSD : si le **R cumulé** passe **sous le
percentile 20** de la distribution du témoin recalculée sur la même fenêtre → **STOP
DÉFINITIF**. Verdict : « pas d'edge confirmé en prospectif ». Pas de deuxième chance.

### b) Arrêt-succès
**≥ 60 trades** clôturés sur EURUSD **ET** percentile **≥ 95** contre le témoin →
**promotion en discussion**. La discussion — pas la promotion : décision Adrian, qui
devra affronter ce que ce test ne mesure pas (§ 1) plus le slippage non modélisé.

### c) Arrêt-temps
**< 30 trades clôturés après 18 mois** → **NON CONCLUSIF, on ferme**. Un régime qui ne
produit plus le signal n'est pas un régime où le signal se mesure. Horizon maximal du
dispositif : 48 mois (`stop_rules.horizon`).

### d) Invariance
**Aucun paramètre ne peut changer en cours de route.** Toute modification de
`params.json`, de la cellule, du spread de valorisation, des conventions d'exécution ou
des critères ci-dessus **invalide le test** : redémarrage à zéro, nouveau scellé, nouveau
journal. Exception unique : un bug démontré du moteur commun corrigé dans `core/` —
auquel cas l'invalidation est **déclarée**, pas contournée.

**Couplage au code vivant, dit ici pour ne pas être découvert plus tard** : ce runner
importe `strategies.S020_balke_macd_cross.strategy` (code non haché — seul
`params.json` l'est) et `report_forward.py` recalcule le témoin via
`core.backtest.anchored_wf`. Toute modification de l'un ou de l'autre pendant le forward
relève du critère d) et doit être déclarée (cf. TCK-014 § oracle de non-régression).

**Ordre de préséance** : a) et b) évalués à chaque lecture (mutuellement exclusifs par
construction) ; c) seulement à défaut de a)/b).

---

## 4. Ce qui est mesuré, et comment le verdict sera rendu

**Mesuré** : chaque signal de la cellule figée sur barres H1 clôturées, exécuté
virtuellement aux conventions du moteur commun ; date/heure de barre, bras, sens, prix
d'entrée (coût inclus), stop, cible, taille, sortie (SL/TP), R, monnaie. Une position
encore ouverte est valorisée au dernier close dans `status.json` mais **n'entre pas**
dans le R cumulé des critères.

**Rendu** : `report_forward.py` — effectif TOUJOURS en regard — R cumulé, R moyen avec
IC 95 %, percentile témoin, et LA phrase : « AUCUN critère d'arrêt atteint — continuer »
ou le critère atteint. Le verdict final sera un `VERDICT_FORWARD.md` écrit **à l'arrêt
du test seulement**, adossé ligne par ligne aux critères § 3, journal en annexe.

**Intégrité — trois couches** :
1. `journal.csv` append-only à chaîne de hachage (chaque ligne porte le SHA-256 du
   fichier avant elle) ; le pas suivant refuse de tourner si un maillon casse (exit 4).
2. Deux horodatages par ligne : la barre (heure serveur) et la mesure (`measured_at_utc`).
3. Le dépôt git : `params.json`, ce protocole et le hash sont commités avant le premier
   signal mesuré.

**Exploitation** : worker `s20_forward` de la tBot factory, tick 3600 s, panneau
`C:/db/tradingBot/tbot-panel.txt`. Codes de sortie : 0 passage, 2 données
indisponibles (MT5), 3 scellé violé, 4 journal altéré.
