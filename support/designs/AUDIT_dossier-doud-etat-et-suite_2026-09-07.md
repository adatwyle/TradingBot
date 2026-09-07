---
name: audit-dossier-doud-etat-et-suite
date: 2026-09-07
type: AUDIT
target_scope: projet
applies_to: [strategies/S018_gold_doud_v2, strategies/S019_gold_sweep, studies/meteo_doud, studies/gold_forward, tickets/TCK-014, tickets/TCK-018]
auteur: cc-support
---

# Dossier Doud — état vérifié et suite à donner

Audit croisé du 2026-09-07 : quatre lectures indépendantes du dépôt, quatre feuilles de
route sous angles distincts, trois critiques adversariales. Toute affirmation reprise
ci-dessous a été **revérifiée à la main** avant d'être écrite : les agents se trompent,
et trois de leurs constats les plus graves se sont avérés exacts.

---

## 1. Trois corrections à ce qui avait été rapporté

### 1.1 Le coût de bord était sous-estimé une deuxième fois

Le catalogue déclare 25 pips. TCK-018 avait mesuré 52 et je l'ai employé partout. **52
était la médiane sur tout l'historique** ; le régime courant est ailleurs :

| Année | 2021 | 2022 | 2023 | 2024 | 2025 | **2026** |
|---|---|---|---|---|---|---|
| Spread médian (pips, M15) | 50 | 51 | 54 | 55 | 65 | **90,8** |

Source : colonne `spread` de `C:/db/tradingBot/bars_cache/XAUUSD_*.pkl`, exprimée en
points (0,001) ; médiane sur 365 jours = p90 = 908 points = 90,8 pips, identique en M1,
M5, M15 et H1.

Conséquence sur S019 : le coût annoncé à 14,3 % du R vaut en réalité **25 % en M15**
(90,8 / 363) et **44 % en M5** (90,8 / 207). Le seuil d'échec écrit d'avance dans
`FALSIFICATION.md` était 35 % : la maille M5 le franchit. **La réfutation de S019 en
sort renforcée**, mais le chiffre publié était faux.

Conséquence sur la v1 : les risques du forward valent 2 400 à 2 750 pips (journal
`C:/db/tradingBot/gold_forward/journal.csv`), donc l'écart 25 → 90,8 pips pèse ≈ 2,8 %
du R par trade. Réel, mais mineur — et il joue contre nous, jamais pour.

### 1.2 La mesure fondatrice du dossier est contaminée, de trois façons

Le « 60 % de ses entrées suivent un balayage contre 39 % au hasard, p = 0,047 » a servi
de justification à S019. Il souffre de trois défauts, tous vérifiés :

**a) Le test est unilatéral.** `croisement_entrees.py:65-88` ne détecte qu'un balayage
**haussier** (`lo[j] < ref and cl[j] > ref` — un plus-bas percé puis récupéré), c'est-à-dire
une configuration d'**achat**. `forward()` (lignes 91-97) calcule `mfe = high - entry` et
`mae = entry - low`, soit le P&L d'une position **longue**.

**b) Le sens de ses entrées n'est jamais établi.** Sur 32 observations, 28 n'ont aucune
indication de sens ; les 4 qui en ont disent toutes **vente**. Le rapport MFE/MAE de 1,80,
qui a justifié « 60 % atteignent 1,5 ATR en sa faveur » et « notre stop métrique couperait
40 % de ses entrées », a donc mesuré du P&L long sur des trades possiblement vendeurs.

