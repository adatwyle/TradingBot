# Doud Trading — la méthode, reconstituée depuis 54 heures de direct

> **Source** : `lives/` — 35 transcriptions des streams publics et gratuits de la
> chaîne `@TheQueenDoud`, soit **54 heures** de scalping XAUUSD en direct,
> 68 984 segments horodatés. Sous-titres automatiques FR, non retouchés.
> **Passages retenus** : `EXTRAIT_regles.txt` (104 blocs de 90 s denses en
> vocabulaire de règle). Citations `(vidéo @ mm:ss)`, vérifiables ligne à ligne.
> **Date** : 2026-09-06.
>
> **Pourquoi ce document existe séparément de `docs/sources/moneytalk/`** : le
> podcast la fait *raconter* sa méthode, les lives la montrent l'*exécuter*. Sur
> quatre points au moins, les deux ne disent pas la même chose — et c'est le
> direct qui fait foi. Le dossier S018 avait été construit sur le seul podcast :
> ce document en corrige les prémisses.

---

## 0. Les quatre corrections que le direct impose au dossier S018

**1. Elle a une cascade de trois timeframes. Nous en testions un seul.**

> « mes timeframes préférés, je dis toujours : **H2 tendance globale, M15 zone de
> travail, M1 point d'entrée, précision sniper**. Quand je fais mes météos, c'est
> en H2. Quand je regarde mes analyses, c'est en M15. Quand je rentre, c'est en
> M1. » — `5HoIRmOBSvM @070:03`

S018 mesure en H1, puis M15, puis M5, chacun **isolément**. Aucun de ces trois
tests ne teste sa méthode, qui est une **structure hiérarchique** : la direction
vient du H2, la zone du M15, le prix du M1. C'est l'explication la plus probable
du résultat M15 (la règle v1 y perd −0,096 R/trade) : un signal mono-timeframe
sur un timeframe fin n'est pas la version fine d'un signal H1, c'est du bruit.

**2. Elle met des stops. Le podcast disait l'inverse.**

> « le SL est obligatoire » — `a__0t9kh88w @14:21`
> « **SL obligatoire pour tout le monde**, sécurisez » — `JtD2bifO96Y @024:15`
> « les annonces économiques, c'est **le seul moment où on met le SL serré** —
> pourquoi ? pour éviter une mèche qu'on aurait pas anticipée » — `G7LP5bb6UhU @027:12`
> « j'ai mis mon SL au 41038, ça me fait une perte de 168 dollars » — `KBqRb5_UJ8Y @028:49`

Le refus D11 (R3, stop obligatoire) reste — mais il ne s'oppose plus à elle.
Ce que le podcast présentait comme « je ne mets pas de stop » se lit, en direct,
comme **« je ne mets pas de stop serré hors annonce »** : stop large ou suiveur en
régime normal, stop serré pendant les annonces. Ce n'est pas la même affirmation,
et notre `SYNTHESE.md` du podcast § 1.8 la caractérisait mal.

**3. Elle n'est pas long-only.**

> « Moi, **je suis vendeuse**, je pense que tout le monde le sait aujourd'hui » —
> `NpesTgZ6KbQ @004:45`

Le podcast dit « je vends quasiment jamais » (@ 21:52). En direct elle se déclare
vendeuse ce jour-là, et ailleurs acheteuse. Le biais n'est pas structurel : il est
**décidé chaque jour** (cf. § 1). Notre commutateur `side_mode = long_only`
testait donc une affirmation qu'elle ne fait pas vraiment — ce qui n'invalide pas
la mesure, mais change ce qu'elle veut dire.

**4. Son « équilibre » n'est pas le milieu d'une jambe.**

> « sur les 4998 57, nous sommes sur **l'équilibre du fair value gap** et donc il
> faut **attendre une prise de liquidité** » — `JtD2bifO96Y @046:10`
> « on reste sur **l'équilibre institutionnel** » — `UugYUucNXlI @004:41`
> « les **prix intermédiaires**, c'est là où c'est **le plus risqué** » — `JtD2bifO96Y @046:10`

