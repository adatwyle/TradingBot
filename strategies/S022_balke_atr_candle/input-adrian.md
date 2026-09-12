# input-adrian — S022 ATR Candle Breakout (René Balke)

*Maintenu par cc-support. Réécrit en place, pas d'historique (git porte la traçabilité).*

## Identité
- **Numéro** : S022 · magic `130022`
- **Source** : EA gratuit « ATR Candle Breakout » (BM Trading, René Balke) —
  page produit <https://bmtrading.de/en/expert-advisors/atr-candle-breakout/>,
  billet de blog <https://bmtrading.de/en/blog/atr-candle-breakout-ea/> (2026-06-09),
  guide d'entrées officiel `docs/sources/renebalke/ea_inputs/ATR Candle Breakout EA Inputs.pdf`,
  réglages live relevés dans `docs/sources/renebalke/EA_inputs_et_reglages-live_2026-09-12.md` § 2.4.
- **Auteur déjà connu du dépôt** : S009 (Session Range Breakout), S020 (MACD cross),
  S021 (grille martingale, réservée). Corpus `docs/sources/renebalke/`.

## La demande d'Adrian (2026-09-12)
> « reproduis la stratégie de Balke telle quelle, mesure, rapporte ; GO 2026-09-12 »

Et la doctrine du même jour, qui gouverne désormais toutes les stratégies :
> « les règles générales ne sont plus valables — chaque stratégie porte ses propres
> règles — bien entendu elles auront des règles communes pour éviter les pertes
> consécutives. »

Et la correction de méthode : **aucun avis avant d'avoir mesuré**. On construit, on
mesure, puis on rend compte de ce que disent les chiffres.

## Pourquoi celle-ci en premier
C'est, des six EA de Balke, **le plus complet et le plus prouvé** : spécification
publique intégrale, réglages live connus, et — unique dans ce dépôt — des **chiffres
publiés à confronter** : 11 ans d'or en tick réel Dukascopy (1 552 trades, WR ≈ 23 %,
PF 1,15, +19 527 € sur 50 k€, DD ≈ 9,6 %) et une comparaison test/live depuis mars 2026
(24 trades +516 € en réel contre 23 trades +634 € au testeur). Notre or H1 est en cache
et le moteur sait tout exprimer : aucune dépendance à lever.

## La règle, telle que son guide la décrit
Sur chaque bougie close : amplitude (haut − bas) > `ATR Multiplier` × ATR(`ATR Period`)
— l'ATR étant calculé sur les barres **strictement antérieures** ; la bougie doit fermer
à moins de `Close proximity` % de son amplitude de son extrême (du haut pour un achat,
du bas pour une vente) ; on suit son sens. Stop et cible en **pourcentage du prix
d'entrée**. **Ses réglages live** : H1, ATR 200, × 2,5, proximité 25 %, TP 2 %, SL 0,5 %
(RR 4), tous les filtres optionnels (tendance, ATR multi-unités, horaire, S/R) et le
trailing **désactivés**.

## État (2026-09-12)
- Reproduite telle quelle, **26 tests verts**, R1 (causalité) et R5 (backtest = live)
  passés sur données réelles — et le harnais refuse de publier quoi que ce soit si l'un
  des deux tombe.
- **Mesurée** : 12 cellules, XAUUSD H1, 6 ans (35 443 barres), walk-forward ancré
  4 fenêtres, témoin aléatoire, spread catalogue **et** spread réellement coté.
  Critères écrits avant : `research/FALSIFICATION.md` (horodatés 19:11).
- **Verdict** (`research/VERDICT.md`) : **ÉCHEC au sens des critères** — 0 cellule
  STRICT sur 12, cellule de ses réglages live à **−10,4 R hors échantillon**,
  percentile témoin 65, résultat plein échantillon porté à 301 % par la seule année
  2023. Ce n'est pas un échec par coût (8,9 % du R au spread mesuré, seuil 35 %).
- **Mais la fidélité est tenue** : 140 signaux/an contre 141 publiés, 20,9 % de
  réussite contre ≈ 23 %, 79 % de sorties au stop, gain moyen 3,94 R pour 1,02 R de
  perte moyenne (son journal : 370 € / 90 €). **Nous mesurons bien sa règle.** Le seuil
  de rentabilité, avec nos propres gains et pertes moyens, est à 20,5 % de réussite :
  tout se joue sur deux points de taux de réussite que nous n'avons pas sur cette
  période, chez ce courtier.

## Ce qui attend Adrian
| Sujet | Décision |
|---|---|
| **Contrainte « une position par symbole »** : elle retire 300 des 836 signaux (36 %). Son EA ne documente aucun plafond, et son nombre de trades publié (141/an) colle à notre nombre de **signaux** (140/an), pas à notre nombre de trades (89/an). Mesurer sans cette contrainte = un bras non déclaré, donc un nouveau dossier avec sa propre falsification | GO / pas GO, et priorité |
| **Période** : son test couvre 2015-2026, le nôtre commence en septembre 2020. Charger de l'or H1 antérieur (MT5 ou autre source) pour couvrir sa fenêtre | faisable ? vaut-il le coup ? |
| **Slippage à 0** dans tout le dépôt — une stratégie qui entre sur des bougies explosives est précisément celle où il mord le plus | renseigner une valeur avant toute décision de production |
| **Suite du corpus Balke** : Turnaround Tuesday (S023) et Go Long (S024) demandent des indices H1, désormais accessibles (MT5 en ligne) | ordre de priorité |

## Ce que S022 ne fait pas, et pourquoi
- Pas de réglage après lecture des résultats : la grille de 12 cellules est celle du
  manifeste, figée avant la mesure. `atr_period` (200) et `tp_pct` (2 %) ne sont pas
  balayés — ce sont ses valeurs dictées.
- Pas de filtres optionnels : ils sont désactivés dans son live.
- Pas de promotion : statut **BACKTESTED** = mesuré, et ici mesuré négatif. Aucun
  changement de statut sans décision d'Adrian (R10).
