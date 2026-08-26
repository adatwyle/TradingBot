# Conditions de falsification — déclarées AVANT tout résultat

> **Horodatage : 2026-08-16.** Écrit et figé avant l'exécution du premier
> backtest, avant même que `strategy.py` existe. Aucun seuil de ce fichier n'a
> été choisi en regardant un chiffre.
>
> `docs/METHODOLOGY.md` §10 : « Ne cherchez jamais la configuration qui *sauve*
> un résultat décevant. » Le seul moyen crédible de tenir cet engagement est de
> nommer d'avance ce qui compterait comme un échec.

**Commit de référence au moment de l'écriture : `434ced1`.**

---

## L'hypothèse, formulée pour être réfutable

> **H** — L'appareil markovien (états par rendement 20 j, matrice de transition
> estimée causalement, signal `P(bull) − P(bear)`, taille proportionnelle à la
> confiance) apporte une **contribution mesurable au-delà d'une simple règle de
> momentum à 20 jours**, et le portefeuille qui en résulte fait mieux que
> détenir les mêmes actifs, après coûts, hors échantillon.

Deux affirmations distinctes, volontairement séparées :

- **H-a (contribution marginale)** — l'appareil n'est pas de la décoration.
- **H-b (performance)** — le résultat bat l'effort zéro.

H-a peut être fausse alors que H-b est vraie (le momentum 20 j marcherait tout
seul, l'habillage markovien n'y serait pour rien). H-b peut être fausse alors
que H-a est vraie (l'appareil change réellement les positions, mais pour le
pire). Les confondre serait la faute méthodologique principale disponible ici.

**Le raisonnement qui motive H-a, posé avant toute mesure.** Une matrice de
transition **stationnaire** attribue à chaque état un signal **constant** :
si l'état est *bull*, `P(bull|bull) − P(bear|bull)` est le même nombre à chaque
occurrence de *bull*. La stratégie se réduit alors exactement à « long si
ret20 > +5 %, short si ret20 < −5 %, plat entre les deux ». Le seul mécanisme
par lequel l'appareil peut se distinguer est la **matrice glissante** : si les
probabilités estimées évoluent, l'amplitude change et le signe peut s'inverser
pour un même état. C'est cela, et rien d'autre, qui doit être isolé.

**Qui paie ?** (`docs/METHODOLOGY.md` §1, question la plus discriminante.)
Réponse honnête avant test : personne de nouveau. Le mécanisme est du
*time-series momentum* à 20 jours. Sa contrepartie structurelle est le trader à
contre-tendance ; la prime existe dans la littérature, mais elle est parmi les
plus documentées, donc les plus arbitrées, et elle est **déjà mesurée morte sur
nos instruments** (s01, s11, plus une concordance externe). L'appareil markovien
n'ajoute aucune contrepartie nouvelle — il ré-exprime la même. C'est une raison
de doute *a priori*, pas un verdict.

---

## F1 — L'appareil markovien est de la décoration

**Déclenchée si** : sur le plein échantillon et sur chaque instrument, la suite
des poids produite par la stratégie complète coïncide avec celle de la règle
naïve *momentum 20 j* sur **≥ 95 % des barres**, ET l'écart de CAGR entre les
deux est **< 1 point**.

**Ce que cela signifierait** : le vocabulaire markovien serait un habillage
pédagogique sans contribution mesurable. Le verdict devrait alors porter sur la
règle de momentum, pas sur la chaîne de Markov — et cette règle est déjà jugée
ailleurs dans le projet.

**Mesure associée, à produire quoi qu'il arrive** : taux de concordance de
signe, taux de concordance de poids à 1 % près, nombre de barres où le signal
markovien **change de signe** pour un état donné (le seul événement qui prouve
que la matrice glissante fait quelque chose).

**Ce qui ne compte pas comme réfutation de F1** : une différence de *taille* de
position seule. Si les deux versions sont longues et courtes aux mêmes moments
et ne diffèrent que par l'amplitude, l'appareil ne fait que du dimensionnement —
ce sera dit comme tel, pas présenté comme un edge de timing.

---

## F2 — Ne bat pas l'effort zéro

**Déclenchée si** : sur le plein échantillon, le Sharpe **et** le rendement
total de la stratégie sont inférieurs à ceux du **meilleur** benchmark rendu par
`run_allocation()` (buy & hold de chaque constituant, équipondéré naïf, cash).

**Pourquoi c'est le test central de la source** : l'auteur annonce « Bitcoin
~60× » sans jamais donner de référence. Le buy & hold de Bitcoin sur une période
comparable fait vraisemblablement davantage. Notre moteur rend la référence
systématiquement ; c'est le critère n°1 de `docs/METHODOLOGY.md`.

**Nuance retenue d'avance** : perdre en rendement total tout en divisant le
drawdown est un arbitrage défendable, pas un échec. F2 exige donc que les
**deux** soient inférieurs.

---

## F3 — S'effondre hors échantillon

