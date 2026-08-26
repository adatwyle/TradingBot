# Analyse — Legacy S2 Donchian + filtre de régime (Phase 1)

Source : projet TBOT 2026, code historique interne
Trader : TBOT interne (Adrian / itérations Claude antérieures)
Fichiers lus : `BacktestEngine_prototype/backtest_engine/backtest_engine/s2_breakout.py`,
`s2_breakout_filtered.py`, `indicators.py`

---

## 1. Nature de la source et crédibilité

Ce n'est pas un contenu externe : c'est **notre propre code**, écrit dans
l'architecture précédente du projet. Il n'y a donc ni claim marketing, ni track
record à confronter — mais il y a un piège spécifique, plus insidieux qu'un
influenceur YouTube : **on est enclin à croire ce qu'on a écrit soi-même**.

Trois faits documentés encadrent cette analyse, et ils sont tous défavorables :

| # | Fait | Conséquence |
|---|---|---|
| F1 | Le moteur historique (`fast_bt_multi`, même famille que `fast_bt_s2`) clôturait les positions résiduelles à `closes[-1]` — dernière barre du tableau **complet** — alors que sa boucle respectait `end_idx`. | **Tous les chiffres S2 antérieurs sont non fiables.** Aucun n'est cité ici. |
| F2 | Les seuils du filtre de régime (`ER < 0,11` / `failed_rate > 0,50`) ont été choisis **par inspection visuelle** des distributions gagnants/perdants. | Sur-ajustement probable. Traités ici comme des **paramètres de grille**, jamais comme des constantes. |
| F3 | Un test de sensibilité antérieur avait montré que **DAX ne passait qu'au point exact** (0,11 / 0,50). | Signature classique d'un pic isolé. C'est la question centrale du présent test. |

Le bug F1 est visible dans le code lu : `fast_bt_s2` clôture bien sur
`closes[loop_end - 1]` (correct), mais partageait le moteur de grille et les
conventions de la famille buguée — et surtout **aucun test d'invariant n'existait**
à l'époque. Rien ne permet de dire rétrospectivement quels résultats étaient sains.

**Posture retenue :** on re-dérive la logique, on la réécrit dans le contrat
actuel, et on la re-mesure de zéro. Le code historique sert de **spécification**,
pas de **preuve**.

---

## 2. La méthode, reformulée

S2 est un **suiveur de tendance par cassure de canal**, conçu comme complément
de S1 (retour à la moyenne). L'idée : S1 perd dans les marchés qui partent en
tendance ; S2 est censé y gagner.

Séquence, à chaque barre clôturée :

1. **Y a-t-il assez de volatilité ?** `ATR(14) > 0,8 x SMA50(ATR)`.
   Sans amplitude, une cassure ne va nulle part.
2. **Le marché est-il en tendance, et cette tendance se renforce-t-elle ?**
   `ADX(14) > 25` **et** `ADX(i) > ADX(i-5)`. La seconde condition est la plus
   discriminante : elle refuse les tendances qui s'essoufflent.
3. **Le prix casse-t-il le canal de Donchian ?**
   `close > max(high des 20 barres précédentes)` -> candidat LONG.
   `close < min(low des 20 barres précédentes)` -> candidat SHORT.
   Le canal est décalé d'une barre (`_prev`) : on compare à un extrême qui
   n'inclut pas la barre courante — sinon la condition serait triviale.
4. **La direction est-elle confirmée ?** `+DI > -DI` (long) / `-DI > +DI` (short).
5. **N'est-on pas déjà à l'extrême ?** `RSI < 75` (long) / `RSI > 25` (short).
6. **Sortie mécanique** : SL à `1,5 x ATR`, TP à `4,0 x ATR` (R:R 2,67).
   Set & forget.

Le **filtre de régime** (`s2_breakout_filtered.py`, mode `combo`) s'ajoute
par-dessus, **en amont** de tout le reste : il **interdit les nouvelles entrées**
(il ne ferme jamais une position ouverte) quand

```
ER200[i] < 0,11        OU        failed_rate200[i] > 0,50
```

