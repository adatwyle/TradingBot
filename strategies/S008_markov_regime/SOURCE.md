# Source — « hedge fund method » : chaîne de Markov sur régimes de marché

**Vidéo** : https://www.youtube.com/watch?v=Z-hU97WO30I (Lewis Jackson, 13 juin 2026, 71 046 vues)
**Concept attribué à** : « Ran », quant sur X/Twitter
**Transcript** : `SOURCE_transcript.txt` — Adrian a fourni la transcription complète
**Captures** : `frames/`

---

## 0. Pourquoi cette source mérite un traitement sérieux

Contrairement à la plupart des sources examinées, **le fond est académiquement
réel**. Les chaînes de Markov à changement de régime et les modèles de Markov
cachés sont un outil standard de la finance quantitative (Hamilton 1989 sur les
régimes économiques, et toute la littérature *regime-switching* qui suit). Ce
n'est ni une invention de youtubeur ni un indicateur propriétaire.

Mieux : **deux des trois corrections qu'il revendique sont statistiquement
justes**, et l'une d'elles est un piège que nous connaissons bien.

Le contenu est monétisé (formation payante, prompt derrière inscription) et les
chiffres annoncés sont invérifiables. Mais le mécanisme, lui, est entièrement
spécifié dans la vidéo — assez pour être codé sans rien deviner.

**Note sur les « prompts proposés »** : son prompt clé-en-main installe un script
Pine sur TradingView. Ce n'est pas notre plateforme, et l'installateur n'a aucun
intérêt pour nous. Ce qui compte est la stratégie, qui est intégralement décrite
dans le transcript.

---

## 1. Le mécanisme, étape par étape

### 1.1 Définition de l'état (concept 2)

Sur les **20 derniers jours**, on calcule le rendement cumulé :

| rendement 20 j | état |
|---|---|
| > +5 % | **bull** |
| entre −5 % et +5 % | **sideways** |
| < −5 % | **bear** |

Il dit lui-même que ces seuils sont arbitraires — c'est ce qui motive le HMM
plus loin.

### 1.2 Propriété de Markov (concept 3)

> « Where the market goes is entirely dependent on the state today. Not about
> what's happened in the past. »

Hypothèse d'absence de mémoire : l'état de demain ne dépend que de l'état
d'aujourd'hui, pas du chemin parcouru.

### 1.3 Matrice de transition (concept 4)

Compter historiquement toutes les transitions d'état vers état — **neuf
combinaisons** — et en tirer une matrice 3×3 de probabilités conditionnelles.

### 1.4 Persistance, « stickiness » (concept 5)

P(bull → bull) et P(bear → bear) ressortent élevées : c'est, dit-il, la
justification mathématique de « the trend is your friend ».

**→ CORRECTION N°1, et elle est juste.** Les fenêtres de 20 jours consécutives
**se chevauchent sur 19 jours**. Deux observations successives partagent 95 % de
leur information, donc la persistance mesurée est un **artefact mécanique**, pas
une propriété du marché. Son analogie est bonne : se peser tous les jours donne
l'illusion d'un poids stable.

Sa correction : n'échantillonner les transitions que sur des **fenêtres sans
recouvrement** — attendre 20 jours avant l'observation suivante. Cela réduit
fortement les probabilités de persistance.

C'est statistiquement correct et c'est exactement le type de défaut que nous
traquons.

### 1.5 Le signal (concept 6)

    signal = P(bull demain | état actuel) − P(bear demain | état actuel)

Positif → long, négatif → short. **La magnitude dimensionne la position** :
70 % de confiance → grosse allocation ; 1 % → petite.

*(Erreur d'énoncé dans la vidéo à 8:46 : il dit « 70 % likelihood of a bare state »
alors que son calcul donne un état bull. Lapsus, sans incidence sur la méthode.)*

### 1.6 Prévision à plusieurs jours (concept 7)

Il décrit : élever la probabilité à la puissance n (0,6 → 0,6² → 0,6³).

**→ C'EST MATHÉMATIQUEMENT FAUX.** Pour une chaîne de Markov, la distribution à
n pas s'obtient par la **puissance n-ième de la MATRICE** (P^n), pas par
l'exponentiation d'un scalaire. Les deux ne coïncident que dans des cas
dégénérés. L'implémentation doit utiliser P^n ; la version scalaire converge
vers zéro alors que P^n converge vers la distribution stationnaire — deux
comportements opposés.

Il a d'ailleurs raison sur la conséquence pratique (au-delà de quelques jours,
l'information se dissipe), mais pour la mauvaise raison.

### 1.7 Walk-forward (concept 8)

**→ CORRECTION N°2, et c'est la plus importante.** La matrice de transition doit
être estimée **uniquement sur les données antérieures** au point de décision.
Sinon la stratégie connaît des transitions qui n'avaient pas encore eu lieu.

