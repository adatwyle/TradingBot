# input-adrian — S018 or v2 (méthode Doud)

*Maintenu par cc-support. Réécrit en place, pas d'historique — git porte la traçabilité.*

## Identité
- **Numéro** : S018 · magic `130018`
- **Source** : deux podcasts MoneyTalk apportés par Adrian le 2026-09-06 — `docs/sources/moneytalk/`
- **Lignée** : v2 du résidu or de `S011_legacy_breakout` v1.0.0. La v1 reste en mesure, scellée, dans `studies/gold_forward/`.

## Ce qu'Adrian a demandé

Verbatim (2026-09-06) : *« j'ai deux nouvelles vidéos youtube à analyser […] ensuite tu analyses les stratégies en cours de développement et tu les renforces avec ces inputs aux endroits que tu identifies comme nécessaires — typiquement le gold forward peut certainement être amélioré […] analyse vraiment ce qu'elle dit, reproduis sa méthode, et renforce notre stratégie gold forward avec ce contenu. »*

Puis, après constat que le forward or est scellé : *« la v1 est en cours de validation → nous allons la laisser. La v2 c'est typiquement ce type de sujet → on fait une branche // v2 et on développe puis on met en test. »* Arbitrage suivant : **nouvelle stratégie S018, worktree séparé**.

## Principe

Le signal de cassure Donchian de la v1, augmenté de cinq lectures issues de la méthode de Cindy « Doud Trading » (scalpeuse XAUUSD) : biais directionnel préalable, longs seuls, canal sur les corps plutôt que sur les mèches, entrée au retour à l'équilibre (50 % de la jambe) plutôt qu'à la cassure, et fenêtres de session US + asiatique en excluant Londres. XAUUSD H1, moteur commun, stop ATR obligatoire.

## État hérité de la v1

`S011/research/VERDICT.md` § 2.5 — sous-verdict XAUUSD : **`NON CONCLUSIF`**. Meilleure cellule hors échantillon, filtre de régime désactivé, plein échantillon : **400 trades, +90,4 R, +0,226 R/trade**, win rate 34,2 %, profit factor 1,34, DD max 16,3 R, 0 trade fantôme, voisinage 9/9 positif. Réserve principale : **62 % du résultat vient de la seule année 2025** (hors 2025 : +34,4 R sur 304 trades). Contrôle directionnel : LONG +0,318 (231 tr) **et** SHORT +0,100 (169 tr).

Ce dernier chiffre compte pour la v2 : la source affirme qu'on n'achète l'or que dans un sens (D1), là où notre propre mesure v1 trouve le côté short positif. L'hypothèse est donc **testable et non triviale** — elle peut parfaitement être fausse chez nous.

## Attentes d'Adrian

- Reprise sans préavis (décision D2, 2026-08-23) : évaluer, tenter des chemins d'amélioration, ne pas s'arrêter à un verdict antérieur.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver, par constat propre du CC, documenté.
- **La v1 scellée n'est jamais touchée.** Elle est le témoin de la v2.
- Promotion PAPER/LIVE = décision Adrian uniquement (R10).

## Ce qui n'a pas été repris de la source, et pourquoi

Sorties partielles TP1/TP2/TP3, stop suiveur, break-even qui finance les frais : le moteur commun ne déplace pas de stop et R9 interdit d'en écrire un autre — tickets `TCK-014` (sorties partielles + trailing) et `TCK-016` (calendrier économique) ouverts vers cc-spec. Absence de stop et renforcement à la baisse : refusés par R3, et la source chiffre elle-même le coût de cette règle à −80 000 € en une séance.
