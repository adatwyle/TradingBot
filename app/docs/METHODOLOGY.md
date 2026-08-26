# RobinBot — Méthodologie de recherche

> **Document de référence commun.** Chaque Claude de stratégie doit l'avoir lu
> avant d'écrire une ligne de code. C'est un outil partagé, au même titre que le
> backtester : personne ne réinvente sa propre méthode.

Deux sources l'alimentent :
1. **Nos propres erreurs**, chacune payée en heures de calcul et en faux espoirs
2. La méthode publiée par **AI Pathways** (*How To Actually Find A Profitable
   Strategy With Claude*), dont plusieurs points nous étaient supérieurs

---

## 0. Les deux seules questions qui comptent

Trouver une stratégie qui *semble* profitable est facile. On peut en produire dix
backtests flatteurs en une heure. La difficulté est de trouver celles qui méritent
d'être exécutées, et ça se réduit à deux exigences :

1. **Battre l'effort zéro** — c'est-à-dire acheter et conserver l'indice
2. **Le faire à travers des régimes de marché différents**

Une stratégie qui gagne sur 2021-2026 mais n'a jamais vu de krach n'a rien prouvé.

---

## 1. Avant de coder — les trois vérifications

| # | Vérification | Question à se poser |
|---|--------------|---------------------|
| 1 | **Ancienne, simple, publiée** | Existe-t-il des décennies de recherche dessus ? Une idée neuve et compliquée est presque toujours un sur-ajustement déguisé |
| 2 | **Une vraie raison de payer** | **Qui perd de l'argent, et pourquoi ?** Si personne n'est structurellement de l'autre côté, il n'y a pas d'edge, juste un motif |
| 3 | **Adaptée à l'actif** | L'or tend, les indices reviennent à la moyenne. Une stratégie de tendance sur un actif qui oscille échouera quelle que soit la qualité du code |

La question 2 est la plus discriminante. Formuler explicitement *qui paie* élimine
la majorité des idées avant même l'implémentation.

---

## 2. L'économie du trade — à calculer AVANT d'implémenter

**Notre ajout à la méthode**, né d'un échec coûteux.

Le spread est un coût **fixe** par trade ; la taille du mouvement visé dépend du
timeframe. Le rapport des deux détermine si une stratégie peut seulement exister.

```
drag       = spread / (sl_atr × ATR)
pénalité_WR = drag / (1 + rr)        exprimée en POINTS de win rate
seuil_WR    = 1 / (1 + rr)
```

Valeurs mesurées sur nos instruments :

| Timeframe | Drag médian | Pénalité en points de WR |
|-----------|-------------|--------------------------|
| H1 | 8,57 % | **2,14** |
| H4 | 4,18 % | 1,04 |
| D1 | 1,85 % | 0,46 |

**Le cas d'école** : S5 affichait 27-28 % de réussite pour un seuil de rentabilité
à 25 % — soit 2-3 points de marge brute. Le péage H1 en consommait 2,14. La
stratégie ne pouvait pas être rentable sur H1, **quelle que soit la qualité du
signal**. Des semaines de calcul auraient été économisées par ce calcul de dix
lignes.

`core/data/source.py::spread_cost_analysis()` le fait pour vous.

> **Règle : si la marge attendue est inférieure au péage, reconcevez. Ne codez pas.**

---

## 3. Les trois règles de test

### 3.1 Causalité stricte — R1

Une stratégie ne peut jamais utiliser une information postérieure à la barre
qu'elle traite. Vérifié **mécaniquement**, pas déclaré :

```
generate_signals(precompute(df),     p, T)
    ==
generate_signals(precompute(df[:T]), p, T)      pour tout T
```

`python -m core.validation.causality --strategy <id> --save`

**Pourquoi ce n'est pas une formalité** : `fast_bt_multi` clôturait les positions
résiduelles à `closes[-1]` — dernière barre du tableau **complet** — alors que sa
boucle respectait `end_idx`. Chaque tranche d'entraînement valorisait son trade
ouvert à un prix futur. Des mois de walk-forward contaminés, sans jamais lever
d'alerte.

