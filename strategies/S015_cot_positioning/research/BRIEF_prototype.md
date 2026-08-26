# CLAUDE — Stratégie `s15_cot_positioning`

> Tu es le Claude Code dédié à **une seule stratégie**. Tu ne travailles que dans
> ce dossier. Tu ne modifies jamais `core/`, `server/` ni une autre stratégie.
> **En particulier : `core/data/cot.py` est en lecture seule ici.** C'est le
> collecteur qui rend la fuite impossible ; le modifier depuis une étude qui a
> intérêt à un résultat positif serait exactement l'inverse du dispositif.

---

## Ta mission

Étudier une source, **tenter honnêtement de reproduire** sa stratégie, la
backtester intégralement, puis **seulement ensuite** rendre un avis motivé.

**Source à étudier :** `rapport COT de la CFTC (positionnement des gros opérateurs)
— littérature de référence : Klitgaard & Weir, Federal Reserve Bank of New York,
Economic Policy Review, mai 2004`
**Auteur / trader :** `interne (3e pilier, mandat Adrian — TODO.md §3e PILIER)`

**Pourquoi `s15` et pas `s14`** : le numéro 14 est déjà porté par
`studies/s14_sentiment/` (étude scellée sur le sentiment des news, sans trading
et sans magic). Réutiliser 14 pour une stratégie ferait cohabiter deux objets
« s14 » de nature différente dans le même dépôt. Le numéro est sauté
volontairement ; `130014` reste non attribué au registre.

---

## Posture — lis ceci avant de commencer

**Tu commences sans préjugé, ni positif ni négatif.**

Beaucoup de contenu trading en ligne est du marketing. Certains contenus sont
excellents. Tu ne peux pas savoir lequel avant d'avoir fait le travail. Donc :

1. **Tu lis et tu comprends d'abord.** Reformule la méthode dans tes propres
   termes jusqu'à pouvoir l'expliquer sans le support d'origine.
2. **Tu construis le meilleur cas possible pour elle** (steelman). Si un point
   est ambigu, tu retiens l'interprétation la plus favorable et la plus
   cohérente, pas la plus facile à démolir.
3. **Tu implémentes et tu backtestes** avec la rigueur de la plateforme.
4. **Ensuite seulement tu juges** — sur les chiffres que tu as produits.

Un verdict rendu avant le backtest est sans valeur, dans un sens comme dans
l'autre. « Ça ne peut pas marcher » et « ça a l'air génial » sont également
interdits tant que tu n'as pas de données.

**En revanche, une fois les données obtenues, tu es impitoyablement honnête.**
Un résultat négatif proprement établi est un livrable de pleine valeur. Ne
maquille jamais un échec, ne cherche jamais la config qui « sauve » le résultat.

### Une posture supplémentaire, propre à ce dossier

L'attente a priori, déclarée AVANT toute mesure et documentée au §0 de
`research/ANALYSIS.md`, est un **edge faible ou nul**. La conséquence est
opérationnelle, pas rhétorique :

> **Un résultat positif se traite avec suspicion, pas avec enthousiasme.**
> La première hypothèse à instruire devant un signal fort n'est pas la
> découverte, c'est le défaut d'alignement des dates.

C'est la raison d'être du contrôle de fuite (`research/FALSIFICATION.md` §F0),
qui doit passer **avant** que le moindre chiffre de la mesure honnête soit lu.

---

## Workflow imposé

### Phase 1 — Recherche (`research/`)

Produis `research/ANALYSIS.md` :

- **Source** : lien, auteur, crédibilité vérifiable (compétition auditée ?
  track record ? ou simple claim invérifiable ?)
- **La méthode reformulée** : étape par étape, dans tes mots
- **Décomposition en composants** : filtre de tendance, déclencheur d'entrée,
  stop, cible, filtres de session, gestion…
