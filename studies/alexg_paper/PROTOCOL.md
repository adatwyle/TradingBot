# PROTOCOLE — Essai à blanc « fxalexg assisté par IA » (détecteur v2 + juge headless)

> **Ce fichier est un scellé.** Il est écrit **avant** le premier signal mesuré.
> Il fixe la configuration, les bras, les falsifications chiffrées et la façon
> dont le verdict sera rendu. Toute conclusion future se lit contre ce qui est
> écrit ici, et nulle part ailleurs. Motif repris de
> `studies/macd_ai_paper/PROTOCOL.md` et `studies/gold_forward/PROTOCOL.md` —
> la valeur entière du dispositif tient à l'impossibilité de tricher
> rétroactivement.

**Date de scellement** : 2026-08-22
**Origine** : mandat Adrian, verbatim — *« pourquoi tu ne crée pas une stratégie
/ tu la dépose et tu la live test pendant 1-2 mois / une fois la v1 profitable
tu la passe en prod / et tu travaille sur son amélioration en V2 »*, puis
*« la partie technique est couverte par un algo / la partie décision humaine
est couverte par un claude code cyclique qui execute le skill d'analyse »*.
**Décision de lancer** : Adrian.

---

## 0. CE QUI EST DÉJÀ MESURÉ, ET CE QUI CHANGE ICI

Deux verdicts existent sur cette source et doivent être lus d'abord :

- `strategies/s01_fxalexg_swing/research/VERDICT.md` — **NON REPRODUCTIBLE**.
- `strategies/s93_alexg_ai_judge/research/VERDICT.md` — rejeu à l'aveugle de
  191 candidats par un juge appliquant la grille de notation d'Alex
  (1 confluence = 10 %). Seule cellule à effectif suffisant : **+0,222 R/trade,
  percentile 88,5** contre le témoin aléatoire — sous la barre de 95 déclarée
  d'avance. **Falsification centrale confirmée : échec.** Et F3 falsifiée :
  monter le seuil de grade **dégrade** le R/trade (+0,222 → −0,385 → −0,488).

**Ce qui change dans cet essai — trois différences, toutes factuelles :**

1. **L'univers était faux.** s93 déclarait GBPJPY/GBPCHF « indisponibles » et
   leur avait substitué GBPUSD/EURJPY. Vérification MT5 du 2026-08-22 :
   **les 26 paires de l'univers documenté de la source sont disponibles chez
   Swissquote** ; leur absence venait du catalogue `core/data/instruments.py`,
   pas du broker. Le catalogue a été complété (13 paires ajoutées, spreads
   mesurés sur 4000 barres H1, pip values relevées via MT5).
2. **La couche de sélection change de nature.** s93 mesurait une **grille à
   cases** (compter des confluences, seuiller le total). Cette grille est
   mesurée non discriminante — et sa distribution observée l'explique :
   `grade_core {0:15, 10:46, 20:51, 30:40, 40:28, 50:7, 60:4}`, aucun candidat
   au-dessus de 60 %, donc un seuil à 70 % ne prend rien. Ici le juge ne
   compte pas des cases : il **décide** (prendre / passer, et à quelle taille),
   sur le motif éprouvé de `macd_ai_paper`.
3. **C'est un forward prospectif**, pas un rejeu. Aucun signal historique
   n'entre au journal : l'essai commence à la pose du scellé.

**La question testée n'est donc PAS « la stratégie d'Alex G marche-t-elle »
(deux fois mesurée non), mais :**

> **Sur le flux de candidats du détecteur v2, tourné sur l'univers RÉEL de la
> source, une session Claude Code cyclique jouant l'analyste peut-elle
> sélectionner un sous-ensemble profitable ?**

Ce dispositif doit pouvoir rendre « non » honnêtement. C'est sa raison d'être.

## 0bis. LE PROBLÈME DE FRÉQUENCE — chiffré d'avance

