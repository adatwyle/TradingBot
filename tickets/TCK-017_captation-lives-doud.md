---
id: TCK-017
from: cc-support
to: Adrian
status: open
blocking: false
created: 2026-09-06
---

## Question

Idée Adrian (2026-09-06) : *« si la connexion à son live météo du dimanche est
nécessaire, considère cette option […] une session Claude Code headless dédiée
pourrait s'en occuper. Idem pour les connexions sur son live avant les annonces. »*

Faut-il capter les lives de Doud Trading — la « météo » du dimanche et les
sessions d'avant-annonce — par une session headless dédiée, pour alimenter S018 ?

## Réponse courte

**Non, ce n'est pas nécessaire, et ça ne débloquerait rien de ce qui bloque.**
L'architecture proposée (worker headless cadencé par la factory) est la bonne —
mais pour une autre cible. Détail ci-dessous, décision à toi.

## Pourquoi ça ne débloque rien

Le VERDICT S018 nomme trois obstacles. Un flux de ses appels n'en lève aucun.

1. **Le moteur ne sait pas exprimer ses sorties.** TP1/TP2/TP3, stop suiveur,
   break-even qui finance les frais : `core/backtest/engine.py` ne connaît qu'une
   sortie unique et ne déplace jamais un stop. Même avec l'enregistrement parfait
   de chacune de ses entrées, **nous ne saurions pas rejouer ce qu'elle en fait**
   — et c'est elle qui présente la gestion comme l'essentiel de son travail.
   C'est `TCK-014`, et c'est le vrai verrou.
2. **L'effectif.** Elle prend de l'ordre de 2 à 5 positions annoncées par semaine :
   100 à 250 par an. Le dossier S018 refuse de conclure sous 20 trades hors
   échantillon et juge 50 à 78 trades non concluants. Il faudrait **deux à trois
   ans de captation** pour atteindre un effectif lisible — sur un opérateur
   discrétionnaire dont la méthode peut changer entre-temps. Pendant ce temps,
   descendre en M15 multiplie l'effectif par 4 sur des données que nous possédons
   déjà, aujourd'hui.
3. **Le calendrier économique.** Ses lives ne nous le donnent pas. La Fed et le
   BLS le publient gratuitement, des années à l'avance. C'est `TCK-016`.

## Ce qu'on obtiendrait à la place

Un **signal de copy-trading**, pas une stratégie. Conséquences concrètes dans ce
dépôt :

- **impossible à backtester** : aucun historique reconstituable, donc R1 (causalité)
  n'a pas d'objet et R10 (`RESEARCH → BACKTESTED → PAPER → LIVE`) est infranchissable ;
- **dépendance à un tiers** qui peut arrêter, changer de méthode, ou se tromper —
  elle documente elle-même une perte de 80 000 € en une séance (@ 32:30) ;
- **exception permanente à la méthode du projet**, qui repose entièrement sur la
  mesure falsifiable. On aurait un flux qu'on suit sans savoir pourquoi.

## CORRECTION 2026-09-06 — la prémisse « ses lives sont payants » était fausse

Rédigé d'abord en ne connaissant que son offre commerciale. Vérification faite
ensuite sur sa chaîne YouTube (`@TheQueenDoud`, 8 010 abonnés) : l'onglet *lives*
contient **40 streams publics et gratuits**, tous du scalping XAUUSD en direct,
sur événement identifié et daté :

- NFP en direct, FOMC, discours de Powell ;
- « scalping GOLD pendant les inscriptions hebdomadaires au chômage » — la série
  la plus fournie, jeudi 14h30 ;
- sessions asiatiques de nuit ;
- durées de 43 à 191 minutes, 1 000 à 5 100 vues.

Les **sous-titres automatiques français sont disponibles** et exploitables : test
sur `a__0t9kh88w` (NFP, 76 min) → 1 647 segments horodatés, dont 85 contiennent
du vocabulaire d'exécution (point d'entrée, SL, TP, lot, renforcement, équilibre).

Conséquence : **l'option B ne coûte ni abonnement ni risque contractuel** — c'est
du contenu public, et l'analyser relève de la même démarche que les transcripts
déjà versionnés dans `docs/sources/`. Le § « obstacles pratiques » ci-dessous ne
vaut que pour l'option C (lives VIP payants), pas pour ce corpus-là.

Second constat, qui touche au fond du dossier S018 : dans ce live gratuit elle
dit **« le SL est obligatoire »** (@ 14:21), alors que le podcast la présente
comme tradant sans stop (@ 12:31). Le refus D11 reste (R3 est un contrat, pas une
opinion), mais la **caractérisation** de sa méthode dans `SYNTHESE.md` § 1.8 est
à réviser à la lumière de ce qu'elle enseigne en direct plutôt que de ce qu'elle
raconte en interview.

## Deux obstacles pratiques, à connaître avant de décider

- **Ses lives sont payants** (39,99 €/mois) et migrent vers sa propre plateforme
  (annoncé @ 76:01). Je ne peux ni créer de compte, ni payer, ni saisir
  d'identifiants — ces gestes te reviennent, et je ne les contournerai pas.
- **Captation automatisée d'un flux payant** : très probablement contraire à ses
  conditions d'utilisation, et il s'agit de son produit intellectuel. Ce n'est pas
  un avis moral, c'est un risque à connaître avant de construire l'outillage.

## Proposition de résolution

Trois options, par ordre de préférence.

**A — Ne rien capter pour l'instant, et dépenser l'effort là où il rend (recommandé).**
Priorité : (1) effectif — M15/M5, en cours, gratuit et immédiat ; (2) `TCK-014`
sorties partielles + trailing, sans quoi on ne mesurera jamais que ses entrées ;
(3) `TCK-016` calendrier économique depuis les sources publiques Fed/BLS, avec
exactement l'architecture que tu proposes : **un worker de la factory, cadencé,
qui maintient un fichier versionné**. Ton idée est bonne — sa cible est le
calendrier, pas son live.

**B — Capter uniquement ce qui est public et gratuit, comme banc d'essai.**
Elle dit sa météo hebdomadaire gratuite sur son Discord (@ 25:34) et fait des
lives publics YouTube/TikTok. Un worker qui journalise **le contenu public
seulement**, une ligne par semaine (direction annoncée, niveaux cités, date),
permettrait dans un an de poser une question falsifiable : *sa météo bat-elle
un tirage à pile ou face sur la direction hebdomadaire de l'or ?* Coût faible,
valeur différée, aucune dépendance dans nos décisions. À lancer seulement si tu
veux la réponse dans deux ans — c'est le genre de mesure qu'on ne peut pas
rattraper après coup.

**C — Captation du live payant.** Non recommandé pour les trois raisons ci-dessus.
Si tu la veux quand même : il te faudrait l'abonnement, ton accord explicite sur
le risque contractuel, et l'acceptation que le résultat soit un signal suivi
sans preuve — hors méthode du projet.

**Préconisation cc-support : A**, et B si tu veux ouvrir le banc d'essai tout de
suite pour l'avoir mûr plus tard.

## Réponse

<Adrian>
