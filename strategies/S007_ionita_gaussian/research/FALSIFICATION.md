# Conditions de falsification — déclarées AVANT tout résultat

> **Horodatage : 2026-08-16.** Ce fichier est écrit et figé avant l'exécution du
> premier backtest. Les seuils qu'il contient n'ont pas été choisis en regardant
> des chiffres. C'est le seul moment où ils peuvent être honnêtes.
>
> `docs/METHODOLOGY.md` §10 : « Ne cherchez jamais la configuration qui *sauve*
> un résultat décevant. » Le meilleur moyen de tenir cet engagement est de
> nommer d'avance ce qui compterait comme un échec.

---

## Hypothèse testée, formulée précisément

> **H** — Le canal gaussien, appliqué à un portefeuille multi-actifs en daily,
> produit un timing d'entrée et de sortie qui améliore le couple
> rendement/risque **par rapport à la simple détention des mêmes actifs**, après
> coûts, et hors échantillon.

Formulation choisie pour être réfutable. Elle ne dit pas « la stratégie gagne de
l'argent » — sur des actifs qui ont beaucoup monté, à peu près tout gagne de
l'argent. Elle dit qu'elle fait **mieux que ne rien faire sur les mêmes lignes**.

C'est aussi exactement l'affirmation de l'auteur, qui consacre trois minutes de
`03_gaussian_10months_forward.txt` à expliquer pourquoi le buy & hold est une
« horrific strategy ». Le point de désaccord est donc net et mesurable.

**Qui paie ?** (`docs/METHODOLOGY.md` §1, question la plus discriminante.)
La réponse honnête, avant test : le mécanisme est un suiveur de tendance à
cassure de bande. Sa contrepartie structurelle serait le vendeur de volatilité
et le trader à contre-tendance, qui paient les rares grands mouvements en
échange de nombreux petits gains. C'est une prime documentée depuis des
décennies (time-series momentum). Elle existe. La question n'est donc pas
« est-ce que ça peut marcher » — c'est « reste-t-il quelque chose après les
coûts d'un CFD crypto et après le drawdown ».

---

## F1 — Ne bat pas la détention des mêmes actifs

**Déclenchée si** : sur le plein échantillon, le rendement total ET le Sharpe de
la stratégie sont inférieurs à ceux du meilleur benchmark rendu par le moteur
(buy & hold de chaque ligne, équipondéré naïf, cash).

**Pourquoi c'est le test décisif** : c'est le critère n°1 de
`docs/METHODOLOGY.md`, et c'est l'affirmation centrale de l'auteur. Si elle
tombe, le reste est un détail d'optimisation.

**Nuance retenue d'avance, pour ne pas tricher plus tard** : une stratégie peut
légitimement perdre en rendement total tout en gagnant en Sharpe et en drawdown.
C'est même son argument explicite (« 8,5 % de DD max »). F1 exige donc que les
DEUX soient inférieurs. Perdre en rendement mais diviser le drawdown par trois
ne déclenche pas F1 — ce serait un résultat, pas un échec.

---

## F2 — S'effondre hors échantillon

**Déclenchée si** : moins de 3 des 4 fenêtres du walk-forward ancré rendent un
résultat OOS positif, OU si le rendement OOS moyen est négatif.

**Pourquoi** : c'est le filtre qui a éliminé 4 des 5 paires validées en avril sur
ce projet. Une stratégie qui n'existe qu'en plein échantillon n'existe pas.

**Garde-fou statistique associé** : la grille compte 45 configurations, donc
≈ 2,25 « réussites » attendues par pur hasard au seuil 5 %. Un compte de
réussites inférieur ou égal à 3 sera traité comme indistinguable du bruit,
quelle que soit sa présentation.

---

## F3 — L'effet disparaît quand on déplace le réglage

**Déclenchée si** : la performance n'est bonne que sur la cellule optimale de la
grille et s'effondre chez ses voisins immédiats (période ±1 cran, pôles ±1).