> « It's almost like taking an exam after you've already seen the answer sheet. »

C'est exactement notre invariant R1. Il rapporte que la correction **change le
signe des résultats** : le S&P 500 passe de perdant à gagnant sur 30 ans, et
Bitcoin de 23× à ~60×.

Ce changement de signe est en soi une information : un backtest dont le verdict
s'inverse selon qu'on corrige ou non la fuite est un backtest dont on ne peut
rien conclure sans savoir laquelle des deux versions on lit.

### 1.8 Markov caché (concept 9)

Plutôt que des seuils arbitraires à ±5 %, ajuster un **HMM** qui apprend les
états directement des données. Puis ne trader que lorsque les deux méthodes
**concordent** — « confirmation subjective et objective ».

**→ DANGER MAJEUR, qu'il ne traite pas.** Un HMM ajusté sur l'échantillon complet
puis utilisé pour étiqueter ce même échantillon est une fuite massive : les
frontières d'état sont apprises en connaissant toute l'histoire. Notre propre
dépouillement d'une autre source a déjà classé ce défaut en rejet
(`docs/sources/aipathways/SYNTHESE.md`, R7 : « HMM entraîné et étiqueté sur la
fenêtre de backtest elle-même »).

Il applique sa correction n°2 à la matrice de transition mais **ne dit nulle part
qu'il l'applique au HMM**. Le HMM doit être réajusté en fenêtre glissante, sinon
la correction n°2 est annulée par la porte de derrière.

### 1.9 Deux modes d'emploi (concept 10)

- **Filtre** : le régime autorise ou interdit la stratégie existante — longs
  seulement si le signal est haussier, plat en marché indécis
- **Autonome** : la stratégie trade le signal directement, taille proportionnelle
  à la persistance, avec un plafond

---

## 2. L'hypothèse à tester en priorité, et elle est décisive

**Une matrice de transition stationnaire produit un signal CONSTANT par état.**

Si l'état actuel est « bull », alors P(bull demain) − P(bear demain) est un
nombre fixe, le même à chaque fois qu'on est en état bull. La stratégie se
réduit donc mécaniquement à :

> long quand le rendement 20 jours dépasse +5 %, short quand il est sous −5 %,
> plat entre les deux

C'est-à-dire **une règle de momentum à 20 jours**, habillée d'un vocabulaire
markovien.

Le test qui tranche est simple et il doit être fait EN PREMIER : comparer la
stratégie complète à cette règle naïve. **Si les deux donnent les mêmes trades,
tout l'appareil markovien est de la décoration** — élégante, pédagogiquement
utile, mais sans contribution mesurable.

Le seul endroit où l'appareil peut apporter quelque chose est la **matrice
glissante** : si les probabilités de transition évoluent dans le temps, le signal
change d'amplitude et peut même changer de signe pour un même état. C'est
exactement ce qu'il faut isoler et mesurer.

Ce que cela signifie pour nous : le suivi de tendance est **déjà mesuré mort** sur
nos instruments (s01, s11, et concordance externe). Si l'appareil markovien se
réduit à du momentum 20 jours, on connaît d'avance le résultat — d'où l'intérêt
de mesurer sa **contribution marginale** plutôt que sa performance absolue.

---

## 3. Ses chiffres, et la question qu'ils posent

| Annonce | Remarque |
|---|---|
| S&P 500 profitable sur 30 ans | aucune référence donnée — profitable *contre quoi* ? |
| Bitcoin ~60× | **le buy & hold de Bitcoin sur la même période fait bien davantage** |

Ce second point est le plus important. Selon la période, détenir Bitcoin sans
rien faire produit plusieurs centaines de fois la mise. Un « 60× » pourrait donc
être une **sous-performance massive** présentée comme un succès — c'est
exactement le piège que notre moteur d'allocation rend impossible, puisqu'il sort
systématiquement le buy & hold de chaque constituant et l'équipondéré naïf.

Il ne compare jamais à une référence. C'est l'angle mort central de la source.

---

## 4. Reproductibilité

| Composant | Faisable ? |
|---|---|
| États par rendement 20 j à seuils ±5 % | oui, purement prix |
| Matrice de transition, fenêtres non recouvrantes | oui |
| Signal P(bull) − P(bear) | oui |
| Prévision n pas par P^n | oui — **matrice**, pas scalaire |
| Matrice glissante causale | oui |
| HMM en fenêtre glissante | oui (`hmmlearn` ou implémentation directe) |
| Mode filtre et mode autonome | oui |

**Tout est reproductible.** Aucun indicateur propriétaire, aucune donnée
indisponible. C'est la première source de la journée dont le mécanisme est
intégralement à notre portée.
