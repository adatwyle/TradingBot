# s15 — Conditions de falsification, figées AVANT le premier backtest

> **Date de gel : 2026-08-19.** Aucun backtest de cette stratégie n'a été
> exécuté au moment où ce fichier est écrit. Aucune mesure, d'aucune sorte,
> n'a été produite — pas même une statistique de données. Toute modification
> de ce fichier après le premier run serait une falsification au sens inverse
> du terme. **Le commit de gel précède tout run.**

Le cadrage, la littérature de référence et les réserves du collecteur sont dans
`research/ANALYSIS.md`, gelé au même commit. L'attente a priori y est déclarée :
**edge faible ou nul**, et un résultat positif se traite avec suspicion.

---

## 1. Convention statistique

La référence du dossier est le **bras témoin empirique** (`control_arm` /
`attach_control_arm` de `core/backtest/anchored_wf.py`, 200 tirages, graine
**20260819**), exécuté avec les MÊMES `engine_kwargs` que la stratégie. Le
comptage STRICT / n×0,05 est rapporté pour archive, jamais comme évidence.

`engine_kwargs` figés, identiques stratégie et témoin :
`max_positions=1, cooldown_bars=0, cb_losses=999` — on mesure le SIGNAL ; le
circuit breaker est un habillage de production qui masquerait la mesure.
`max_hold_bars` dépend de la sortie (5 pour `hold5`, 25 pour `atr_2_2`) et est
appliqué à la stratégie ET au témoin.

**Coûts** : spread catalogue (`core/data/instruments.py` — EURUSD 1,9 pips
avec pip = 0,0001 ; XAUUSD 25,0 pips avec pip = 0,01, soit 0,25 USD) plus
**0,5 pip de slippage à chaque bout**. Tout chiffre annoncé « réel » les paye ;
tout chiffre annoncé « brut » l'indique explicitement.

La recherche est LARGE relativement à la donnée (128 cellules, §4) et la donnée
est hebdomadaire (§3). Les deux protections principales sont le **hold-out
scellé** (§2) et le **contrôle de fuite** (§5) — la seconde étant un préalable
absolu à la lecture de la première.

---

## 2. HOLD-OUT SCELLÉ — déclaré avant tout chiffre

- **Coupe des données** : toute barre D1 datée **≥ 2026-08-15** est écartée
  (semaine en cours incomplète). Dernière semaine complète : lundi 2026-08-10 →
  vendredi 2026-08-14.
- **Scellé** : toute barre D1 datée **≥ 2021-08-16** (un lundi) est EXCLUE de
  toute exploration, toute grille, tout témoin, toute sélection. Aucun script
  d'exploration ne les charge. Durée : **5 ans, ≈ 261 semaines**.
- **Exploration** : début du cache (≈ 2006-08) → **2021-08-13** (vendredi),
  soit ≈ **782 semaines**.
- **Ouverture** : UNE seule fois, sur **≤ 3 candidates** sélectionnées par la
  règle du §7. Aucun retour en arrière : un échec au hold-out est un échec
  définitif de la candidate — pas une invitation à en choisir une quatrième.
  La liste des candidates est **close et écrite au VERDICT AVANT** l'ouverture.

### 2.1 Pourquoi 5 ans et non 18 mois (l'écart avec s13, assumé)

s13 scelle 18 mois. Ce dimensionnement est calibré pour un signal **quotidien** :
466 barres = 466 occasions de décision. Ici la décision est **hebdomadaire**
(§3 de `ANALYSIS.md`). 18 mois = 78 occasions, dont ~16 seulement dans l'état
au seuil primaire, agglutinées en 3 à 5 épisodes indépendants — un hold-out
**sans pouvoir de trancher**, qui rendrait NON CONCLUSIF par construction, donc
un hold-out inutile.