**Déclenchée si** : moins de **3 fenêtres sur 4** du walk-forward ancré
(60/70/80/90 %) rendent un rendement OOS positif, **ou** si le rendement OOS
moyen est négatif.

**Garde-fou statistique déclaré d'avance** : la grille de paramètres sera
maintenue sous 60 cellules, soit **≈ 3 « réussites » attendues par pur hasard**
au seuil 5 %. Tout compte de réussites inférieur ou égal à cette attente sera
traité comme indistinguable du bruit, quelle que soit sa présentation.

**Contrainte d'effectif propre à cette stratégie, notée avant de mesurer** :
l'échantillonnage sans recouvrement à 20 jours réduit l'effectif d'un facteur
20. Sur 2 774 barres D1 (SP500, ~10,6 ans), cela donne ~138 transitions
observées au total, et bien moins au début de l'historique. Une matrice 3×3
estimée sur ~50 transitions a des barres d'erreur énormes. **L'effectif de
transitions sera rapporté à côté de chaque matrice**, sans exception. Si la
première fenêtre du walk-forward dispose de moins de **30 transitions**, elle
sera déclarée non concluante plutôt qu'interprétée.

---

## F4 — Le résultat n'est qu'un pari directionnel déguisé

**Déclenchée si** : plus de **85 %** du résultat vient d'un seul instrument,
**ou** si la jambe longue porte tout pendant que la jambe courte détruit — sur
un échantillon (2014-2026 pour BTC, 2016-2026 pour les indices) qui contient un
marché haussier massif.

**Pourquoi ici en particulier** : `docs/METHODOLOGY.md` §5.2 — sur s01/USDJPY,
+69,7 R en long contre −10,0 R en short passait pour un système ; c'était un
pari sur la hausse. Une stratégie qui est longue 70 % du temps sur BTC depuis
2014 gagnera de l'argent quelle que soit la qualité de son signal.

**Contrôle imposé** : décomposition long / short séparée, systématique, sur
chaque instrument.

---

## F5 — Le verdict change de signe selon qu'on corrige la fuite

**Déclenchée si** : la version à matrice **non causale** (estimée sur tout
l'échantillon, ce que fait implicitement la version « v1 » que l'auteur dit
avoir corrigée) est rentable alors que la version **causale** ne l'est pas.

**Pourquoi c'est une condition à part entière** : l'auteur affirme que la
correction causale **inverse le signe** de ses résultats — dans le sens
favorable (S&P 500 de perdant à gagnant). C'est contre-intuitif : une fuite
d'information améliore normalement le backtest, elle ne le dégrade pas. Si
notre mesure va dans le sens attendu (fuite → meilleur) et que l'écart est
important, alors son récit est douteux **et** la version honnête est la moins
flatteuse des deux.

Cette condition n'est pas un test de la stratégie mais un test de la **source**.
Elle sera chiffrée dans les deux sens et l'écart rapporté en clair : c'est une
mesure directe de l'ampleur du biais de fuite, utile bien au-delà de s08.

**Corollaire HMM, déclaré ici pour ne pas pouvoir l'éviter plus tard** : si le
HMM est implémenté, ses deux versions (ajusté une fois sur tout l'échantillon
puis utilisé pour étiqueter ce même échantillon / réajusté en fenêtre glissante)
seront mesurées **toutes les deux**. `docs/sources/aipathways/SYNTHESE.md` R7
classe déjà le premier cas en rejet. Publier uniquement la version glissante
priverait le rapport de l'ampleur du biais ; publier uniquement la version
pleine serait une fraude.

---

## Ce qui ne comptera PAS comme une réfutation

Nommé d'avance pour ne pas pouvoir s'en servir d'échappatoire.

- **Un désaccord avec le « 60× » annoncé.** Ce chiffre n'est ni daté, ni
  documenté, ni comparé à une référence. Il n'est pas la cible.
- **Un rendement total inférieur au buy & hold, seul**, si le drawdown est
  nettement plus faible (cf. nuance F2).
- **L'absence du mode « enhanced states »** de la démo vidéo : le transcript ne
  dit nulle part ce qu'il contient. Reproduire ce qui n'est pas spécifié serait
  inventer. Le manque sera déclaré, il ne sera pas comblé par une supposition.
- **Le fait que le S&P 500 ne soit pas SPY.** Nous avons un CFD indice
  Swissquote, pas l'ETF, et pas les dividendes. Écart connu, déclaré, il rend le
  résultat approximatif — pas faux.
- **Une profondeur d'historique inférieure aux « 30 ans » qu'il évoque.** Nous
  disposons de 10,6 ans sur les indices et 12,1 ans sur BTC. C'est une limite de
  reproduction, elle rend le verdict PARTIEL sur l'axe régime macro.

---

## Le point de comparaison retenu

Aucun chiffre de la source n'est vérifiable : pas de date de début, pas de
capital initial, pas de référence, pas de courbe. La comparaison se fera donc
**exclusivement contre les benchmarks internes** rendus par `run_allocation()`.

C'est précisément l'angle mort de la source, et le harnais y répond nativement.
