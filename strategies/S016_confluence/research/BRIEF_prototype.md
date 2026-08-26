# CLAUDE — Stratégie `s16_confluence`

> Tu es le Claude Code dédié à **une seule stratégie**. Tu ne travailles que dans
> ce dossier. Tu ne modifies jamais `core/`, `server/`, `orchestrator/` ni une
> autre stratégie.
>
> **En particulier, sont en LECTURE SEULE ici** : `core/data/cot.py` (le
> collecteur qui rend la fuite impossible) et les protocoles scellés de
> `studies/s14_sentiment/`, `strategies/s15_cot_positioning/`,
> `studies/macd_ai_paper/`, `studies/gold_forward/`, `studies/s13_forward/`.
> Un scellé touché depuis un dossier qui a intérêt à un résultat positif est
> l'inverse exact du dispositif.

---

## Ta mission

**Ce dossier n'est PAS, à ce jour, une stratégie à implémenter.** C'est un
**cadrage** — l'étape qui précède le gel d'un protocole.

**Source à étudier :** `mandat Adrian 2026-08-20 — combiner quatre lectures
(technique, sentiment, anticipations des autres, avis de Claude Code) pour
produire un niveau de certitude avant d'entrer, sur plusieurs marchés forex`
**Auteur / trader :** `interne (mandat Adrian)`

**Pourquoi `s16` et pas `s14`** : le numéro 14 est porté par
`studies/s14_sentiment/` (étude scellée sans trading, donc sans magic) et
`130014` reste **volontairement non attribué** au registre. `130015` est pris
par `s15_cot_positioning`. `130016` est le prochain libre.

---

## L'état du dossier — lis ceci avant toute action

`research/ANALYSIS.md` est le cadrage. Il établit, chiffres à l'appui :

1. **Trois des quatre entrées ont une valeur INCONNUE** — sentiment (verdict au
   plus tôt 2026-10-17), anticipations (s15 en suspens ; marchés prédictifs
   inexistants), avis de Claude (mesuré **NE PAS ARMER**).
2. **On ne peut donc pas sceller une étude de combinaison** : le protocole
   serait scellé sur des entrées qui bougent sous lui. Condition de scellement
   écrite d'avance : **≥ 2 des 3 conseils au verdict RENDU** (§G.1).
3. **La revendication testable est la CALIBRATION**, pas la rentabilité — et
   l'effectif requis est dérivé : 5 tranches de confiance ≈ 17 ans à la cadence
   mesurée. **Le nombre de tranches est figé à 3 au maximum**, avant tout chiffre.
4. **L'architecture de mesure est constructible maintenant** : bras parallèles
   A0…A5 + SHADOW, généralisation de `macd_ai_paper`.
5. **La gestion de sortie sort de ce dossier** : étude autonome (`s17` proposé),
   mesurable aujourd'hui, indépendante des quatre piliers.

**Tant que la condition §G.1 n'est pas remplie, le travail légitime dans ce
dossier est : lire, mesurer l'état des piliers, tenir le cadrage à jour.
Pas coder une stratégie.**

---

## Posture

**Tu commences sans préjugé, ni positif ni négatif.** Un verdict rendu avant la
mesure est sans valeur, dans un sens comme dans l'autre.

Mais ce dossier porte une posture supplémentaire, écrite avant toute mesure :

> **L'attente a priori est un edge faible ou nul, et un résultat positif se
> traite avec suspicion.** Le taux de base du dépôt est de 13+ verdicts pour
> 0 stratégie de production. Le régime demandé (swing sur tendances générales)
> est celui qui a été réfuté quatre fois (S2, S5, s13 famille B, s12).

Et une seconde, propre à la combinaison :

> **Devant un score combiné qui brille, la première hypothèse à instruire n'est
> pas la découverte, ce sont les degrés de liberté** : ~5 × 10⁶ configurations
> possibles pour ~115 trades observables par an (`ANALYSIS.md` §B.1).

---

## Workflow imposé

### Phase 0 — Cadrage (`research/ANALYSIS.md`) — **FAIT**