C'est l'erreur la plus coûteuse du dossier S018. J'avais traduit « récupérer le
milieu » (podcast @ 18:08) par *entrer au retracement 50 % de la jambe*. En direct,
l'équilibre désigne le **milieu d'un fair value gap** (concept ICT), c'est-à-dire
une zone identifiée à l'avance — et elle dit explicitement que **le milieu de
mouvement est la zone la plus dangereuse** où entrer. Le commutateur
`entry_mode=equilibrium` de S018 ne teste donc pas son idée. Son effet mesuré
(+0,010 R/trade en H1) ne dit rien de sa méthode.

---

## 1. Le pipeline réel, dans son ordre

### 1.1 Avant la séance — la direction

Elle arrive avec un biais construit sur le H2 et le contexte macro, publié le
dimanche (« la météo »). En direct elle l'énonce et s'y tient : *« je reste
haussière sur le long terme, je vais chercher les 3000 quoi qu'il m'en coûte »*
(`VPLmoxOmhDY @007:51`). Elle **refuse de trader contre son biais** : quand le
marché part dans l'autre sens, *« on laissera la main au vendeur et on attendra un
setup acheteur »* (`NpesTgZ6KbQ @004:45`).

Elle **ne travaille pas 24 h avant une décision de taux** : *« normalement, je
travaille jamais 24 heures avant les taux d'intérêt »* (`5HoIRmOBSvM @003:07`).

### 1.2 La zone — M15

Elle marque à l'avance des zones colorées (« zone jaune », « zone rose ») et des
**prises de liquidité** : des poches de stops sous le prix qu'elle attend de voir
balayées. Le vocabulaire est constant sur les 35 lives : *liquidité* apparaît plus
souvent que *TP*, *SL* et *point d'entrée* réunis.

### 1.3 L'entrée — M1, après le balayage

Le déclencheur n'est pas une cassure : c'est **un balayage de liquidité suivi d'un
rejet**, puis l'impulsion.

> « il vient chercher les stop loss, il est remonté, il a stoppé, il a ressorti
> plus bas et **il est parti en impulsion** » — `5HoIRmOBSvM @070:03`
> « plus il chute, **plus on a le point d'entrée pour acheter** le gold » — `5IPouztc1_0 @010:33`
> « on a même pas eu de DD parce qu'on a pris **sur mèche de rejet**. Zéro DD » — `UugYUucNXlI @019:02`
> « il va juste venir **chasser les SL**. Voilà ce qu'il a l'habitude de faire » — `G7LP5bb6UhU @071:25`

Autrement dit : elle **attend que le marché aille chercher les stops des autres**,
et achète le rejet. C'est mécaniquement l'inverse d'une entrée en cassure — et
c'est codable (balayage d'un plus-bas récent + réintégration dans la barre).

### 1.4 Le cas des annonces — une horloge précise

> « le point d'entrée sur une annonce économique **ne se fait pas avant 27** » —
> `LTN-S3DC5Fg @011:53`
> « il est 23, on attend 28, comme d'habitude, pour être sûr du point d'entrée » —
> `G7LP5bb6UhU @027:12`
> « tu peux trader **5 minutes avant et 5 minutes après**, mais **tu ne peux pas
> trader pendant** l'annonce » — `1kVYJ160yOI @032:39`
> « une annonce économique peut bouger de **3000 points** […] en M1 sur une bougie
> d'impulsion, c'est très probable » — `G7LP5bb6UhU @027:12`

Elle note aussi les mouvements qui **précèdent** la publication : *« je note le
mouvement parce qu'il se produit avant, et deux fois cette semaine »*
(`Cc1Meko5FhA @020:56`).

### 1.5 La taille — progressive, jamais pleine