**c) L'horodatage est celui de la parole, pas de l'entrée.** Les 20 observations alignées
proviennent de 13 vidéos seulement et comportent **2 paires de doublons exacts**
(`g0QZlUtQLvM` prix 333548 à 13 s d'intervalle ; `pO6DkqBIUFE` prix 4063 à 274 s). Le
champ `ctx` montre qu'elle commente fréquemment une position **déjà ouverte** — « je suis
déjà dedans, je suis rentré au 333548 », « je viens de clôturer », « j'y suis ». Le
balayage est cherché dans les 30 barres M1 précédant la **parole** ; si elle parle d'un
trade qui a déjà bougé en sa faveur, un balayage antérieur devient mécaniquement plus
probable. Le confondant travaille dans le sens du résultat obtenu.

Ce qui ne change pas : **S019 mesurait une règle directement sur cinq ans de barres**,
indépendamment du corpus. Sa réfutation tient. Ce qui change, c'est la raison pour
laquelle cette règle avait été choisie.

### 1.3 TCK-014, tel que recommandé, met en danger le forward scellé

Le scellé n'est pas isolé du code vivant. Deux couplages vérifiés :

- `studies/gold_forward/run_forward.py:43` importe `strategies.S011_legacy_breakout.strategy`.
  **Le code de la stratégie n'est pas haché** — seul `params.json` l'est.
- `studies/gold_forward/report_forward.py:44` importe `control_arm` depuis
  `core.backtest.anchored_wf` et l'appelle ligne 174 **à chaque lecture**. Les critères
  d'arrêt du `PROTOCOL.md` § 3 sont des **percentiles contre ce témoin**.

Donc toute modification de `core/backtest/engine.py` — ce qu'exige TCK-014 — déplace les
critères d'arrêt d'un test scellé qui tourne depuis le 14 août.

Et le garde-fou de production ne le verrait pas : `app/orchestrator/tbot-prod-watcher.py:212`
lance `pytest app -q`, quand `.github/workflows/ci.yml:71` lance
`pytest app strategies studies`. Le test d'intégrité du scellé
(`studies/gold_forward/test_forward_step.py`) ne garde donc pas le rollback de prod.

---

## 2. La mesure qui tranche sur TCK-014 — et qui coûte quatre minutes

Question : une sortie plus fine (partielles, suiveur) peut-elle extraire un avantage d'un
déclencheur mesuré neutre ? Réponse par la **loi de chemin** des 5 138 trades S019, sans
toucher une ligne de moteur.

Pour une marche **sans dérive**, la probabilité d'atteindre +b avant −1 R en partant de
+a vaut `(a+1)/(b+1)`. Observé contre théorie :

| Depuis | Atteint avant SL | Observé P(suite) | Martingale |
|---|---:|---:|---:|
| +0,5 R | 61,8 % | — | 66,7 % |
| +1,0 R | 47,6 % | 77,1 % | 75,0 % |
| +1,5 R | 39,4 % | 82,8 % | 80,0 % |
| +2,0 R | 33,0 % | 83,7 % | 83,3 % |
| +3,0 R | 24,3 % | 73,7 % | 75,0 % |
| +4,0 R | 19,3 % | 79,2 % | 80,0 % |

Les écarts sont de −1,3 à +2,8 points, sans direction systématique, et ils sont calculés
**hors spread** — donc optimistes. Le chemin de prix après une entrée S019 est
indiscernable d'une marche aléatoire.

**Conséquence** : par le théorème d'arrêt optionnel, toute stratégie d'arrêt sur une
martingale a la même espérance. Clôtures partielles, stop suiveur, break-even — aucune ne
peut créer d'avantage ici. **TCK-014 ne sauvera pas S019.**

Ce que cela ne dit pas : TCK-014 reste une dette de plateforme légitime (le trailing de
S011 n'a jamais été reproductible, cf. `S011/research/ANALYSIS.md` § 4). Mais ce n'est
plus le chemin critique du dossier or, et cela ne justifie plus de toucher `core/` en
urgence — donc plus de risquer le scellé.

---

## 3. Réponses aux cinq questions

| Question | Réponse |
|---|---|
| **Prête pour le paper trading ?** | Non pour S018 (`NON RETENU`) et S019 (réfuté). La v1 est déjà en forward scellé : 7 trades sur 100, +3,92 R, verdict attendu ~juin 2027. L'infrastructure paper tourne (4 études pas-à-pas quotidiennes) — le frein n'est pas technique. |
| **Entrée reconstituée ?** | Décrite entièrement (géométrie complète : zones fatidiques → têtes de mort → sabre laser → zone blanche → zone jaune → zone de retournement). Mesurée neutre. Son **filtre de sélection** reste inconnu, et la mesure qui fondait tout est contaminée (§ 1.2). |
| **Météo reconstruite ?** | Non. Instrument prêt (`score_meteo.py`, témoin par miroir symétrique), matière absente : 6 prévisions, **toutes haussières**, tirées de clips où elle annonce ses réussites, pendant une hausse de 77 %. Le script documente lui-même le biais de publication comme total. Aucun couplage à une stratégie. |
| **Testée ?** | Oui, lourdement : S018 (32 cellules × 3 mailles), S019 (16 × 2 mailles, 120 k puis 359 k barres), R1 et R5 passés partout, bras témoin systématique, falsification écrite avant chaque campagne. Étalon jamais battu : **v1 = 402 trades, +0,236 R/trade, percentile 100,0**. |
| **Suite ?** | § 4. |

---

## 4. Suite — ordonnée par rapport coût/information, la moins chère d'abord

Le principe qui ordonne cette liste : **rien qui touche `core/` tant que le scellé n'est
pas protégé, et rien de cher tant qu'un calcul gratuit peut trancher.**

### P0 — gratuit ou presque, et ça ferme des portes

1. **Corriger le coût de bord au régime courant** *(cc-spec puis cc-app, TCK-018)*.
   Porter les médianes annuelles au catalogue `app/core/data/instruments.py`. Critère :
   toute mesure or postérieure valorise à ≥ 90 pips, et les dossiers déjà rendus portent
   la mention « spread catalogue, optimiste ».
   *Bénéfice : tout le projet, pas seulement l'or.*

2. **Établir le sens des 20 entrées, purger les doublons, rejouer en bilatéral**
   *(cc-support)*. 20 timecodes à réécouter, pas 35 lives. Règle de purge écrite **avant**
   la relecture. Puis `croisement_entrees.py` rendu symétrique (balayage baissier + MFE/MAE
   selon le sens), même graine, même témoin 200 tirages, falsification écrite d'avance.
   Critère : le 60/39 est confirmé, corrigé ou tombe — les trois issues sont acceptables,
   aucune n'est cherchée.

3. **Dépouiller les mesures orphelines de S018** *(cc-S018)*. `results_M15.json` et
   `results_M5.json` existent depuis le 2026-09-06 et n'ont jamais été lues ; le § 6 du
   VERDICT affirme « nous mesurons en H1 », ce qui est devenu faux. **Addendum daté, jamais
   réécriture en place.** Coût : 20 minutes.

4. **Réparer le garde-fou de production** *(cc-app)*. `tbot-prod-watcher.py:212` doit
   lancer le même périmètre que la CI (`app strategies studies`), sinon le test
   d'intégrité du scellé ne garde pas le rollback. Deux lignes, risque nul, dette
   découverte ici.

### P1 — décision d'Adrian, éclairée par P0

5. **Arbitrage, trois branches écrites** *(Adrian)*.
   (a) Si le 60/39 tombe en bilatéral → le volet Doud se clôt sur un verdict honnête, et
   on a appris beaucoup sur la méthode de mesure.
   (b) S'il tient → une hypothèse d'entrée reste à formuler, mais avec la puissance
   statistique calculée d'avance (à n = 20, détecter 60 % contre 39 % a une puissance de
   0,25 — c'est le vrai obstacle, pas le manque d'idées).
   (c) Dans les deux cas, TCK-014 redevient une dette de plateforme normale, hors chemin
   critique de l'or.

### P2 — seulement si Adrian veut TCK-014 pour la plateforme

6. **Oracle de non-régression AVANT toute ligne de moteur** *(cc-app)*. Référence figée
   trade par trade (entrée, sortie, raison, R) du moteur actuel sur barres réelles, pour
   S011 et les stratégies en vol. `studies/verify-journal.py` **ne convient pas** : il
   vérifie une chaîne de hachage, il ne rejoue aucun trade.

7. **Note de couplage du scellé** *(cc-support)*. Fichier **neuf**
   `studies/gold_forward/NOTE_couplage-core_2026-09-07.md` — jamais le `PROTOCOL.md`, qui
   se déclare non amendable. Il recense les deux imports vers le code vivant et énonce la
   règle : toute modification de `core/backtest/` déclare l'invalidation du forward
   plutôt que de la contourner (PROTOCOL § 3d, exception « bug démontré du moteur »).

8. **TCK-014 spécifié et implémenté** *(cc-spec puis cc-app)*, avec un périmètre élargi de
   deux obligations que les quatre feuilles de route avaient omises : étendre
   `_reference_profile` et `_random_signals` (`anchored_wf.py:236-355`) pour que le bras
   témoin sache rejouer un plan de sortie, et étendre la conformance R5 en conséquence.
   Sans cela, on comparerait une stratégie à sorties multiples contre un témoin à cible
   unique.

### Ce qui est explicitement écarté

- **Remesurer S019 avec une meilleure sortie** — réfuté par la loi de chemin (§ 2).
- **Une stratégie S020 « sortie seule »** — même raison, et son critère d'acceptation
  (« tout R positif est imputable à la sortie ») est précisément ce qui la rend
  infalsifiable sur un chemin martingale.
- **Les zones fatidiques comme filtre d'entrée sur l'or** — 100 % des niveaux au-dessus
  du prix ont moins d'un an (mesuré le 2026-09-07), et elle-même dit être aveugle sur
  territoire vierge.
- **Viser 40 observations d'entrée** — 32 candidats existent au total, 20 alignés, 13
  vidéos. Un critère inatteignable n'est pas un critère.
- **Écrire `docs/PROMOTION_POLICY.md` maintenant** — le rédiger en connaissant les cinq
  jeux de résultats auxquels il s'appliquera est un calibrage de seuil a posteriori.

---

## 5. Ce que ce dossier a produit, en une ligne

Aucune amélioration de la v1 — et **quatre portes fermées avec preuve** : la cassure sur
les corps, la sortie au temps, le balayage comme règle, et la sortie fine comme sauvetage.
Plus trois défauts de mesure découverts chez nous (spread périmé, test unilatéral,
garde-fou de prod incomplet) qui valent pour tout le projet. Le seul objet vivant sur l'or
reste la v1, et son forward scellé continue.
