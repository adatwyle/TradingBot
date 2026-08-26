# RobinBot — Règles de compatibilité des stratégies

> Toute stratégie qui ne respecte pas ces règles est **refusée par la plateforme**.
> Ce ne sont pas des conventions de style : chacune vient d'un bug réel ou d'une
> erreur méthodologique qui nous a coûté du temps ou faussé des résultats.

---

## R1 — Causalité stricte (règle non négociable)

Une stratégie ne peut **jamais** utiliser une information postérieure à la barre
qu'elle traite.

**Test obligatoire — l'invariant de troncature :**

```
generate_signals(precompute(df),     params, T)
    ==
generate_signals(precompute(df[:T]), params, T)      pour tout T
```

Si les deux diffèrent d'un seul trade, il y a fuite.

**Pourquoi cette règle existe :** en août 2026, `fast_bt_multi` clôturait les
positions résiduelles à `closes[-1]` — la dernière barre du tableau **complet** —
alors que sa boucle respectait `end_idx`. Chaque tranche d'entraînement valorisait
donc son trade ouvert à un prix futur. Le bug a contaminé des mois de walk-forward
avant d'être trouvé. Il était invisible sans ce test.

`core/validation/causality.py` exécute l'invariant. **Aucune stratégie ne passe en
PAPER sans l'avoir validé.**

---

## R2 — Séparation stratégie / risque

Une stratégie **ne calcule jamais** :
- une taille de position (lots)
- un pourcentage de risque
- une exposition

Elle émet un `Signal` avec `entry`, `stop`, `target`. La couche `core/risk/`
convertit ça en ordre exécutable selon l'allocation décidée sur le dashboard.

**Pourquoi :** c'est ce qui permet de changer le capital alloué à une stratégie,
ou de la bloquer, sans toucher à son code. Une stratégie qui lit le solde du
compte casse cette isolation.

---

## R3 — Stop loss obligatoire

`Signal.stop` ne peut pas être `None`. Le constructeur lève une exception.
Le stop part au broker (set & forget) et survit à un crash du process Python.

---

## R4 — Magic number unique

Chaque stratégie déclare un `MAGIC_NUMBER` unique dans son manifest. C'est ce qui
isole ses positions de celles des autres stratégies sur le **même compte
Swissquote**. Sans ça, impossible d'attribuer un trade à une stratégie — donc
impossible de faire le reporting fiscal ni de bloquer une stratégie seule.

**Registre :** `core/contracts/MAGIC_REGISTRY.md`. Toute collision est un bug
bloquant.

---

## R5 — Cohérence backtest / live

`generate_signals()` (backtest) et `on_bar()` (live) doivent produire les
**mêmes décisions** sur le même état de marché. `core/validation/conformance.py`
rejoue les deux chemins sur l'historique et compare.

**Pourquoi :** c'est la première cause de « ça marchait en backtest ».

---

## R6 — Aucun état caché

`on_bar()` doit être une fonction pure de `(ctx, self.params)`. L'orchestrateur
peut redémarrer le process à tout moment — la stratégie doit se comporter
identiquement. Tout état nécessaire doit être reconstructible depuis `ctx`.

Exception tolérée : compteurs internes (pertes consécutives) exposés via
`health()` et reconstructibles depuis le ledger.

---

## R7 — Le manifest est la seule source de vérité

Instruments, timeframe, warmup, grille de paramètres : tout est déclaré dans
`manifest()`. Ni le backtester, ni l'orchestrateur, ni le dashboard ne codent en
dur quoi que ce soit sur une stratégie.

---

## R8 — Tout passe par le ledger commun

Aucune stratégie n'écrit ses propres résultats. Chaque trade — backtest, paper
ou live — est enregistré par `core/ledger/` avec son `strategy_id` et son `mode`.

**Pourquoi :** le reporting fiscal exige le détail de chaque opération, et le
dashboard agrège depuis une source unique. Une stratégie qui tient ses propres
comptes rend l'un et l'autre impossibles.

---

## R9 — Backtester commun, jamais réimplémenté

Une stratégie fournit ses signaux ; l'exécution (spread, slippage, SL/TP,
circuit breaker) appartient à `core/backtest/`. Une stratégie qui code sa propre
boucle de backtest produit des chiffres non comparables aux autres.

---

## R10 — Le mode PAPER n'est pas optionnel

Progression obligatoire : `RESEARCH → BACKTESTED → PAPER → LIVE`.
Aucun passage direct backtest → argent réel. Durée minimale en PAPER définie
dans `docs/PROMOTION_POLICY.md`.

---

## Checklist d'admission

Avant qu'une stratégie passe de `RESEARCH` à `BACKTESTED` :

- [ ] Sous-classe `StrategyModule`, manifest complet
- [ ] `MAGIC_NUMBER` unique, inscrit au registre
- [ ] **Invariant de causalité (R1) passé** — sortie du test archivée
- [ ] Conformance backtest/live (R5) passée
- [ ] Aucune lecture de solde, aucun calcul de taille (R2)
- [ ] `stop` toujours renseigné (R3)
- [ ] Anchored walk-forward exécuté, résultats dans `backtests/`
- [ ] **Nombre de trades reporté** sur chaque résultat (un pass sur 19 trades
      n'est pas une preuve — voir `docs/METHODOLOGY.md`)
- [ ] Coût du spread chiffré pour le timeframe visé
- [ ] `research/ANALYSIS.md` rédigé : source, hypothèse, ce qui est reproductible
      et ce qui ne l'est pas