> « mes premiers trades, je ne rentre pas avec mes lots initiaux de départ. **Je
> trade 0,10**, je tâte un petit peu le terrain pour ne pas risquer mes bénéfices
> de la veille » — `9lp_5lvii3I @045:01`
> « je suis en lot de 1, et après je passe en **0,50 et 0,25** pour des clôtures
> partielles » — `NpesTgZ6KbQ @074:46`
> « je ne rentre pas en lot de 1 cette semaine. Beaucoup trop imprévisible » — `Cc1Meko5FhA @027:15`
> « n'oubliez pas, **on ne rentre jamais avec ses gros lots** sur ces niveaux-là » — `5IPouztc1_0 @018:16`

Et le renforcement, qui existe bien : *« s'il casse ce niveau-là, on attendra un
point plus bas et **on renforcera** beaucoup plus bas »* (`Cc1Meko5FhA @020:56`),
avec compensation entre positions : *« je compense mes lots sans avoir mis tous mes
lots sur le même niveau »* (`G7LP5bb6UhU @060:16`).

### 1.6 La sortie — c'est là que vit son système

**Clôtures partielles** : *« quand je rentre en multiple de trois, j'en ferme une,
j'en ferme une, et après les autres, je les mets à suiveur »* (`1kVYJ160yOI @018:32`) ;
*« je ferme une position de mon côté, je suis en multiple […] maintenant j'en garde
qu'une seule »* (`KBqRb5_UJ8Y @031:57`).

**Stop suiveur, systématique et non négociable** : *« c'est le suiveur pour tout le
monde, obligatoire, non négociable »* (`1kVYJ160yOI @021:43`) ; *« on monte le SL
suiveur »* revient dans presque tous les lives ; *« pourquoi je vous demande de le
poser ? pour que quoi qu'il arrive votre trade soit sécurisé »* (`QbkYJMzeodI @071:59`).

**Refus explicite du break-even** : *« tu ne sors pas à break even, et encore moins
à perte »* (`KBqRb5_UJ8Y @031:57`) ; *« ceux qui sortent à break even, c'est ceux
qui ont peur du marché »* (`KiGK6ydHfK4 @024:10`) ; et à l'inverse, couper une
perte est sain : *« fermer ses pertes, ce n'est pas grave et ce n'est pas une
honte »* (`1kVYJ160yOI @009:18`).

### 1.7 Ce qu'elle vise — des ratios hors norme

C'est le chiffre le plus important du corpus, et il n'apparaît nulle part dans le
podcast :

> « en général, **un trader trade entre 1 et 1,5 de ratio** » — `1kVYJ160yOI @018:32`
> ratios annoncés en direct sur ses propres positions : **1,92 · 2,82 · 4,52 ·
> 5,00 · 5,65 · 7,00 · 7,29 · 8,66 · 8,93** (`1kVYJ160yOI`, `5HoIRmOBSvM`,
> `KBqRb5_UJ8Y`, `G7LP5bb6UhU`)
> « je ne vais pas chercher des ratios de 10 ; en général, je vais chercher des
> ratios **entre 15 et 17** » — `1kVYJ160yOI @056:14`
> « le plus petit ratio cette semaine, c'était 7 » — `1kVYJ160yOI @074:49`

Un R:R de 5 à 17 n'est atteignable qu'avec un **stop qui remonte** : le risque
initial se réduit en cours de trade, donc le dénominateur du ratio aussi. C'est
exactement ce que notre moteur ne sait pas faire. Notre S018 travaille à R:R
**fixe 2,67** (tp_m 4,0 / sl_m 1,5). **Nous ne mesurons pas la même géométrie de
trade qu'elle, pas même approximativement.**

### 1.8 L'outillage

MT5 (`G7LP5bb6UhU @063:24`), CFD **et** prop firm Topstep en parallèle, journal de
trading quotidien tenu sans exception (`9lp_5lvii3I @007:28`), lives à 14 h tous
les jours sauf le mercredi (`KBqRb5_UJ8Y @039:44`).