Pire : l'auto-test montre que la fuite ne se manifestait qu'à **une coupure sur
quatre**. Ailleurs, un `max()` masquait l'écart par hasard. **Ces bugs échouent
par intermittence** — c'est pour ça qu'on teste quatre coupures.

### 3.2 Coûts toujours actifs

Spread aux deux extrémités, et le modèle d'exécution reste pessimiste : stop
touché dès que le prix le traverse dans la barre, et **stop prioritaire sur cible**
quand les deux tombent dans la même barre — on ignore l'ordre de visite.

*Non modélisés à ce jour, à garder en tête : slippage, spread variable sur news,
swap sur positions multi-jours, gaps de week-end.*

### 3.3 Hors échantillon

Walk-forward ancré, 4 fenêtres (60/70/80/90 %). L'entraînement part toujours de
zéro — c'est la situation réelle d'un trader qui accumule de l'historique.

---

## 4. Les trois filtres de survie

Survivre à la fenêtre de test ne suffit pas.

| Filtre | Ce qu'il élimine |
|--------|------------------|
| **Stress sur une autre époque** | Les stratégies qui n'ont jamais vu de crise. *Notre limite actuelle : 5 ans de données, un seul régime. C'est notre faiblesse méthodologique n°1.* |
| **Cohérence de famille** | Les combinaisons chanceuses. Tout le voisinage de réglages doit fonctionner |
| **Test de plateau** | Le curve-fitting. On ne fait confiance à un réglage optimisé que si la performance est **lisse** autour, et si le classement sur train correspond à celui sur test |

---

## 5. Les deux diagnostics maison

Inventés en cours de route, désormais obligatoires.

### 5.1 Ablation du spread

```python
spec_gratuit = dataclasses.replace(spec, spread_pips=0.0)
```

Rejouer les mêmes signaux à coût nul. Ça sépare deux diagnostics qui appellent des
décisions **opposées** :

- Négatif avec spread, **positif sans** → il y a un edge, mangé par les coûts.
  Piste : timeframe supérieur, courtier moins cher, cibles plus lointaines.
- Négatif dans les deux cas → **il n'y a pas d'edge**. Rien à sauver.

Sur s01 : −0,1028 R/trade réel contre −0,0082 à coût nul. Le signal était
indiscernable d'une pièce. Aucun changement d'exécution ne l'aurait sauvé.

### 5.2 Contrôle long/short

La période 2021-2026 contient de fortes tendances directionnelles. Elles
fabriquent de faux edges.

Sur s01/USDJPY : **+69,7 R du côté long contre −10,0 R du côté short** sur cinq ans
de hausse du dollar-yen. Ça passait pour un système ; c'était un pari directionnel.

> **Découpez toujours la performance par sens.** Si un seul côté porte le
> résultat, vous avez mesuré une tendance, pas une stratégie.

---

## 6. Discipline statistique

| Règle | Le cas qui l'a imposée |
|-------|------------------------|
| **Toujours reporter l'effectif** | Un « strict pass » sur 19 trades a été pris pour un succès. IC 95 % du taux de réussite : **[27,3 % ; 68,3 %]**, seuil de rentabilité 28,6 % — **dedans**. Indistinguable du hasard |
| **Comparer au hasard** | Une grille de N configurations produit **≈ N × 0,05** réussites par pur hasard. 10 passes sur 144 ne prouvent rien. `anchored_wf` affiche cette attente |
| **Se méfier de la moyenne OOS seule** | Une cellule à +10,44 R de moyenne OOS faisait **−36,7 R** en plein échantillon |
| **Traquer la concentration** | Un book dont 93 % du résultat vient d'un instrument n'est pas un système, c'est un pari |
| **Ne jamais juger un filtre sur le PnL total** | Retirer des trades baisse le total mécaniquement. Seul le **PnL par trade** dit si on a retiré les *mauvais* trades |

---

## 7. Portefeuille

**Le seul effet robuste que ce projet ait mesuré.** Corrélation moyenne +0,005
entre instruments ; drawdown portefeuille 8,9 % contre 28,7 % pour la pire paire
seule.