**Un scellé se dimensionne en occasions de décision, pas en jours calendaires.**
5 ans (≈ 261 semaines) est la plus petite fenêtre qui laisse au hold-out une
chance de dire quelque chose (§6, dérivation du seuil d'épisodes), tout en
laissant ≈ 782 semaines à l'exploration. C'est le facteur limitant du dossier :
l'historique de prix D1 plafonne à ~20 ans, quelle que soit la profondeur de la
série COT.

### 2.2 Ce que contient le scellé — déclaré d'avance

2021-2026 couvre le cycle de resserrement 2022, le dollar fort, le marché
haussier de l'or 2023-2026, **et la suspension de publication du COT de 2025**
(30 septembre → 29 décembre, `GEL_2025`). Le scellé contient donc le pire cas
opérationnel. C'est voulu : un hold-out qui ne contiendrait qu'un régime ne
vaudrait rien.

---

## 3. Contrainte de fréquence — la chaîne des effectifs

Arithmétique **a priori** (semaines × paramètres déclarés), **pas une mesure** :
les effectifs réels seront rapportés au VERDICT.

| Étage | Ordre de grandeur | Pourquoi il rétrécit |
|---|---|---|
| Observations COT brutes (or, série Legacy) | ≈ 1 900 | 1986 → 2026 |
| Semaines utilisables (alignées sur les prix) | ≈ 1 043 | l'historique D1 plafonne à ~20 ans |
| Semaines d'exploration | ≈ 782 | hold-out scellé retiré |
| Semaines DANS L'ÉTAT, seuil primaire q = 0,20 | ≈ 156 | une semaine sur cinq dans la queue |
| **Épisodes INDÉPENDANTS** | **≈ 35-45** | le positionnement est fortement autocorrélé : les semaines extrêmes arrivent en grappes |

**C'est la dernière ligne qui compte.** 156 trades issus de 5 épisodes de
positionnement, ce sont 5 observations, pas 156. Toute métrique du dossier est
rapportée avec **ses deux effectifs** : nombre de trades ET nombre d'épisodes.

### 3.1 Définition figée d'un ÉPISODE

Pour un couple (instrument, famille, `lookback`, `q`, état) donné :

> Un **épisode** est une suite maximale de semaines dans l'état. Deux entrées
> appartiennent à des épisodes distincts si et seulement si elles sont
> séparées par **au moins 4 semaines consécutives HORS de l'état**.

**Pourquoi 4 semaines** : la série de positionnement varie lentement d'une
semaine à l'autre ; un mois complet passé hors de la queue est la séparation
minimale à partir de laquelle deux franchissements peuvent être traités comme
deux événements et non comme un seul qui oscille autour de son seuil. Valeur
déclarée a priori, jamais ajustée sur les résultats.

---

## 4. Grille — figée, par instrument

Constantes hors grille : ATR 14 sur D1, warmup 60 barres, entrée au close de la
barre de décision, stop TOUJOURS renseigné (R3), **une entrée autorisée
uniquement sur la première barre D1 de la semaine**.

Le percentile est calculé causalement sur les `lookback` dernières observations
**publiées** (`cot.connu_au()`), valeur courante incluse. La fenêtre est prise
sur la série COT, plus profonde que les prix — aucun signal n'est perdu au
démarrage de l'exploration.

| Famille | État | Paramètres | Cellules / instrument |
|---|---|---|---|
| **A `niveau`** | percentile de `pct_noncomm` | `lookback` ∈ {104, 260} × `q` ∈ {0,10, **0,20**} × état ∈ {bas, haut} × sens ∈ {long, short} × sortie ∈ {`hold5`, `atr_2_2`} | 32 |
| **B `impulsion`** | percentile de Δ`pct_noncomm` (1 semaine) | idem | 32 |
| **C `suiveur`** | — | **0 cellule** : c'est la lecture (état, sens opposé) des cellules ci-dessus, produite par le même run | 0 |

**Total : 64 × 2 instruments = 128 cellules.**
Jeux de dates d'entrée **distincts** : 2 `lookback` × 2 `q` × 2 états × 2
familles × 2 instruments = **32**. Les dimensions `sens` et `sortie` ne créent
aucune date nouvelle.

### 4.1 Seuil primaire désigné d'avance : `q = 0,20`

`q = 0,20` est le seuil **primaire** ; `q = 0,10` est une **sonde de
profondeur** (au sens de la sonde dose-réponse de s90), pas une candidate de
repli. **Pourquoi 0,20 en primaire** : c'est le plus petit seuil qui laisse à
l'exploration ET au hold-out assez d'épisodes indépendants pour que le §6 soit
franchissable (§3). Un protocole dont le seuil primaire ne peut pas passer son
propre critère d'effectif ne teste rien.

`lookback = 260` (5 ans) est le lookback **primaire** ; `lookback = 104` (2 ans)
est son voisin de robustesse. **Pourquoi 260** : c'est la fenêtre la plus longue
qui reste locale au regard de la reclassification des catégories de traders
(`ANALYSIS.md` §9.3), donc le meilleur compromis entre stabilité de la
distribution de référence et immunité à la dérive de définition.

### 4.2 Attente sous H0, déclarée

128 cellules × 0,05 ≈ **6 à 7 « réussites » attendues par pur hasard** sous la
convention de commodité. Les cellules sont de plus fortement corrélées (mêmes
dates d'entrée sous deux sens et deux sorties). Le juge n'est donc jamais un
compte de cellules vertes : c'est le témoin mesuré (F2), la stabilité de graine
(F3), le voisinage (F5) et le hold-out scellé (F9).

---

## 5. F0 — LE CONTRÔLE DE FUITE (test du DISPOSITIF, pas de l'hypothèse)

> **F0 est un GATE, pas un falsifieur parmi d'autres.** Tant qu'elle n'est pas
> passée, **aucun chiffre de F1 à F9 ne peut être lu**, et **aucun verdict ne
> peut être rendu** — ni positif, ni négatif. Une mesure honnête produite par
> un dispositif dont on n'a pas prouvé qu'il mesure quelque chose ne vaut rien.

Toute mesure du dossier est produite en **trois** versions (`ANALYSIS.md` §5.3) :
**HONNÊTE** (lundi, via `connu_au()`), **FUITÉE-3J** (la ligne du mardi lue dès
le mardi) et **FUITÉE-CONTEMPORAINE** (le snapshot du mardi *t* lu dès le
mercredi *t−6*, horizon 5 barres — l'alignement synchrone exact de la
littérature).

### 5.1 F0.1 — assertions dures, structurelles (vrai ou faux, pas statistique)

| # | Assertion | Portée |
|---|---|---|
| **F0.1a** | Pour CHAQUE trade de la version honnête : `date_barre_entrée >= publication(snapshot_utilisé) + 3 jours` | une seule violation → **ARRÊT**, réparation, tout run antérieur jeté |
| **F0.1b** | Pour CHAQUE trade de la version honnête : la barre d'entrée est la **première barre D1 de sa semaine ISO** | idem |
| **F0.1c** | Le recouvrement entre l'ensemble des dates d'entrée HONNÊTE et celui de FUITÉE-CONTEMPORAINE est **exactement 0 %** | un recouvrement non nul prouve que les deux chaînes ne sont pas distinctes → **ARRÊT** |
| **F0.1d** | R1 (`core.validation.causality`) passé et archivé | R1 porte sur les barres ; F0.1a-c portent sur la donnée exogène. Les deux sont requis, aucun ne remplace l'autre |

### 5.2 F0.2 — lecture différentielle, chiffrée

Mesure : exploration seule, géométrie `atr_2_2` (RR 1:1 symétrique — c'est la
géométrie sous laquelle la dérivation du seuil ci-dessous est valide), poolée
sur les deux instruments, sur le **jeu d'entrées primaire de la famille B en
lecture suiveuse** (`lookback` 260, `q` 0,20) — c'est la forme exacte du
résultat de Klitgaard & Weir, donc le seul endroit où l'on sait ce qui DOIT
apparaître. Coûts réels.

Notation : `E_h` = R/trade HONNÊTE, `E_c` = R/trade FUITÉE-CONTEMPORAINE,
`E_3` = R/trade FUITÉE-3J.

**Ordre d'évaluation obligatoire — b avant a** (il faut d'abord savoir si
l'instrument est calibré, avant de comparer quoi que ce soit à lui) :

| # | Condition | Lecture figée | Suite |
|---|---|---|---|
| **F0.2b** | `E_c ≤ +0,10 R` | **SOUPÇON DE BUG DE PIPELINE.** La corrélation contemporaine est un fait établi (30-45 % de la variance hebdomadaire expliquée) ; ne pas la retrouver alors qu'on lit délibérément la donnée en synchrone signale une erreur de branchement — mauvais code contrat, signe inversé, jointure de dates fausse, colonne vide — **pas une découverte** | **ARRÊT**, réparation, re-run complet |
| **F0.2a** | `E_c − E_h < +0,10 R` | **ALIGNEMENT CASSÉ.** La chaîne honnête voit ce que voit la chaîne synchrone : elle lit donc, d'une manière ou d'une autre, de l'information non publique. La mesure honnête est **invalide** | **ARRÊT**, réparation avant toute conclusion |
| **F0.2c** | `E_c > +0,10 R` **ET** `E_c − E_h ≥ +0,10 R` | **DISPOSITIF SAIN.** F1-F9 peuvent être lus. `E_c − E_h` et `E_3 − E_h` **chiffrent la fuite évitée** et sont rapportés au VERDICT à ce titre | on continue |

#### Pourquoi le seuil est +0,10 R et pas autre chose

75 % de réussite directionnelle sur une géométrie symétrique RR 1:1 donne une
espérance brute de **0,75 − 0,25 = +0,50 R/trade**. Notre dispositif ne peut pas
en capturer la totalité : la littérature mesure des rendements hebdomadaires non
stoppés, nous stoppons à 2 ATR, nous payons le péage, et notre horizon est
borné. Exiger **un cinquième** de l'effet connu est donc très conservateur.

Conséquence à retenir : **franchir +0,10 R en version fuitée n'est pas une
performance, c'est le minimum syndical d'un branchement correct. Ne pas le
franchir est un symptôme.**

### 5.3 Ce que F0 n'est pas, écrit noir sur blanc

- Aucun chiffre d'une version fuitée n'entre dans une candidate.
- Aucune version fuitée ne passe au hold-out.
- Aucune version fuitée n'apparaît au VERDICT autrement que comme **mesure de
  l'instrument** et **chiffrage de la fuite évitée**.
- Un résultat fuité spectaculaire vaut **zéro** comme évidence sur l'avenir.
  C'est son rôle de valoir zéro : il est le témoin positif, pas la preuve.

---

## 6. Effectif minimal — dérivation du seuil d'épisodes

Le nombre de trades ne suffit pas (§3). Le seuil est posé sur les **épisodes
indépendants**, et il est dérivé — pas choisi — par la question suivante :

> *En dessous de combien d'épisodes une cellule ne pourrait-elle PAS être
> significative, même avec un historique parfait ?*

Test de signe unilatéral sur `n` épisodes, tous favorables : `p = 2⁻ⁿ`.

| Étage | Multiplicité | Calcul | Seuil retenu |
|---|---|---|---|
| **Exploration** | 128 cellules | `2⁻¹² × 128 = 0,031 < 0,05` ; `2⁻¹¹ × 128 = 0,063 > 0,05` | **≥ 12 épisodes** |
| **Hold-out** | ≤ 3 candidates | `n = 12` tolère **un** épisode défavorable (`p = 0,0032 × 3 = 0,010`) ; `n = 8` exigerait un sans-faute (`7/8` donne `0,035 × 3 = 0,105`) | **≥ 12 épisodes** |

Un test de confirmation qui ne peut passer que sur un parcours parfait n'est pas
un test. D'où le même seuil de 12 des deux côtés, pour deux raisons différentes.

**Le test de signe ne sert QUE à dériver ce plancher.** Le critère de décision
reste le R/trade net et le percentile témoin (F2, F9) — pas un compte
d'épisodes gagnants.

---

## 7. Règle de sélection des candidates (écrite AVANT tout résultat)

1. **Exploration seule.** Walk-forward ancré 4 fenêtres par instrument. Sont
   **éligibles** les cellules satisfaisant simultanément **F4** (≥ 60 trades OOS
   cumulés ET ≥ 12 épisodes) et **F1** (espérance à coût nul > 0).
2. **Témoin apparié** (200 tirages, graine 20260819) sur les éligibles les mieux
   classées par `avg_oos` : retenir **percentile ≥ 95** (F2).
3. Appliquer dans l'ordre **F3** (5 graines), **F5** (voisinage), **F6** (sens
   séparés), **F7** (domination du suiveur).
4. **Au plus 3 candidates**, toutes familles et instruments confondus. En cas
   d'excédent : classement par percentile témoin, puis R/trade OOS net. En cas
   de déficit : **aucun repêchage** — s'il n'en survit qu'une, il n'y en a
   qu'une ; s'il n'en survit aucune, le hold-out n'est jamais ouvert.
5. La liste est **écrite au VERDICT et commitée AVANT** l'ouverture du scellé.

---

## 8. Falsifications — TOUTES chiffrées, figées

Prérequis absolu : **F0 passée** (§5). Sans elle, ce tableau ne se lit pas.

| # | Condition | Seuil | Si déclenchée |
|---|---|---|---|
| **F1** | Espérance à **coût nul** (exploration, plein échantillon) | R/trade ≤ 0 | **PAS D'EDGE** pour la cellule — le signal est négatif avant même le péage, inutile d'aller plus loin |
| **F2** | Témoin empirique (`control_arm`, 200 tirages, graine 20260819, `engine_kwargs` identiques) sur le `honest_r` OOS | percentile **< 95** | cellule éliminée — le timing n'apporte rien au-delà du profil de risque |
| **F3** | Multi-graines : témoin rejoué sur 5 graines (20260819 + k, k = 0..4) | percentile ≥ 95 sur **< 4/5** graines | artefact de graine — éliminée |
| **F4** | **Effectif indépendant** : exploration ≥ **60 trades** OOS cumulés **ET ≥ 12 épisodes** ; hold-out ≥ **25 trades ET ≥ 12 épisodes** (§6) | en dessous | **NON CONCLUSIF** pour l'objet concerné, sans négociation |
| **F5** | Voisinage : voisins à ±1 pas de grille (`lookback` voisin, `q` voisin, sortie voisine — même famille, même état, même sens) | **< 50 %** des voisins avec OOS > 0, **OU** médiane des voisins < 0 | sur-ajustement de cellule — éliminée |
| **F6** | Les deux sens mesurés **séparément** : un « edge » qui n'existe qu'agrégé long + short | aucun sens ne tient seul | artefact d'agrégation — éliminé |
| **F7** | **Domination du suiveur** (famille C) : R/trade OOS net de la lecture inverse (même état, sens opposé, même sortie) | la lecture suiveuse **≥** la candidate contrarienne | la candidate contrarienne est éliminée : c'est la lecture inverse qui porte le signal, et H15 est fausse dans sa forme contrarienne. **Cas d'intégrité** : si les DEUX lectures sont positives nettes sur les mêmes dates et la même géométrie, c'est arithmétiquement anormal → **bug de dispositif, ARRÊT** |
| **F8** | Cohérence trans-instruments (**informatif, faible**) : la config candidate appliquée à froid à l'autre instrument, R/trade poolé | ≤ **−0,05 R/t** | suspicion de sélection d'instrument — dégradé au verdict, documenté. **Réserve permanente** : XAUUSD et EURUSD partagent la jambe dollar ; passer F8 n'est **pas** une réplication indépendante et ne sera jamais plaidé comme telle |
| **F9** | **HOLD-OUT SCELLÉ** (ouvert UNE fois, ≤ 3 candidates) : R/trade **net** > 0 **ET** percentile témoin hold-out (200 tirages, `control_arm` tranche unique) **≥ 90** **ET** F4 hold-out satisfaite | net ≤ 0 **OU** percentile < 90 | **PAS D'EDGE** pour la candidate — définitif. F4 non satisfaite → **NON CONCLUSIF** pour la candidate |

Lecture des filtres : **uniquement au R/trade**, jamais au PnL total (retirer
des trades baisse le total mécaniquement).

---

## 9. Verdict — règles d'issue, écrites d'avance

**Préalable** : si **F0** n'est pas passée, il n'y a **pas de verdict**. Le
livrable est alors un rapport de dispositif : ce qui a été détecté, ce qui a
été réparé, ce qui reste à réparer. Ni EDGE CANDIDAT, ni PAS D'EDGE.

- **EDGE CANDIDAT** — ≥ 1 candidate passe F1 à F9 (F8 documenté quel qu'il
  soit). Livrable : la stratégie + **proposition d'un forward-test scellé zéro
  argent** (motif `studies/gold_forward`), avec critère d'arrêt écrit d'avance.
  **JAMAIS de promotion PAPER ou LIVE** — R10, décision d'Adrian et de personne
  d'autre. Le forward est d'autant plus obligatoire ici que l'angle mort des
  **révisions** (`ANALYSIS.md` §9.1) n'est attrapable par aucun falsifieur
  rétrospectif : seule une observation prospective voit la donnée telle qu'elle
  arrive.
- **PAS D'EDGE** — aucune candidate ne passe F9, ou aucune candidate n'émerge
  de F1-F7. Livrable : le constat chiffré, par famille, par instrument et par
  sens, avec la comparaison explicite à l'attente a priori (`ANALYSIS.md` §0).
  Ce verdict **clôt le motif « niveau et impulsion du COT Legacy »** : aucune
  relecture des mêmes barres ne serait justifiée. La seule suite légitime
  serait une **donnée nouvelle** — le rapport TFF (*Leveraged Funds*), dans un
  dossier scellé séparé (`ANALYSIS.md` §4.3).
- **NON CONCLUSIF** — les effectifs (F4) tuent toutes les familles, ou le
  hold-out ne réunit pas 12 épisodes sur la ou les candidates. Livrable :
  consigner précisément ce qui manque, en épisodes, et à quel prix on
  l'obtiendrait (le seul levier réel étant le temps qui passe, l'historique
  de prix D1 étant plafonné).

