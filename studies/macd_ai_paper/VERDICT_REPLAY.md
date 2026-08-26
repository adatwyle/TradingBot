# VERDICT — Rejeu à l'aveugle accéléré (couche 1 du protocole macd_ai_paper)

> Rendu APRÈS jugement des 400 dossiers, contre la falsification F1-rejeu
> déclarée dans `PROTOCOL.md` § 4 (committé avant le premier jugement).
> Date : 2026-08-17. Chiffres : `replay_measure.py` sur
> `C:\db\tbot\macd_ai_paper\replay\` (journaux des juges dans `judgments/`).

## Dispositif exécuté

- **Candidats** : cellule scellée s12 (`close_down=true, sl_atr=3`) sur MT5 D1
  SP500/NASDAQ/DAX 2016→2026 (165 signaux) + LONGHIST close-only SP500
  1927→2015 et NASDAQ 1971→2015 (2 217 signaux, coupés à 2016 — pas de
  recouvrement). Sous-échantillon déterministe **400 candidats** (graine
  20260816), outcomes indépendants au moteur commun (précédent s93).
- **Anonymisation motif s93** : id opaque, ordre mélangé, pas de dates, 60
  barres D1 en (prix−entrée)/ATR, stop/cible en ATR, mapping jamais montré.
- **Juges** : 16 sous-agents (25 dossiers chacun), prompt gestionnaire de
  risque identique à celui du runner temps réel (`ai_judge.py`), sortie
  take/skip + size + sl/tp_adjust dans les bornes.

## Les chiffres

| Mesure | Valeur | Effectif |
|---|---|---|
| Prendre-tout (net, base) | **−0,124 R/candidat** (−49,8 R) | 400 |
| Pris par l'IA | 228/400 (57 %) · **−0,065 R/pris** (−14,8 R) | 228 |
| Percentile groupé vs 1000 tirages même effectif | **95,6** | 400 |
| — MT5 seul | pris 22/25 (88 %) · +0,244 R/pris · percentile **77,6** [MINCE] | 25 |
| — LONGHIST seul | pris 206/375 (55 %) · −0,098 R/pris · percentile **89,3** | 375 |
| **Percentile STRATIFIÉ** (composition MT5/LONGHIST fixée, 2000 tirages — diagnostic post-hoc déclaré) | **90,0** | 400 |
| Sizing gradué | taille moyenne 0,52 · corrélation taille/R **+0,022** (nulle) | 228 |
| Resserrage SL/TP | 47 pris ajustés : base −6,2 R → ajusté **−10,0 R** (délta **−3,9 R**) | 47 |

## Verdict contre la falsification

**F1-rejeu (seuil de rejet < 80, seuil de signal ≥ 95)** : percentile groupé
95,6 — formellement au-dessus du seuil de signal. MAIS le diagnostic de
composition, obligatoire à déclarer, le désamorce :

1. **Fuite de composition** : le juge voit des barres o=h=l=c (LONGHIST
   close-only) vs des barres OHLC réelles (MT5). Il a pris 88 % du pool MT5
   (le meilleur pool : +0,22 R/candidat, marché 2016-2026 haussier) et 55 %
   du pool LONGHIST (−0,15). Une partie du « tri » est la reconnaissance du
   TYPE de dataset, pas de la qualité du trade. À composition fixée, le
   percentile tombe à **90,0** ; dans chaque strate isolée il est à 77,6 et
   89,3 — **aucune strate n'atteint 95**.
2. **Les pris restent perdants** : −0,065 R/pris, −14,8 R cumulés. La
   sélection réduit la perte de moitié, elle ne crée pas d'espérance
   positive. À la question du mandat — « les décisions de l'IA sont-elles
   dans l'ensemble profitables ? » — la réponse mesurée est **NON**.
3. **Le « management » IA détruit de la valeur** : les resserrements SL/TP
   demandés coûtent −3,9 R sur 47 trades ; la gradation de taille est
   décorrélée du résultat (+0,02). Seul le take/skip porte un semblant de
   signal — exactement le profil s93 (le grading fin est du rituel).

**Lecture honnête : signal de tri MINCE (90e percentile stratifié, même ordre
que les 88,5 de s93), sur un socle mort, avec des trades sélectionnés
toujours perdants.** Le même juge, deux flux différents, deux fois la même
conclusion : l'IA évite une partie des pires dossiers mais n'extrait pas
d'espérance positive d'un flux qui n'en a pas.

## Décision recommandée sur la couche 2 (runner temps réel)

**NE PAS ARMER sur s12.** Le protocole conditionnait l'armement à un signal
≥ 95 ; le 95,6 groupé ne survit pas au contrôle de composition (90,0
stratifié) et l'espérance des pris est négative — un an de forward
confirmerait au mieux « perdre moins que le témoin ». L'infrastructure
(runner 3 bras + journal scellé) reste prête et réutilisable telle quelle si
un socle VIVANT est un jour validé — c'est sur un flux à espérance ≥ 0 que la
question « l'IA ajoute-t-elle ? » vaudrait un forward.

## Limites

- Un seul sous-échantillon (400/2 382, graine figée) ; juges = 8-16 contextes
  frais mais même modèle — pas d'ensemble multi-modèles.
- LONGHIST close-only : outcomes approximés (dégradation déclarée) et barres
  plates reconnaissables (la fuite de composition mesurée ci-dessus).
- Le percentile stratifié est un diagnostic post-hoc (déclaré comme tel) ;
  la falsification formelle F1-rejeu portait sur le pool groupé.