**Résultat contre-intuitif à retenir** : la construction **naïve équipondérée bat
la sélection optimisée** en hors-échantillon (+3374 contre +939 en agrégé). Le
glouton concentre sur peu de noms en maximisant le Sharpe du *train*, qui ne
prédit pas celui du *test* — et détruit au passage la diversification.

C'est le résultat classique de DeMiguel, Garlappi & Uppal (2009), redécouvert
empiriquement sur nos données. **Ne construisez pas d'optimiseur de portefeuille.**

Toute la valeur vient du **filtre d'admission** :
`PnL > 0`, `DD < 40 %`, `≥ 20 trades` — calculés sur le train uniquement.

---

## 8. Décroissance de l'edge

Un edge trouvé finit par disparaître : il se fait connaître, il est arbitré.
Toute stratégie est temporaire ; **c'est le processus qui est durable**.

D'où les règles d'arrêt, écrites **avant** la mise en production :
- Halte si la performance glissante passe sous ce que produirait une entrée
  aléatoire
- Halte si le drawdown dépasse le pire drawdown backtesté

Implémenté dans `core/risk/` et tracé dans `risk_events`.

---

## 9. Ce qu'on sait de nos propres limites

| Limite | État |
|--------|------|
| **Un seul régime macro** (2021-2026) | Le plus grave. Pas de krach dans l'échantillon |
| Profondeur M5 : ~16 mois | Limite serveur Swissquote (~100 000 barres/symbole). Stratégies M5 non validables |
| Pas de volume réel (`real_volume = 0`) | Orderflow, footprint, delta bid/ask : impossibles |
| Pas de données options | GEX, IV, Greeks : impossibles |
| Slippage et swap non modélisés | Les résultats sont optimistes d'un montant inconnu |
| Folds emboîtés | Les résultats OOS ne sont pas indépendants ; n < 3 en pratique |

**Ambiguïté intra-barre : mesurée à 0,3 %** — négligeable pour des stops à
1,5-2 ATR. Le modèle barre H1 est sain sur ce point précis.

---

## 10. Le calibre externe — ce que font réellement les meilleurs

Deux places de marché publient des track records **vérifiés** de traders réels
sur plusieurs années : Darwinex (notation des gérants) et SignalStart (comptes
de signaux audités). Constat stable des deux côtés : les comptes les mieux
notés et les plus anciens — 2 à 4 ans de vie — tournent à **2-3 % par mois
avec un drawdown maximal ≤ 15 %**. Les comptes qui affichent 10-30 % mensuels
ne tiennent presque jamais plus d'un an.

Usage : c'est notre borne de vraisemblance. Toute stratégie, la nôtre ou celle
d'une source, qui promet durablement plus de ~3 % par mois est soit
extraordinaire (à prouver par un forward-test scellé), soit en route vers le
compte vide, soit un argument de vente. Et c'est aussi la référence de
communication : sur 1 000 CHF, l'excellence mondiale vérifiée, c'est 20 à
30 CHF par mois. Quiconque trouve ça décevant cherche autre chose que du
trading. Source archivée : `docs/sources/misc/tradingbots_55k_darwinex_signalstart.txt`.

## 11. La posture

**Aucun préjugé au départ.** Lire, comprendre, construire le meilleur cas possible
pour la méthode étudiée, implémenter fidèlement, backtester intégralement — et
**seulement ensuite** juger, sur ses propres chiffres.

Un verdict rendu avant les données n'a aucune valeur, dans un sens comme dans
l'autre.

**Mais une fois les chiffres obtenus, honnêteté totale.** Un résultat négatif
proprement établi est un livrable de pleine valeur — il économise du capital réel.
Ne maquillez jamais un échec. Ne cherchez jamais la configuration qui « sauve » un
résultat décevant.

> Vous n'êtes pas payé pour trouver une stratégie qui marche.
> Vous êtes payé pour **savoir** si elle marche.
> Les deux réponses ont de la valeur ; une seule des deux coûte de l'argent réel
> si elle est fausse.