Mesure du 2026-08-22, détecteur v2 sur les 26 paires, 2021-07 → 2026-08 :
**777 candidats en 5,1 ans = 2,94 candidats/semaine**, R/trade mécanique
**−0,2085** (n=777, coûts catalogue + 0,5 pip de slippage).

Conséquence arithmétique, écrite maintenant pour ne pas être négociée plus
tard :

| Durée de forward | Décisions IA attendues |
|---|---|
| 1 mois | ~13 |
| 2 mois | ~26 |
| 3,2 mois | ~40 — **seuil de verdict** |

**Un forward de 1-2 mois ne peut donc PAS rendre un verdict** ; il rend une
lecture intermédiaire. Le verdict tombe à N = 40 décisions, soit ~3,2 mois au
rythme mesuré. C'est un fait de fréquence, pas une réserve d'opinion.

## 0ter. CE QUI EST VOLONTAIREMENT HORS PÉRIMÈTRE V1

- **COT** : s93 n'obtenait sa seule cellule positive qu'avec le COT. Il est
  néanmoins écarté ici, sur la doctrine du dépôt lui-même
  (`core/data/cot.py`) : le positionnement d'une croisée est reconstitué par
  différence de deux jambes dollar, c'est **une hypothèse et non une mesure**,
  et le module exige qu'elle soit *« scellée dans une étude SÉPARÉE — sinon un
  résultat obtenu sur EURUSD contaminerait sa lecture »*. Branche V2.
- **Sélection de paires.** La mesure par paire montre des extrêmes (NZDJPY
  +1,01 R/t, AUDCHF −0,85 R/t). Sur 26 paires ces extrêmes sont **attendus par
  hasard** ; retenir les gagnantes serait le sur-ajustement que
  `docs/METHODOLOGY.md` interdit. **Les 26 paires tournent, sans exception.**
- **Réglage des niveaux par l'IA.** Bornes `sl_adjust` et `tp_adjust` figées à
  **[1,0 ; 1,0]** : la doctrine de la source est le *set and forget* avec stop
  structurel. Laisser l'IA resserrer les niveaux testerait autre chose que sa
  méthode. Le juge décide **prendre/passer et la taille**, rien d'autre.

---

## 1. Configuration FIGÉE

Source unique : `studies/alexg_paper/params.json`.

```
SHA-256(params.json) = 14c7f31b66eb754d2f40e76955c677115d5e0a762e546263fce694ebd542e9d3
```

Répliqué dans `PARAMS_SHA256` de `paper_step.py`. Refus de tourner si
divergence (**exit 3**).

| Élément | Valeur |
|---|---|
| Détecteur | `strategies/s93_alexg_ai_judge/strategy.py` **IMPORTÉ** — une seule implémentation du signal (R5). Chemin live : `on_bar`, R5 par construction |
| Instruments / TF | **26 paires** (univers documenté de la source : majors + croisées GBP/JPY/CHF/AUD/NZD/CAD) / **H1** |
| Coûts | spread médian mesuré sur 4000 barres H1 par paire + **0,5 pip de slippage**, demi-spread payé à chaque extrémité |
| Exécution | conventions du moteur commun répliquées : entrée au close du signal + coût ; stop unilatéral, gap payé à l'ouverture ; la cible ne profite pas du gap ; SL prime sur TP ; coût aussi en sortie ; une position par bras et par paire ; cooldown 2 barres ; circuit breaker 3 pertes → 24 barres |
| Compte virtuel | 10 000 par bras, risque de base 1 %/trade via `RiskLayer` |
| Juge | `claude -p --output-format json`, prompt par STDIN, timeout 180 s, UNE relance ; échec persistant → bras IA **N/A pour ce signal**, témoins jamais affectés |

**Aucun ordre n'est envoyé au broker.** Le compte MT5 connecté est un compte
RÉEL (Swissquote, `trade_mode=2`, relevé le 2026-08-22) : ce dispositif lit
des barres et ne place rien. L'exécution est simulée en Python, comme
`macd_ai_paper` et `gold_forward`.