**Pourquoi** : `docs/METHODOLOGY.md` §4, test de plateau. Un pic isolé est un
sur-ajustement, pas un edge. Un edge réel est une colline, pas une aiguille.

**Signal complémentaire** : si le walk-forward retient une configuration
*différente* à chaque fenêtre, c'est le même symptôme sous une autre forme — la
grille suit le bruit récent.

---

## F4 — Les coûts mangent le résultat

**Déclenchée si** : le résultat est positif à coût nul mais négatif une fois
inclus spread + slippage + coût de portage (swap ≈ 14 %/an sur les longs crypto
CFD chez ce broker).

**Pourquoi c'est spécifiquement dangereux ici** : la stratégie de l'auteur tourne
sur Hyperliquid, où le financement d'un perpétuel est d'un ordre de grandeur
différent et peut même être encaissé. Chez un broker CFD, le portage est un
prélèvement continu. Une stratégie investie 60 % du temps paie ~8,5 %/an rien
que pour exister. C'est l'écart le plus susceptible de renverser le verdict, et
il n'est pas dans le modèle du moteur — donc il doit être chiffré à la main.

**Distinction imposée par la méthodologie** (§5.1, ablation du spread) :
- positif sans coûts, négatif avec → il y a un signal, mangé par la structure de
  coût. Conclusion : « pas exploitable ICI », pas « pas d'edge ».
- négatif dans les deux cas → il n'y a rien à sauver.
Ces deux diagnostics appellent des décisions opposées et ne seront pas
confondus.

---

## F5 — Le résultat n'est qu'un pari directionnel déguisé

**Déclenchée si** : la performance vient quasi exclusivement d'une seule ligne
(> 85 % du résultat), ou si la jambe longue porte tout pendant que la jambe
courte détruit — sur un échantillon qui contient un marché haussier massif.

**Pourquoi** : `docs/METHODOLOGY.md` §5.2. Sur s01/USDJPY, +69,7 R en long
contre −10,0 R en short passait pour un système ; c'était un pari sur la hausse
du dollar-yen. BTC de 2018 à 2026 est le pari directionnel le plus fort
disponible : le risque est maximal ici.

---

## Ce qui ne comptera PAS comme une réfutation

Nommé d'avance, pour ne pas m'en servir comme échappatoire après coup :

- **Un rendement total inférieur au buy & hold, seul.** Si le drawdown est
  nettement plus faible, c'est un arbitrage rendement/risque défendable — c'est
  l'argument de l'auteur et il mérite d'être évalué sur ses propres termes.
- **Un univers de deux lignes au lieu de cinquante.** C'est une limite de
  reproduction, déjà actée. Elle rend le verdict PARTIEL, elle ne le rend pas
  négatif.
- **L'absence du Trend Radar.** Idem : elle interdit d'attribuer une éventuelle
  surperformance au canal plutôt qu'à la sélection. Elle n'est pas une preuve
  contre le canal.
- **Un désaccord avec les 7 492 % de la publicité.** Ce chiffre n'est pas la
  cible et n'a jamais été retenu comme telle.

---

## Le point de comparaison retenu

Le **forward-test publié par l'auteur** dans
`sources/03_gaussian_10months_forward.txt` : 51,74 % de profit, 8,57 % de
drawdown max, 44,44 % de trades gagnants, sur BTC, du 15 octobre 2024 à début
septembre 2025.

C'est une donnée hors échantillon publiée par l'auteur lui-même, donc
infiniment plus informative que sa vitrine. La reproduction sera comparée à
elle, sur la même fenêtre calendaire et le même instrument.

**Relevé dès la lecture, avant tout calcul** : dans cette même vidéo, l'auteur
mesure le buy & hold de la période à « about 68% » — supérieur aux 51,74 % de sa
stratégie. Son propre forward-test échoue donc à son propre critère n°1. Ce
constat est antérieur à notre backtest ; il n'est pas un résultat de notre part,
et il ne dispense pas de faire le travail.