---

## 10. Économie a priori — P0, à produire AVANT l'implémentation

Le premier pas des runners est une mesure **data-only** (aucun signal, aucune
stratégie), rapportée au VERDICT et non ici — ce fichier ne contient aucun
chiffre mesuré.

Formule figée :

```
drag(atr_2_2) = (spread_catalogue + 2 × 0,5 pip) / (2 × ATR14_médiane_D1)
drag(hold5)   = (spread_catalogue + 2 × 0,5 pip) /      ATR14_médiane_D1
```

À produire pour XAUUSD et EURUSD, sur l'exploration seule (le hold-out reste
scellé, y compris pour une statistique de données).

**Règle de lecture figée** : une cellule dont le `drag` dépasse **25 %** est
déclarée **morte sur papier** avant tout backtest (règle reconduite de s90
§2.3). Le péage D1 mesuré ailleurs dans le dépôt (0,46 pt de win rate, 1-5 % du
R) rend cette borne très improbable ici — elle est posée pour que le cas soit
tranché d'avance s'il se présente.

---

## 11. Ce que ce dossier ne fera PAS

- Aucune exploration au-delà des 128 cellules déclarées.
- Aucun timeframe autre que D1 (`ANALYSIS.md` §3).
- Aucune paire synthétique (`ANALYSIS.md` §2) — étude séparée, scellée à part.
- Aucun rapport TFF (`ANALYSIS.md` §4.3).
- Aucun filtre de session, de jour, de news, ni aucune gestion fine ajoutés en
  cours de route. Une idée née des chiffres est consignée comme **piste
  post-hoc** pour un dossier futur, jamais testée ici.