## 2. LES QUATRE BRAS — journalisés à CHAQUE signal

| Bras | Rôle |
|---|---|
| **MECH** | le détecteur nu : prend tout signal quand il est flat. C'est la base à battre (−0,21 R/t mesuré historiquement) |
| **AI** | la session Claude Code headless décide prendre/passer + taille 0..1. Panne CLI → décision `na`, les témoins continuent |
| **RND** | prise aléatoire **au même taux que l'IA** (recalculé à la volée), graine 20260822, tirage déterministe par (graine, paire, barre) — rejouable |
| **SHADOW** | comptable, pas un compte : chaque signal ouvre une position contrefactuelle à configuration de base, sans blocage ni cooldown. Fournit le R par signal dont F1 et F2 ont besoin |

## 3. FALSIFICATIONS — déclarées AVANT la première décision

| # | Énoncé | Seuil | Conséquence si atteint |
|---|---|---|---|
| **F1** | La sélection IA ne bat pas des tirages aléatoires de même taux | n ≥ 40 décisions ; percentile **< 80** | **ÉCHEC** — le juge n'apporte rien. Entre 80 et 95 : **suggestif, non concluant** (c'est exactement où s93 s'est arrêté, à 88,5). **≥ 95** requis pour conclure à un apport |
| **F2** | Le socle mécanique perd même sans aucun coût | n ≥ 40 signaux shadow clos ; R cumulé **sans coût** < 0 | le détecteur est mort en lui-même ; seule la sélection peut sauver le dispositif |
| **F3** | La taille demandée par l'IA ne corrèle pas au résultat | n ≥ 40 ; corrélation de rang (taille, R) ≤ 0 | la modulation de taille est du rituel — à retirer en V2 |
| **F4** | Le taux de prise dérive vers les extrêmes | taux < 5 % ou > 95 % sur 40 décisions | le juge ne sélectionne pas, il approuve ou refuse en bloc — prompt à revoir |
| **F5** | Fréquence réalisée > 2 trades/semaine pour le bras IA | moyenne sur 8 semaines | le dispositif n'est plus la méthode de la source (1-2 trades/semaine documentés) |
| **TEMPS** | Moins de 40 décisions après 6 mois | — | **NON CONCLUSIF (données insuffisantes)** |

**La règle est écrite d'avance : si le percentile F1 ressort à 94, c'est un
échec.** Aucune renégociation du seuil après lecture des chiffres.

## 4. PROMOTION — ce qu'il faut pour passer en LIVE

R10 impose `RESEARCH → BACKTESTED → PAPER → LIVE`. Cet essai est le PAPER.
Passage en LIVE proposable **uniquement** si, cumulativement :

1. n ≥ 40 décisions IA closes ;
2. F1 percentile **≥ 95** ;
3. R/trade du bras IA **> 0** et **> celui du bras MECH** ;
4. F4 et F5 non atteintes ;
5. **décision d'Adrian** — jamais du runner, jamais de Claude.

Aucun de ces cinq points n'est négociable à la lecture des résultats.

## 5. INVARIANTS TECHNIQUES

1. **SCELLÉ** — SHA-256 de `params.json` vérifié avant toute action (exit 3).
2. **APPEND-ONLY** — journal à chaîne de hachage ; toute réécriture,
   troncature ou perte détectée → refus de tourner sans rien écrire (exit 4).
3. **IDEMPOTENT** — un curseur `last_bar_time` par paire ; deux passages sur
   les mêmes données n'ajoutent rien et **ne rappellent pas le juge**.

Codes de sortie (contrat commun de l'usine) : `0` passage effectué · `2` MT5
indisponible · `3` scellé violé · `4` journal altéré.

## 6. HISTORIQUE

| Date | Événement |
|---|---|
| 2026-08-22 | Scellement. Catalogue d'instruments complété (13 paires + EURGBP). Fréquence et base mécanique mesurées sur l'univers réel : 777 candidats, 2,94/sem, −0,2085 R/t. |