avec :

* **ER200** = moyenne sur 200 barres du **ratio d'efficience de Kaufman** à 100
  barres. `ER100[i] = |close[i] - close[i-100]| / somme|delta close|` sur la même
  fenêtre. Vaut 1 pour une droite parfaite, ~0 pour un aller-retour.
  **Mesure : le marché va-t-il quelque part, ou tourne-t-il en rond ?**
* **failed_rate200** = proportion, sur les ~200 dernières cassures Donchian, de
  celles qui sont **revenues dans le canal en moins de 3 barres**.
  **Mesure : les cassures récentes ont-elles tenu ?**

L'intention est cohérente et se dit en une phrase : *ne pas trader des cassures
dans un marché qui ne va nulle part et où les cassures récentes ont échoué.*

---

## 3. Décomposition en composants

| # | Composant | Rôle | Paramètres historiques |
|---|---|---|---|
| C1 | Filtre de volatilité | éviter les cassures atones | `ATR > 0,8 x SMA50(ATR)` |
| C2 | Filtre de tendance | ne trader que dans un marché directionnel | `ADX > 25` |
| C3 | Filtre d'accélération | tendance qui se **renforce** | `ADX(i) > ADX(i-5)` |
| C4 | Déclencheur | cassure du canal Donchian décalé | `N = 20` |
| C5 | Confirmation directionnelle | croisement DI | `+DI > -DI` |
| C6 | Anti-extrême | ne pas acheter le sommet | `RSI < 75 / > 25` |
| C7 | Stop | invalidation | `1,5 x ATR` |
| C8 | Cible | objectif | `4,0 x ATR` |
| C9 | Trailing (optionnel) | SL au point mort après `+1,5 ATR` | désactivé par défaut |
| C10 | **Filtre de régime ER** | halte si marché non directionnel | `ER200 < 0,11` |
| C11 | **Filtre de régime cassures ratées** | halte si les cassures échouent | `failed_rate200 > 0,50` |
| C12 | Cooldown / circuit breaker | limiter les séries noires | 2 barres / 3 pertes -> 24 barres |

---

## 4. Tableau de reproductibilité

Données disponibles : barres OHLC MT5 Swissquote, `tick_volume`, `spread`.
`real_volume = 0`. Pas de carnet d'ordres.

| Composant | Reproductible ? | Note |
|---|---|---|
| C1 ATR + SMA(ATR) | **Oui, à l'identique** | prix seulement |
| C2 ADX | **Oui, à l'identique** | variante MT5 `iADX` reprise telle quelle depuis `indicators.py` (lissage EMA `alpha = 2/(p+1)`, buffers amorcés à 0) — pas la variante Wilder |
| C3 ADX croissant | **Oui, à l'identique** | |
| C4 Donchian décalé | **Oui, à l'identique** | |
| C5 +/-DI | **Oui, à l'identique** | même remarque que C2 |
| C6 RSI | **Oui, à l'identique** | Wilder, `ewm(alpha=1/14)` |
| C7 / C8 SL / TP ATR | **Oui** | |
| **C9 trailing / point mort** | **NON** | `core/backtest/engine.py` ne gère ni trailing ni déplacement de stop. R9 interdit d'écrire un moteur. **Composant abandonné** — c'était déjà l'option non-défaut. Limite assumée, section 8.1. |
| C10 ER | **Oui, à l'identique** | prix seulement |
| C11 failed_rate | **Oui, à l'identique** | prix seulement |
| C12 cooldown / CB | **Oui** | le moteur commun applique exactement `cooldown_bars=2`, `cb_losses=3`, `cb_cooldown_bars=24` — mêmes valeurs que l'historique |

**Aucun composant central n'est irréalisable.** Contrairement à une stratégie
d'orderflow, S2 ne consomme que des prix. C'est une re-dérivation **complète**,
pas un substitut dégradé.

---

## 5. Ce qui change par rapport au code historique (et pourquoi)

Ces écarts sont imposés par le contrat de la plateforme, pas par confort.