- Aucune modification de `core/`, en particulier **aucune modification de
  `core/data/cot.py`** — c'est le module qui rend la fuite impossible, et cette
  étude a intérêt à un résultat positif.
- Aucun sizing, aucun portefeuille, aucun PAPER/LIVE.

---

## 12. Angles morts assumés (notés AVANT mesure)

1. **Les révisions de la CFTC.** Tout notre échantillon est de la donnée
   révisée (`ANALYSIS.md` §9.1). Aucun falsifieur rétrospectif ne peut le
   corriger. C'est l'angle mort principal, et il ne se ferme que par un forward.
2. **Deux instruments, une seule jambe dollar.** F8 est faible par construction.
   L'univers de ce dossier ne permet **aucune** réplication indépendante — c'est
   la limite structurelle du périmètre « contrats directs », et elle est le prix
   à payer pour ne pas contaminer la lecture avec des proxies.
3. **La sélection reste de la sélection.** Le percentile témoin d'une cellule
   choisie parmi 128 est optimiste. C'est ce que F9 (hold-out vierge) est
   chargé d'attraper — et lui seul.
4. **Les 4 fenêtres OOS sont emboîtées, pas indépendantes** (`docs/METHODOLOGY.md`
   §9).
5. **Un hold-out de 12 épisodes reste mince.** C'est le maximum que la
   fréquence hebdomadaire et la profondeur des prix D1 autorisent. Un EDGE
   CANDIDAT issu de ce dossier sera donc, par construction, **faible en
   confiance** — ce qui est exactement la raison pour laquelle sa seule suite
   est un forward scellé, et jamais une promotion.
6. **La reclassification des catégories de traders** n'est mitigée que
   partiellement par le percentile glissant (`ANALYSIS.md` §9.3) : une marche
   d'escalier créerait un faux extrême pendant toute la fenêtre.
7. **`publication()` est une règle reconstruite**, pas une date observée. Un
   décalage de publication exceptionnel, hors du gel 2025 déjà codé, passerait
   inaperçu.
8. **Futures ≠ spot** (`ANALYSIS.md` §9.4) : le positionnement mesuré n'est pas
   celui du marché que nous tradons, seulement son proxy le plus proche.
