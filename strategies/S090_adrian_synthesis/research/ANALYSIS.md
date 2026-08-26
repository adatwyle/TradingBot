# Analyse — Stratégie Adrian (synthèse) : le « fade de l'échec »

Source : synthèse des VERDICT.md validés du projet (pas une source externe).
Trader : Adrian Daetwyler.
Protocole d'instruction : `research/HYPOTHESIS.md` (figé 2026-08-17 avant tout backtest).

## 1. La source et sa crédibilité

Contrairement aux dossiers s01-s12/s91-s93, la « source » est ici **notre
propre corpus de mesures** : quatre dossiers indépendants, chacun avec R1
passé, coûts réels, témoins appariés et effectifs publiés. C'est la source la
plus crédible dont le projet dispose — et aussi la plus dangereuse, parce que
c'est NOUS qui l'avons sélectionnée : le risque n'est pas le marketing, c'est
la sélection rétrospective. L'instruction est construite autour de ce risque
(univers hors découverte, témoin conditionné, multi-graines).

Les quatre apparitions et leurs chiffres exacts : HYPOTHESIS.md §0.

## 2. La méthode reformulée (dans mes termes)

Dans une tendance H1 (SuperTrend 10/3.0, ADX14 > 20), on suit le pullback
contre la tendance depuis l'extrême de la jambe. Tant que la tendance n'a pas
flippé, un pullback qui atteint 3 ATR ou plus est une sur-extension : la fin
du mouvement est du flux forcé, pas de l'information. On entre au close dans
le sens de la tendance à chaque palier entier d'ATR au-delà du seuil (une
fois par palier et par jambe), stop à 1-2 ATR, cible à 1 ATR — on encaisse la
rétraction partielle, pas un retournement.

## 3. Décomposition en composants

| Composant | Définition | Origine |
|---|---|---|
| Filtre de tendance | SuperTrend(10, 3.0) H1 | étude grid (figé) |
| Gate de force | ADX(14) H1 > 20 | étude grid (figé) |
| Ancre / excursion | extrême de jambe depuis flip, X = ancre − close | étude grid (figé) |
| Déclencheur | palier entier k × 1,0 ATR, k ≥ threshold ∈ {2,3,4} | seuil 3 = mesure n°4 ; 2/4 = dose-réponse H90 |
| Stop | 1,0 ou 2,0 ATR | RR honnête (G2 mesuré) + voisin |
| Cible | 1,0 ATR | rétraction partielle H90 (figé) |
| Sortie temporelle | aucune | comme mesuré |
| Sessions/filtres | aucun | rien d'ajouté |

## 4. Reproductibilité avec nos données

| Besoin | Disponible ? |
|---|---|
| OHLC H1 Swissquote, 5,1 ans, 17 instruments | OUI — snapshot figé cache 2026-08-16 |
| ATR/ADX/SuperTrend causaux | OUI — implémentations vérifiées R1 dans l'étude grid |
| Spread + slippage réels | OUI — catalogue + slippage 0,5 pip (convention projet) |
| Volume réel / carnet | NON — non requis par la méthode |

Aucune substitution, aucune dégradation : la règle candidate est exactement
celle mesurée par l'étude n°4. Les seuls degrés de liberté (seuil, stop) sont
déclarés et bornés a priori.

## 5. L'hypothèse testable

Voir HYPOTHESIS.md §1 (H90 : sur-réaction/liquidité, prédictions et
interdits) et §3 (F1-F8, mapping F3b, règles de verdict figées). Le nœud de
l'instruction : **est-ce que l'effet existe hors des 3 instruments qui ont
servi à le découvrir, net de coûts réels, contre un témoin conditionné à
l'état d'excursion ?** Tout le reste est du contrôle.

## 6. Risques identifiés avant exécution

1. **Sélection post-hoc** — les vedettes viennent de l'étude grid ; d'où
   l'univers 17 instruments et le verdict suspendu au pool hors découverte.
2. **Aliasing de graine** — documenté dans l'étude n°4 ; d'où F5 (5 graines).
3. **Témoin trop faible** — réserve §5.7 de l'étude n°4 ; d'où F3b
   (conditionné à l'état), avec mapping d'issues écrit d'avance.
4. **Folds emboîtés** — les 4 fenêtres OOS ne sont pas indépendantes
   (METHODOLOGY §9) ; limite reconduite, non résolue ici.
5. **Mono-régime** — 5,1 ans sans krach ; le verdict ne parlera que de
   l'espérance, pas de la queue.