| # | Historique | Ici | Motif |
|---|---|---|---|
| E1 | La boucle décide *et* exécute (position ouverte gérée dans la même boucle) | La stratégie **émet des signaux**, `core/backtest/engine.py` exécute | R9. Effet de bord : un candidat émis pendant qu'une position est ouverte est **compté et rejeté** par le moteur (`skipped_open`) au lieu d'être ignoré silencieusement. Le jeu de trades réellement pris est équivalent. |
| E2 | Spread lu barre par barre (`spreads[i]/10`), fallback horaire x1,5 la nuit | Spread **fixe** issu de `core/data/instruments.py` | R7 : le catalogue est la seule source de vérité sur le broker. Le spread fixe est un peu plus optimiste la nuit, un peu plus pessimiste en séance. |
| E3 | Bruit d'exécution `NOISE x 0,15 x range` élargissant la zone de touche du stop | Aucun bruit — stop touché si `low <= stop <= high`, **et le SL l'emporte** si SL et TP sont dans la même barre | Le moteur commun est volontairement plus pessimiste. |
| E4 | PnL en devise, `size = capital x RISK / distance` | PnL en **R** | R2 : la stratégie ne dimensionne pas. |
| E5 | Résiduel clôturé à `closes[loop_end-1]` | Idem, garanti par le moteur commun + testé par R1 | F1. |
| E6 | `trailing` disponible | Retiré | Voir C9. |

---

## 6. L'hypothèse testable

Elle se décompose en deux affirmations **séparables**, et c'est volontaire :

> **H1 — le signal de cassure.** Une cassure de canal Donchian, filtrée par une
> tendance ADX **croissante**, un croisement DI cohérent et une volatilité
> supérieure à sa propre moyenne, a une espérance **positive après spread**,
> avec un stop à 1,5 ATR et une cible à 4 ATR.
>
> **H2 — le filtre de régime.** Suspendre les entrées quand `ER200 < seuil_ER`
> **ou** `failed_rate200 > seuil_FR` **améliore l'espérance par trade** — et
> cette amélioration **survit au déplacement des seuils**.

Deux précisions méthodologiques, fixées **avant** de voir le moindre chiffre :

1. **Le filtre se juge sur le R/trade, jamais sur le R total.** Un filtre retire
   des trades ; le total baisse mécaniquement. Seul le PnL par trade dit si on a
   retiré les *mauvais* trades.
2. **Critère de robustesse des seuils, fixé d'avance.** Le filtre n'est déclaré
   robuste que si l'amélioration du R/trade reste positive sur **la majorité du
   voisinage 3x3** autour de (0,11 ; 0,50) — c'est-à-dire pour
   `seuil_ER dans {0,09 ; 0,11 ; 0,13}` x `seuil_FR dans {0,45 ; 0,50 ; 0,55}`.
   **Si seul le point exact (0,11 ; 0,50) fonctionne, le filtre est déclaré
   sur-ajusté** — quel que soit son gain apparent. Ce critère est écrit ici pour
   qu'il ne puisse pas être réécrit après coup.

H1 et H2 sont indépendantes : H1 peut être fausse et H2 vraie (le filtre
améliorerait un signal perdant sans le rendre gagnant), et réciproquement. Les
deux sont mesurées séparément — c'est à ça que sert la valeur « filtre désactivé »
dans la grille.

---

## 7. Instruments, timeframe, grille

**Timeframe : H1**, celui du code historique. Rappel de méthodologie : le péage
du spread y coûte ~2,14 points de win rate, contre 1,04 en H4 et 0,46 en D1.
C'est le timeframe le plus hostile — c'est aussi celui qu'on doit tester si on
veut savoir ce que valait S2.

**Instruments (8)** — S2 visait « indices et forex tendanciels » :

| | |
|---|---|
| Indices | DAX, NASDAQ, SP500, FTSE, NIKKEI |
| Métal | XAUUSD |
| Forex | EURJPY, USDJPY |

DAX est retenu explicitement : c'est l'instrument sur lequel F3 signalait un pic
isolé. NIKKEI et FTSE apportent des régimes moins corrélés au complexe US.