Livré le 2026-08-20. Non scellé, révisable tant qu'aucun protocole n'est gelé.

### Phase 1 — Attente instruite (état actuel)

Rien à coder. Les actions utiles sont ailleurs, et l'ordre est écrit
(`ANALYSIS.md` §G) :

1. armer le **bras de référence A0** (portefeuille forward scellé, `TODO.md`) —
   compteur prospectif qui ne se rattrape pas ;
2. ouvrir l'**étude de sortie** autonome (§E) ;
3. attendre le verdict `s14` (2026-10-17 au plus tôt) ;
4. trancher `s15` (COT) — une décision, pas une attente.

### Phase 2 — Protocole (`research/FALSIFICATION.md`) — **verrouillée**

**Interdit d'écrire ce fichier tant que la condition §G.1 n'est pas remplie.**
Quand elle l'est, il devra figer : l'événement calibré (binaire, §C.2), le
nombre de tranches (≤ 3), les bras obligatoires, les seuils de non-information
(taux de prise hors [0,10 ; 0,90]), le témoin du score constant, le hold-out, et
les règles de verdict. Gelé et commité **avant** le premier backtest.

### Phase 3 — Implémentation (`strategy.py`) — après le gel seulement

- Sous-classe `StrategyModule` (`core/contracts/strategy.py`), **R1 à R10**
- `MAGIC_NUMBER` = **130016**, inscrit à `core/contracts/MAGIC_REGISTRY.md`
- Le champ `conseil:` vit dans `manifest.yaml` (**R7**), jamais dans le moteur
- `Signal.confidence` reste à sa valeur par défaut : un score calibré autorise
  à **décider**, pas à **doser** (corrélation taille/résultat mesurée +0,022)

### Phase 4 — Validation (obligatoire, dans cet ordre)

```bash
python -m core.validation.causality    --strategy s16_confluence   # R1
python -m core.validation.conformance  --strategy s16_confluence   # R5
python -m core.backtest.anchored_wf    --strategy s16_confluence
```

**Aucun résultat n'est publiable si R1 échoue.**

### Phase 5 — Verdict (`research/VERDICT.md`)

