# Analyse — FXAlexG Swing HTF (Phase 1)

Source : https://www.youtube.com/@fxalexg__
Trader : fxalexg (~1,3 M abonnés)
Rédigé : 2026-08-16

---

## 1. Source et crédibilité

| Élément | État vérifiable |
|---|---|
| Audience | ~1,3 M abonnés YouTube — mesurable, mais **ne dit rien sur la performance** |
| Track record audité | **Aucun** trouvé. Pas de compétition auditée, pas de relevé broker vérifié par tiers |
| Claims chiffrés | Le transcript ne donne **ni win rate, ni R:R, ni drawdown**. Il décrit une *approche*, pas une performance |
| Nature du contenu | Pédagogique / narratif. Descriptions de trades a posteriori sur graphiques |

**Conséquence méthodologique.** Il n'y a pas de chiffre annoncé à réfuter. Le
test ne peut donc pas être « la source dit 70 % de WR, on mesure X ». Il porte
sur la **thèse** : *« la structure de marché lue sur timeframe élevé, jouée en
retracement, avec des détentions de plusieurs jours, produit un edge »*.
C'est cette proposition-là qui est testable.

C'est aussi ce qui rend le verdict plus délicat : on ne pourra pas conclure
« il a menti », seulement « la règle mécanique la plus fidèle que nous savons
écrire produit / ne produit pas d'edge sur nos données ».

---

## 2. La méthode reformulée

Dans mes mots, à partir du transcript :

1. **On établit d'abord la direction sur un timeframe élevé.** Analogie du bloc
   de béton : une structure qui met 30 jours à se former est plus solide qu'une
   structure de 24 h. Donc la lecture directionnelle se fait en haut, pas en bas.
2. **La direction se lit en structure de marché**, pas en indicateur : suite de
   *higher high / higher low* = haussier ; bascule en *lower low / lower high* =
   baissier. Le moment charnière est le **basculement de structure**.
3. **On n'entre jamais en chasse.** Un marché ne tombe pas en ligne droite ; il
   doit produire des retracements pour continuer. Donc après un *lower low*, on
   **anticipe le lower high** et on entre dessus.
4. **Top-down** : la direction vient du TF élevé, l'**entrée** se cherche sur un
   TF inférieur.
5. **Set & forget.** Une fois en position : stop et cible placés, on ne touche
   plus. Détentions annoncées de 5, 6, 7 jours, parfois plus.
6. **Sélectivité.** « Une à deux transactions par jour maximum », pas de chasse
   aux mouvements impulsifs.
7. **Pas de remise en cause de la direction** en cours de trade, précisément
   parce qu'elle vient du TF élevé.

---

## 3. Décomposition en composants

| # | Composant | Rôle dans la méthode |
|---|---|---|
| C1 | Détection de swings (points pivots) | Matière première de la structure |
| C2 | Classification de structure HH/HL vs LL/LH | Filtre directionnel |
| C3 | Détection du basculement de structure | Autorise le retournement de biais |
| C4 | Zone de retracement de la jambe d'impulsion | Où l'on a le droit d'entrer |
| C5 | Déclencheur d'entrée sur TF inférieur (le *lower high* / *higher low* qui se confirme) | Timing |
| C6 | Stop d'invalidation | Au-delà du swing d'entrée |
| C7 | Cible | Objectif fixe (set & forget) |
| C8 | Durée de détention longue (5-7 j) | Conséquence des points précédents |
| C9 | Sélectivité | Une entrée par jambe |

---

## 4. Tableau de reproductibilité

Données disponibles : barres OHLC MT5 Swissquote, `tick_volume` (changements de
cotation, **pas** un volume de contrats), `spread`. `real_volume = 0`.
Pas de carnet d'ordres, pas de delta bid/ask, pas d'options.