**Grille — 128 configurations** (`128 x 0,05 = 6,4 réussites STRICT attendues
par pur hasard et par instrument` ; **51 sur 8 instruments**) :

| Paramètre | Valeurs | Rôle |
|---|---|---|
| `er_min` | **0,00** / 0,09 / **0,11** / 0,13 | seuil ER. `0,00` = **filtre ER désactivé** |
| `fr_max` | **1,00** / 0,45 / **0,50** / 0,55 | seuil cassures ratées. `1,00` = **filtre FR désactivé** |
| `donchian` | 20 / 40 | période du canal |
| `adx_min` | 20 / 25 | seuil de tendance |
| `tp_m` | 3,0 / 4,0 | cible en ATR |

`(er_min=0,00 ; fr_max=1,00)` est le **témoin sans filtre** : il teste H1 seule.
Les 3x3 cellules autour de (0,11 ; 0,50) testent H2 et sa robustesse.

Hors grille, fixés aux valeurs historiques pour ne pas gonfler l'espace de
recherche : `sl_m = 1,5`, `atr_vol_ratio = 0,8`, `adx_rising_lookback = 5`,
`rsi_long_max = 75`, `rsi_short_min = 25`.

**Warmup : 400 barres.** Contrainte dominante : ER100 lissé sur 200 (= 300), et
le taux de cassures ratées sur 200 cassures décalé de 4 barres (~210).

---

## 8. Causalité — les deux points sensibles

**ER200.** `ER100[i]` n'utilise que `close[i-100 ... i]`, la moyenne mobile 200
n'utilise que `ER100[i-199 ... i]`. Dépendance incluse dans `[0, i]`. Causal.

**failed_rate200 — le point à vérifier.** Le calcul de `fail[j]` regarde
**délibérément le futur de j** (`close[j+1 ... j+3]`) : c'est nécessaire, on ne
peut pas savoir qu'une cassure a échoué avant qu'elle échoue. La causalité tient
uniquement au **décalage d'agrégation** : à la barre `i`, la fenêtre s'arrête à
`j = i - horizon - 1 = i - 4`, dont l'évaluation n'a consommé que
`close[... i-1]`. Dépendance incluse dans `[0, i-1]`. **Causal** — mais par
construction fragile : supprimer ce décalage introduirait une fuite invisible.
Ce décalage est reproduit à l'identique et l'invariant R1 est rejoué **sur 16
points de la grille**, pas seulement sur le défaut.

### 8.1 Limites connues, annoncées avant les chiffres

1. **Le trailing / point mort n'est pas testé** (C9, R9). C'était l'option
   non-défaut de l'historique.
2. **Spread fixe** au lieu de barre par barre (E2).
3. **Un seul timeframe** (H1) et **un seul régime** (2021-2026).
4. **Pas de portefeuille** : instrument par instrument, une position à la fois.
5. **Slippage non modélisé** — ne peut qu'aggraver le résultat.
6. **R5 non exécutable** : `core/validation/conformance.py` n'existe pas dans le
   dépôt. Mitigation structurelle : `on_bar()` appelle littéralement
   `precompute()` + `generate_signals()` et ne garde que la décision de la barre
   courante. Il n'existe pas deux implémentations pouvant diverger.

---

## 9. Ce qui ferait conclure quoi (fixé d'avance)

| Observation | Verdict |
|---|---|
| Témoin sans filtre positif hors échantillon, et filtre robuste sur le voisinage 3x3 | `EDGE CONFIRMÉ` |
| Témoin sans filtre ~nul, filtre robuste et positif | edge **du filtre** — à isoler, promotion prudente |
| Filtre positif **au seul point (0,11 ; 0,50)** | **sur-ajustement confirmé** (F2/F3) — pas d'edge attribuable au filtre |
| STRICT <= hasard sur l'ensemble, R/trade négatif partout | `PAS D'EDGE` |
| Effectifs < 20 trades hors échantillon | `NON CONCLUSIF` sur l'instrument concerné |