---

## 2. Ce que ça change pour S018 — bilan honnête

| Élément | Ce que S018 a codé | Ce qu'elle fait | Verdict |
|---|---|---|---|
| Timeframe | un seul (H1, puis M15, M5) | cascade H2 → M15 → M1 | **non testé** |
| Entrée | cassure Donchian, ou repli 50 % | balayage de liquidité + rejet, sur zone M15 pré-marquée | **mal traduit** |
| Direction | commutateur long-only figé | biais décidé au jour le jour sur H2 | **mal traduit** |
| Stop | ATR × 1,5 fixe | large ou suiveur, **serré uniquement en annonce** | partiellement |
| Sortie | TP unique à 4 ATR | partielles + suiveur, R:R visé 5 à 17 | **non testé** (moteur) |
| Break-even | absent | **refusé explicitement** | conforme par accident |
| Taille | hors périmètre (R2) | 0,10 pour tâter, puis 1,0, partielles 0,50/0,25 | hors périmètre |
| Annonces | non testé (pas de calendrier) | entrée à T−3 min, jamais pendant, stop serré | **non testé** |

**Conclusion** : le verdict `NON RETENU` de S018 reste valide **pour ce que S018
mesure** — un signal de cassure Donchian augmenté de cinq filtres. Il ne dit
toujours rien de la méthode Doud, et il en dit encore moins que je ne le pensais :
sur les huit éléments ci-dessus, **deux sont mal traduits et trois ne sont pas
testés du tout**.

---

## 3. Ce qui serait mesurable, et à quelles conditions

Par ordre de faisabilité décroissante, avec le verrou associé :

1. **Entrée par balayage de liquidité + rejet** — codable aujourd'hui sur M1/M5
   (balayage d'un plus-bas de N barres puis réintégration dans la même barre).
   C'est la traduction correcte de son déclencheur, et elle remplace le
   `entry_mode=equilibrium` mal traduit.
2. **Cascade de timeframes H2/M15/M1** — codable : porte de tendance H2, zone M15,
   déclenchement M1. Nos données couvrent les trois (M1 non encore tiré, M5 oui).
3. **Sorties partielles + stop suiveur** — **bloqué par le moteur** (`TCK-014`).
   C'est le verrou principal : sans lui, la géométrie R:R 5-17 est hors d'atteinte
   et toute mesure de sa méthode reste une caricature.
4. **Fenêtres d'annonce** — **bloqué par l'absence de calendrier** (`TCK-016`).
   Ses règles horaires sont précises (T−3 min, jamais pendant, ±5 min) et donc
   testables dès qu'on a les dates.
5. **Biais journalier H2 + refus de contre-tendance** — codable, déjà approché par
   `htf_bias` mais sur une EMA journalière plutôt que sur sa lecture H2.

---

## 4. Ce que ce corpus ne prouve pas

- **Aucun résultat n'est vérifié.** Elle annonce des ratios et des gains en dollars
  à l'oral ; rien n'est un relevé. Le corpus vaut pour la **méthode**, pas pour la
  performance — même régime de lecture que `docs/sources/moneytalk/SYNTHESE.md` § 4.
- **Les sous-titres sont automatiques.** Les prix cités (« les 68 », « au 4075 54 »)
  sont souvent tronqués ou déformés par la reconnaissance vocale. Une extraction
  automatique de ses trades exacts depuis ce corpus serait fragile ; ce document
  ne s'appuie que sur des énoncés de **règle**, robustes à ce bruit.
- **Ces lives sont publics, donc pédagogiques.** Ce qu'elle y fait est peut-être
  plus prudent que sa pratique privée (elle le dit : *« vu que là j'étais en live,
  j'ai un peu pris plus de temps, je suis rentrée un peu plus tard »*,
  `5HoIRmOBSvM @063:50`).