| # | Reproductible ? | Traduction opérationnelle retenue | Dégradation assumée |
|---|---|---|---|
| C1 | **Oui** | Fractal de Williams : swing haut en `j` si `high[j] = max(high[j-k .. j+k])`. **Confirmé seulement en `j+k`** — c'est ce qui rend la règle causale. | Un swing n'existe pour nous que `k` barres après son sommet réel. C'est aussi vrai pour un humain qui trade en direct : on ne sait pas qu'un sommet est un sommet avant qu'il tienne. Dégradation faible, et honnête. |
| C2 | **Oui** | Biais haussier si les **deux derniers** swings hauts sont croissants ET les deux derniers swings bas croissants. Baissier si les deux décroissants. Sinon neutre → pas de trade. | Il lit un graphique, avec du jugement. Nous imposons une règle binaire. C'est la substitution la plus lourde de tout le projet (cf. §6). |
| C3 | **Oui, implicitement** | Le basculement n'est pas codé séparément : il *est* le passage de l'état C2 de haussier à baissier. | Aucune, sinon que le basculement est daté à la confirmation du swing, pas au moment où l'oeil le voit. |
| C4 | **Oui** | Jambe = du dernier swing haut HTF confirmé `H` au dernier swing bas HTF confirmé `L`. Zone de retracement short = `[L + rmin*(H-L), L + rmax*(H-L)]`. | Il ne cite pas de niveaux de Fibonacci explicitement ; « retracement » est qualitatif. `rmin/rmax` sont notre traduction — mis en paramètres et testés. |
| C5 | **Oui** | Sur le TF d'entrée (H1) : fractal haut confirmé **à l'intérieur de la zone**, alors que le biais HTF est baissier. Entrée au close de la barre de confirmation. | C'est exactement « anticiper le lower high » : on entre quand le LH se confirme, pas quand on l'espère. |
| C6 | **Oui** | Stop au-dessus du swing d'entrée + `buf x` ATR(14, H1). | Aucune. Conforme R3. |
| C7 | **Oui** | Cible = `rr x` la distance de risque. | Il ne donne pas de R:R chiffré. `rr` est paramétré. |
| C8 | **Oui, par construction** | Aucune sortie temporelle. La position vit jusqu'au SL ou au TP. Avec un risque ancré sur un swing HTF, les détentions sortent naturellement en jours. **Vérifié a posteriori** (`bars_held` mesuré, cf. VERDICT). | Aucune. |
| C9 | **Oui** | Une seule entrée par jambe `(H, L)`. Plus la contrainte du moteur : une position à la fois, cooldown 2 barres. | Aucune. |
| — | **Non applicable** | Rien dans cette méthode n'exige du volume réel, du carnet d'ordres ou du footprint. | **C'est le point fort de cette source** : contrairement à une méthode orderflow, elle est intégralement reproductible avec des barres OHLC. |

**Verdict de reproductibilité : aucun composant central n'est irréalisable.**
Pas de mur de données. C'est rare et ça mérite d'être noté avant de juger le
résultat : si ça échoue, ce ne sera pas faute de données.

---

## 5. Choix des timeframes — et pourquoi cette tentative diffère de « S5 »

Une tentative antérieure du projet (« S5 ») a implémenté une logique de
structure voisine et échoué (0/7 en strict). Elle était **mono-timeframe H1 et
sans notion de durée de détention**. Ce n'était donc pas une reproduction de
cette méthode-ci : elle en retirait les deux points que la source martèle.

Ce qui est corrigé ici :

| Exigence de la source | S5 | Cette implémentation |
|---|---|---|
| Hiérarchie de TF | absente (H1 seul) | structure sur **H4 ou D1**, entrée sur **H1** — paramétré, les deux testés |
| Détention longue | non modélisée | aucune sortie temporelle ; risque ancré sur swing HTF donc détentions en jours, **mesurées** |
| Entrée sur retracement | partielle | zone de retracement obligatoire, pas d'entrée hors zone |
| Sélectivité | non | une entrée par jambe + une position à la fois |

**Pourquoi H1 en exécution et non H4/D1.** L'exécution sur H1 donne au moteur
la granularité la plus fine dont nous disposons pour savoir *quand* le stop est
touché — donc le chiffre le plus pessimiste et le plus honnête. Placer
l'exécution en D1 masquerait des stops touchés en intraday.
Les barres H4/D1 utilisées pour la structure sont **rééchantillonnées depuis les
mêmes H1**, ce qui garantit qu'aucun désalignement de fuseau ou de calendrier
n'introduit d'information que le moteur n'aurait pas.

**Péage du spread, mesuré (`spread_cost_analysis`, hypothèse risque = 2xATR) :**

| | EURUSD | USDJPY | USDCHF | AUDUSD | USDCAD | EURJPY | XAUUSD |
|---|---|---|---|---|---|---|---|
| H1 (pts de WR) | 2,47 | 2,27 | 3,20 | 2,87 | **3,82** | 2,68 | 0,74 |
| H4 | 1,20 | 1,06 | 1,55 | 1,40 | 1,86 | 1,30 | 0,37 |
| D1 | 0,50 | 0,45 | 0,67 | 0,81 | 0,56 | 0,56 | 0,14 |