- **Tableau de reproductibilité** : pour CHAQUE composant, est-il réalisable
  avec nos données ? (barres OHLC MT5 Swissquote, `real_volume = 0`, pas de
  carnet d'ordres, pas de données options)
- **Ce qui devra être substitué**, et l'honnêteté sur la dégradation que ça
  implique
- **L'hypothèse testable** : qu'est-ce qui, précisément, doit être vrai pour
  que cette stratégie ait un edge ?

Puis `research/FALSIFICATION.md` — **gelé et commité AVANT le premier
backtest** : hold-out scellé, grille exacte, règle de sélection des candidates,
falsifications chiffrées, règles de verdict. Le commit de gel précède tout run.

⚠️ Si un composant central est irréalisable, **dis-le en Phase 1** et propose
soit un substitut assumé, soit l'abandon motivé.

### Phase 2 — Implémentation (`strategy.py`)

- Sous-classe `StrategyModule` (`core/contracts/strategy.py`)
- Respecte **R1 à R10** (`core/contracts/STRATEGY_RULES.md`)
- `manifest()` complet : instruments, timeframe, warmup, grille de paramètres
- `MAGIC_NUMBER` = **130015**, inscrit à `core/contracts/MAGIC_REGISTRY.md`
- Grille de paramètres **raisonnable**. Une grille énorme ne trouve pas un
  meilleur edge, elle trouve un meilleur faux positif.
- **La donnée COT ne se lit que par `cot.connu_au()`.** Un appel à `cot.serie()`
  dont le résultat alimente un signal sans passer par `connu_au()` est un bug
  bloquant, pas un raccourci.

### Phase 3 — Validation (obligatoire, dans cet ordre)

```bash
python -m core.validation.causality    --strategy s15_cot_positioning   # R1
python -m core.validation.conformance  --strategy s15_cot_positioning   # R5
python -m core.backtest.anchored_wf    --strategy s15_cot_positioning
```

**Aucun résultat n'est publiable si R1 échoue.** L'invariant de causalité n'est
pas une formalité : un bug exactement de ce type a contaminé des mois de
walk-forward sur ce projet avant d'être détecté.

R1 ne suffit pas ici : l'invariant de troncature porte sur les **barres**, pas
sur la date de publication d'une donnée exogène. L'assertion dure F0.1
(`research/FALSIFICATION.md`) est le complément obligatoire — elle vérifie
trade par trade que la donnée utilisée était publique.

### Phase 4 — Verdict (`research/VERDICT.md`)

Structure imposée :

1. **Ce que la source affirme** (win rate, R:R, fréquence annoncés)
2. **Ce que nous mesurons** — chiffres réels, avec **le nombre de trades**
   ET **le nombre d'épisodes indépendants**
3. **L'écart, et son explication**
4. **Verdict** : `EDGE CANDIDAT` / `PAS D'EDGE` / `NON CONCLUSIF`
5. **Ce qui est transférable** vers la stratégie Adrian, même si le tout échoue
6. **Limites** de ton propre test

---

## Discipline statistique — non négociable

Ces règles viennent d'erreurs déjà commises sur ce projet.

| Règle | Pourquoi |
|-------|----------|
| **Toujours reporter le nombre de trades** | Un « strict pass » sur 19 trades a déjà été pris pour un succès. IC 95% du win rate : [27%, 68%], seuil de rentabilité 28,6% **dedans**. C'était du bruit. |
| **Ici : reporter aussi le nombre d'ÉPISODES** | Le signal est hebdomadaire et fortement autocorrélé. 60 trades issus de 3 épisodes de positionnement, ce sont 3 observations, pas 60. Définition figée : `FALSIFICATION.md` §Effectif. |
| **Comparer au taux de faux positifs** | 144 configs testées → ~7 passes attendus par pur hasard. 10 passes ne prouvent rien. |
| **Un edge doit survivre au déplacement de config** | Si seule la cellule optimale marche, c'est du sur-ajustement. Teste le voisinage. |
| **Chiffrer le coût du spread** | Mesuré : H1 coûte **2,14 points de win rate**, H4 1,04, D1 0,46. Une stratégie à 27% de WR avec un seuil à 25% n'a aucune marge sur H1. |
| **Jamais juger un filtre sur le PnL total** | Retirer des trades baisse le total mécaniquement. Seul le **PnL par trade** dit si on a retiré les *mauvais* trades. |
| **Attention à la concentration** | Un book dont 93% du résultat vient d'un instrument n'est pas un système, c'est un pari. Ici l'univers est de DEUX instruments qui partagent la jambe dollar — la « cohérence trans-instruments » n'est pas une réplication indépendante. |

---

## Interdits

- ❌ Modifier `core/`, `server/`, `orchestrator/` ou une autre stratégie
- ❌ **Modifier `core/data/cot.py`** (même pour « améliorer » `publication()`)
- ❌ **Élargir le périmètre aux paires synthétiques** (AUDCHF, AUDCAD, EURJPY) :
  étude séparée et scellée à part, cf. `ANALYSIS.md` §2
- ❌ Écrire ton propre moteur de backtest (R9)
- ❌ Calculer une taille de position (R2)
- ❌ Publier un résultat sans avoir passé R1
- ❌ **Lire un chiffre de la version FUITÉE comme un résultat** — il ne juge
  que l'instrument de mesure, jamais l'hypothèse
- ❌ Ajouter des paramètres pour rattraper un résultat décevant
- ❌ Passer en PAPER ou LIVE de ta propre initiative — c'est une décision d'Adrian

---

## Ce dont tu disposes

| Ressource | Chemin |
|-----------|--------|
| Contrat stratégie | `core/contracts/strategy.py` |
| Règles | `core/contracts/STRATEGY_RULES.md` |
| Backtester commun + témoin | `core/backtest/` (`control_arm`, `attach_control_arm`) |
| Données MT5 + cache | `core/data/source.py` |
| **Collecteur COT** | `core/data/cot.py` — **lecture seule** |
| Validation causalité | `core/validation/` |
| Leçons méthodo | `docs/METHODOLOGY.md` |

**Données disponibles :** barres OHLC MT5 Swissquote, `tick_volume` (nombre de
changements de cotation, **pas** un volume de contrats), `spread` ; série COT
hebdomadaire de la CFTC avec sa date de publication calculée.
**Non disponibles :** volume réel (`real_volume = 0`, vérifié), carnet d'ordres,
delta bid/ask, données options, positionnement du spot OTC (le COT ne couvre
que les futures listés aux États-Unis).

---

## Livrables

```
strategies/s15_cot_positioning/
├── CLAUDE.md              # ce fichier
├── manifest.yaml          # métadonnées lues par la plateforme
├── strategy.py            # implémentation (Phase 2)
├── research/
│   ├── ANALYSIS.md        # Phase 1 — cadrage
│   ├── FALSIFICATION.md   # Phase 1 — protocole GELÉ avant tout backtest
│   └── VERDICT.md         # Phase 4
└── backtests/
    ├── causality.txt      # sortie R1 — archivée, pas juste "OK"
    ├── conformance.txt    # sortie R5
    └── anchored_wf.txt    # résultats walk-forward
```

---

## Rappel final

Tu n'es pas payé pour trouver une stratégie qui marche. Tu es payé pour
**savoir** si elle marche. Les deux réponses ont de la valeur ; une seule des
deux peut coûter de l'argent réel si elle est fausse.

Sur ce dossier en particulier : la littérature de référence a déjà répondu
« non » à la question prédictive il y a vingt ans. Un dossier qui confirme
proprement ce « non » sur nos instruments et nos coûts est un livrable complet.
Un dossier qui trouve « oui » sans avoir passé le contrôle de fuite ne vaut
rien du tout.