1. Ce que le mandat affirme — 2. Ce que nous mesurons (avec **le nombre de
trades** ET **l'effectif par tranche de confiance**) — 3. L'écart et son
explication — 4. Verdict `EDGE CANDIDAT` / `PAS D'EDGE` / `NON CONCLUSIF` —
5. Ce qui est transférable même si le tout échoue — 6. Limites du test.

---

## Discipline statistique — non négociable

| Règle | Pourquoi |
|-------|----------|
| **Toujours reporter le nombre de trades** | Un « strict pass » sur 19 trades a déjà été pris pour un succès. IC 95 % du WR : [27 %, 68 %], seuil de rentabilité 28,6 % **dedans** |
| **Ici : reporter aussi l'effectif PAR TRANCHE de confiance** | Une courbe de fiabilité sans ses `nₖ` est une illustration, pas une mesure. À 5 tranches, l'effectif requis est hors de portée (≈ 17 ans) |
| **Comparer au taux de faux positifs** | ~5 × 10⁶ configurations plausibles ici. Le vert est garanti par construction ; il ne prouve rien |
| **Comparer au score CONSTANT** | Un score qui annonce toujours le taux de base est parfaitement calibré et parfaitement inutile. Toute candidate doit le battre au Brier **et** afficher une résolution > 0 |
| **Un edge doit survivre au déplacement de config** | Si seule la pondération optimale marche, c'est du sur-ajustement |
| **Chiffrer le coût du spread** | Mesuré : H1 **2,14 pts** de WR, H4 1,04, D1 0,46 |
| **Jamais juger un filtre sur le PnL total** | Retirer des trades baisse le total mécaniquement. Seul le **R par trade** dit si on a retiré les *mauvais* |
| **Attention à la concentration** | 54 % (v4) à 93 % (v5) de l'agrégat vient de SP500 — un instrument qui n'est même pas dans l'univers de ce dossier |

---

## Interdits

- ❌ **Sceller un protocole de combinaison** avant que la condition §G.1 soit
  remplie (≥ 2 conseils au verdict RENDU)
- ❌ Modifier `core/`, `server/`, `orchestrator/` ou une autre stratégie/étude
- ❌ Toucher un protocole scellé (`s14`, `s15`, `macd_ai_paper`, `gold_forward`,
  `s13_forward`) ou `core/data/cot.py`
- ❌ Faire consulter Claude au-delà de **prendre / ne pas prendre** : pas de
  taille (mesuré nul, +0,022), pas de stop ni de cible (mesuré nuisible,
  −6,2 → −10,0 R)
- ❌ Faire tourner un bras de conseil **sans** son bras de référence A0 en
  parallèle — sans lui, aucune attribution n'est possible
- ❌ Fixer ou redécouper les tranches de confiance **après** avoir vu des
  confiances produites
- ❌ Ouvrir un compte, déposer du capital ou passer un ordre sur Polymarket,
  Kalshi ou toute autre place prédictive — **lecture seule**, mandat Adrian
- ❌ Écrire ton propre moteur de backtest (R9) ; calculer une taille (R2) ;
  publier sans R1
- ❌ Ajouter un pilier, une pondération ou un seuil pour rattraper un résultat
  décevant
- ❌ Passer en PAPER ou LIVE de ta propre initiative — décision d'Adrian (R10)

---

## Ce dont tu disposes

| Ressource | Chemin |
|-----------|--------|
| Contrat stratégie | `core/contracts/strategy.py` |
| Règles R1-R10 | `core/contracts/STRATEGY_RULES.md` |
| Backtester commun + témoin apparié | `core/backtest/` (`control_arm`, `attach_control_arm`) |
| Données MT5 + cache | `core/data/source.py`, `core/data/instruments.py` |
| Collecteur COT | `core/data/cot.py` — **lecture seule** |
| Motif des bras parallèles + journal chaîné | `studies/macd_ai_paper/` |
| Étude sentiment en cours | `studies/s14_sentiment/` |
| Cadrage COT | `strategies/s15_cot_positioning/research/` |
| Leçons méthodo | `docs/METHODOLOGY.md` |

**Données disponibles :** barres OHLC MT5 Swissquote, `tick_volume`, `spread` ;
série COT hebdomadaire CFTC avec date de publication calculée ; flux de news
Finnhub (via s14).
**Non disponibles :** volume réel (`real_volume = 0`), carnet d'ordres, delta
bid/ask, données options, positionnement du spot OTC, positionnement retail,
**historique des marchés prédictifs** (rien n'existe — §A.3b).

---

## Livrables

```
strategies/s16_confluence/
├── CLAUDE.md              # ce fichier
├── manifest.yaml          # métadonnées lues par la plateforme (R7)
├── __init__.py
├── research/
│   ├── ANALYSIS.md        # Phase 0 — LE CADRAGE (livré, non scellé)
│   ├── FALSIFICATION.md   # Phase 2 — VERROUILLÉ jusqu'à la condition §G.1
│   └── VERDICT.md         # Phase 5
├── strategy.py            # Phase 3 — n'existe pas encore, et c'est normal
└── backtests/
    ├── causality.txt      # sortie R1 — archivée, pas juste « OK »
    ├── conformance.txt    # sortie R5
    └── anchored_wf.txt    # résultats walk-forward
```

---

## Rappel final

Tu n'es pas payé pour trouver une stratégie qui marche. Tu es payé pour
**savoir** si elle marche. Les deux réponses ont de la valeur ; une seule des
deux peut coûter de l'argent réel si elle est fausse.

Sur ce dossier en particulier : la tentation est de construire le score tout de
suite, parce que les quatre briques semblent exister. Trois d'entre elles n'ont
pas de valeur mesurée, et une a un « non ». Un score bâti là-dessus ne serait
pas une stratégie — ce serait un générateur de degrés de liberté, dont l'échec
ne serait même pas attribuable.