ATTENTION : ces chiffres supposent un risque de 2xATR(H1). **Notre risque réel
est ancré sur un swing, donc plus large** — le péage effectif sera plus faible.
Il est **remesuré sur la distance de risque réellement observée** et reporté
dans le VERDICT. Ne pas utiliser le tableau ci-dessus comme conclusion.

Seuil de rentabilité : 33,3 % de réussite à `rr = 2`, 25 % à `rr = 3`.

---

## 6. Ce qui est substitué, et l'honnêteté sur la dégradation

1. **Le jugement visuel devient une règle binaire.** C'est la substitution
   majeure. Un trader lit « la structure est cassée » avec du contexte (vitesse
   du mouvement, qualité de la bougie, niveau plus large). Nous réduisons ça à
   « les deux derniers swings fractals vont dans le même sens ». Si la méthode
   a un edge qui vit *dans le jugement* et pas dans la règle, notre test le
   manquera. **C'est la limite fondamentale de tout ce travail** et elle doit
   figurer dans le verdict, quel qu'il soit.
2. **« Une à deux transactions par jour »** : nous produirons beaucoup moins.
   Lui suit un panier d'instruments simultanément ; nous testons instrument par
   instrument, une position à la fois. Ce n'est pas une infidélité, c'est un
   changement d'unité d'observation.
3. **Le retracement chiffré.** `rmin/rmax` en Fibonacci sont notre invention.
   Mis en grille plutôt que devinés.
4. **Aucun contexte fondamental / macro.** La source ne l'invoque pas, donc
   pas de dégradation ici.

---

## 7. Hypothèse testable

> **H0 (à réfuter)** — Une entrée prise dans le sens d'une structure de marché
> HH/HL ou LL/LH lue sur H4 ou D1, déclenchée par la confirmation d'un swing
> contraire (lower high / higher low) situé dans la zone de retracement de la
> dernière jambe d'impulsion, avec stop au-delà de ce swing et cible à un
> multiple fixe du risque, n'a **pas** d'espérance positive nette de spread.

> **H1** — Elle en a une, et cet edge :
> - survit hors échantillon sur les 4 fenêtres du walk-forward ancré,
> - dépasse le nombre de réussites attendues par pur hasard (~5 % des configs),
> - survit au déplacement de configuration (le voisinage de la cellule optimale
>   marche aussi),
> - n'est pas porté à plus de 80 % par un seul instrument,
> - repose sur un effectif suffisant (>= 20 trades hors échantillon par
>   instrument ; en dessous, `NON CONCLUSIF` est la seule réponse honnête).

**Prédiction accessoire, vérifiable indépendamment du résultat financier** : si
l'implémentation est fidèle, la **durée médiane de détention doit tomber dans
l'ordre de grandeur annoncé (5-7 jours, soit 120-170 barres H1)**. Si elle en
est loin, l'implémentation ne reproduit pas la méthode, et le verdict devra
être `NON REPRODUCTIBLE` plutôt qu'un jugement sur l'edge.

---

## 8. Grille de paramètres — et pourquoi elle est petite

96 configurations. Une grille de 96 produit **~5 « réussites » par pur hasard**
si l'edge est nul. C'est le nombre auquel tout résultat sera comparé.

| Paramètre | Valeurs | Justification |
|---|---|---|
| `htf` | H4, D1 | Les deux lectures « timeframe élevé » plausibles |
| `k_htf` | 2, 3 | Sensibilité du fractal HTF |
| `k_ltf` | 2, 3 | Sensibilité du fractal d'entrée H1 |
| `retr_min` | 0.382, 0.5 | Bord bas de la zone de retracement |
| `retr_max` | 0.786, 1.0 | Bord haut (1.0 = jusqu'au swing précédent) |
| `rr` | 1.5, 2.0, 3.0 | Aucun R:R n'est annoncé par la source |
| `sl_buf_atr` | 0.5 | **Fixé**, pas mis en grille — pas d'inflation de la grille sur un paramètre de confort |

2 x 2 x 2 x 2 x 2 x 3 = **96**.

---

## 9. Ce qui reste hors du test

- Le panier multi-instruments simultané qu'il trade réellement.
- Le jugement discrétionnaire (§6.1).
- Le slippage (le moteur ne le modélise pas — limite connue de la plateforme).
- Les nouvelles / le calendrier macro.
- `core/validation/conformance.py` n'existe pas dans le dépôt à ce jour : R5 ne
  peut pas être exécuté. `on_bar()` est néanmoins implémenté en réutilisant
  exactement le même code que `generate_signals()` (mêmes fonctions, même
  chemin), ce qui rend la divergence structurellement impossible.
