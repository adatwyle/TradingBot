# fxalexg (Alex Gonzalez) — synthèse des 27 transcripts

> **Sources** : 15 vidéos de fond + 12 épisodes de la série « $100 → $1M (2.0) »,
> 1,16 M de caractères de sous-titres dédupliqués. Trois rapports d'extraction
> exhaustifs, chaque affirmation sourcée `(fichier @ timestamp)`.
> **Date** : 2026-08-17. Rédigé par la session principale à partir des
> extractions ; citations en anglais d'origine (sous-titres automatiques).

---

## 0. Les trois réponses en tête

**1. Le mystère « SOS > 10% » de la checklist d'Adrian est résolu.** Le terme
n'apparaît dans aucune vidéo publique (grep exhaustif : zéro occurrence de
« SOS », « strength of signal », « checklist » chiffrée). MAIS le système existe,
décrit dans `challenge/ep06 @ 00:21:3` :

> « every single trade is graded… either graded 100%, 90%, 80%, 70% based off of
> how many confluences… let's say this trade has a total of five confluences,
> that would be a 50% grade »

**≈ 10 confluences possibles, 1 confluence = 10 %.** Et le sigle lui-même est
élucidé ailleurs : **« SOS » = Shift Of Structure** — il étiquette ses alarmes
ainsi : « type in here s oos shift of structure » (ep12 @ 00:07:0). La ligne
« Entry Check : 1. SOS 2. Entry Signal » de la checklist d'Adrian se lit donc :
*shift de structure confirmé, puis signal d'entrée* — et le « 10 % » est un
cran de la grille de notation par confluences. Les deux objets sont codables.

**2. La stratégie 2025 est nettement plus spécifiée que ce que s01 a codé.**
Zone AOI ≤ 60 pips, ≥ 3 touches en corps, règle des 2 timeframes CONSÉCUTIFS,
break + retest de neckline obligatoire — aucun de ces chiffres n'était dans s01.
La v2 est reproductible (§3).

**3. Aucune preuve auditable de richesse par le trading, dans 27 transcripts.**
Pas un relevé broker, pas un lien Myfxbook public, pas un nom de broker (refus
explicite), taille de compte délibérément cachée (« I don't have to show it »,
12 @ 00:04:3). Et un modèle économique d'audience complet et visible (§4).

---

## 1. SPEC v2 — la stratégie consolidée (état 2025)

### 1.1 Pipeline

1. **Top-down 7 TF** : W, D, 4H (trend + AOI uniquement) / 2H, 1H, 30m (entrée
   uniquement ; le 15m est en voie d'abandon — « zero use… it's just confusing
   me », 06 @ 00:25:3).
2. **Trend** : minimum **2 timeframes CONSÉCUTIFS en sync** (W+D ou D+4H — pas
   2 sur 3 : consécutifs, 06 @ 00:13:3). Jamais de contre-tendance (règle
   violée par lui-même 2 fois sur 5 trades dans le challenge $1M, 12).
3. **AOI** — la définition la plus précise du corpus (06 @ 00:15:0-00:19:3) :
   - une **zone**, pas une ligne, **largeur ≤ 60 pips**
   - **≥ 3 touches en CORPS de bougie** (jamais les mèches — « the wicks are
     just wicks », 06 @ 00:12:0)
   - identifiée **uniquement sur Weekly (swing) et Daily (day trade)**
   - à l'intérieur du dernier HH/HL de la structure
   - lookback ~1-3 ans (05 @ 00:13:3) — la déclinaison par TF de la checklist
     d'Adrian (weekly 5-6 ans, daily 1-2 ans, 4h 6-12 mois) ne figure dans
     aucune vidéo publique : soit formation payante, soit note personnelle.
4. **Attendre le retracement DANS l'AOI** — jamais d'entrée sur le break
   (05 @ 00:17:0). L'accumulation au niveau est un signe favorable.
5. **Déclencheur (durci en 2025)** : shift de structure par **body close** sur
   le TF d'entrée + **head & shoulders avec break ET retest de neckline
   obligatoire** (« It has to happen a perfect break and retest. If not, I will
   not be entering », 06 @ 00:24:3) + confirmation engulfing (« I will not take
   a trade if I do not have a bullish or bearish engulfing candlestick »,
   11 @ 00:11:0 ; variantes morning/evening star, 10).
6. **SL** : invalidation structurelle — derrière l'épaule droite ou la tête du
   H&S, au-delà du dernier pivot du TF d'entrée. **TP** : avant le prochain
   point de structure daily (≥ 3 touches à gauche). **R:R minimum 1:2**
   (2025 ; 1:2.5 en 2024 — mouvant, et enfreint à 1:2.1 sur son plus gros trade).
7. **Set and forget** (il a déposé la marque) : ni breakeven, ni trailing, ni
   partiels — SL ou TP, rien entre. Exceptions documentées : coupe au 1:2 dans
   les « Trump markets », clôture le vendredi (frais de swap), sortie fin de
   session NY sur les flips.
8. **Grading** : score de confluences ×10 % (cf. §0). Confluences observées sur
   son trade de référence : structure, H&S daily, canal cassé, AOI 4H, EMA,
   double top, engulfing, niveau psychologique rond — « 8 to 9 confluences »
   (11 @ 00:12:0).

### 1.2 Structure de marché — règles fines

- Niveaux posés sur les **corps**, jamais les mèches ; vérification au line chart
- Pivot valide = **≥ 2 bougies de retracement** (05 @ 00:06:0)
- « Snake trick » pour trouver le dernier HL/LH
- HH↔HL couplés : pas de nouveau HH sans nouveau HL
- Un shift minuscule compte quand même

### 1.3 Profil opérationnel (bornes de réfutation pour tout backtest)

| Grandeur | Valeur observée | Source |
|---|---|---|
| Fréquence | 1-2 trades/semaine MAX, semaines à zéro | 04 @ 00:01:3, 13 sem. 5 |
| Ratio pris/identifiés | ~5 exécutés / ~19 identifiés sur 4 semaines (~26 %) | 12 @ 00:21:3-00:22:3 |
| Durée de détention | swing 7 j-3 sem. ; challenge : moyenne 20 h (Myfxbook cité) | 04, 13 @ 00:45:3 |
| Win rate revendiqué | 60-65 % (08) ; 70 % sur 7 trades (13, sem. 6) | 08 @ 00:10:3 |
| Sessions | London privilégiée, NY secondaire | 14 @ 00:35:3 |
| Instruments | 100 % forex (majors + crosses GBP/JPY/CHF/AUD/NZD/CAD) | tous |

### 1.4 Ce qui reste non codable — dit par lui-même

- **La période de l'EMA n'est jamais donnée** (seulement « 1-hour EMA »).
- **Le signal d'entrée exact est gardé secret** : « there's something in here
  that happened that is my entry signal and I don't really ever speak about
  it » (13 @ 01:35:3). Ce qu'on code est donc au mieux sa version publique.
- La pondération des confluences dans le grading n'est pas publiée.
- Il est **anti-backtest assumé** : « I've always been against back testing »
  (06 @ 00:03:3), « I never back tested one day in my life » (15 @ 00:16:0).
  Sa stratégie n'a jamais été validée par backtest, de son propre aveu.

### 1.5 Diff avec s01

| | s01 avait | v2 ajoute |
|---|---|---|
| AOI | zones S/R génériques | ≤ 60 pips, ≥ 3 touches en corps, W/D uniquement, dans le HH/HL |
| Trend | alignement W/D | 2 TF **consécutifs**, hauts TF priment |
| Déclencheur | rejet + engulfing | break+retest de neckline OBLIGATOIRE, pivot ≥ 2 bougies |
| Sélection | aucune | grading ×10 %, ratio pris/identifiés ~26 % |
| Session | aucune | London, clôture vendredi |
| Niveaux ronds | non | oui (confluence) |

---

## 2. La comptabilité de la série « $100 → $1M » — instruite

### 2.1 Les faits établis par ses propres transcripts

- **Le challenge 1.0 est la pièce maîtresse du dossier survivant** : démarré le
  6 août 2023, monté à **360 000 $ en 3-4 mois… puis compte intégralement cramé
  sur un NFP** (« I got caught in between an NFP news », ep01 @ 00:04:0). Il
  voulait s'arrêter à 100 k et ne l'a pas fait. C'est lui-même qui le raconte.
- **« 90 jours » = 14 semaines racontées** (~98 jours), semaine 1 datée du
  16 juillet, vidéo finale publiée le 19 octobre 2024.
- **3 à 5 tentatives échouées AVANT** : « I failed three four five times in
  front of hundreds of thousands of people » (13 @ 00:00:3), margin call filmé.
  Le « 2.0 » du titre de la playlist n'est donc pas la 2e tentative mais au
  moins la 4e. Versions divergentes non réconciliées : « 90 days » (10) vs
  « about a year and a half… I blew plenty of challenges » (08 @ 00:10:0) vs
  départ à « $800 » (10 @ 00:09:3).
- **Sizing du flip, verbatim** : « there's no real risk management here. There's
  no real 1% 2%… The first trade you're going to take has to be **100% risk of
  the account**… then 30 to 50%… then 20 to 25% » (10 @ 00:16:3-00:17:3).
  Confirmé épisode par épisode : full margin à levier 1:500 sur les trades
  « A-grade » (ep02-04), 20 % sur l'unique trade « degen » documenté (ep05 :
  17,65 lots, SL 17 pips, −3 000 $ au tick près).
- **Jamais de take profit posé dans la plateforme** : « I always put the
  stop-loss… but I never want to cut my profit short » (ep02 @ 00:32:0) —
  sortie discrétionnaire sur clôtures daily. La moitié « TP » du set-and-forget
  n'existe pas dans sa pratique filmée.
- **Sélectivité mesurée sur la série** : ~24 setups suivis sur 5 semaines,
  **5 exécutés (~21 %)** — 3 gagnants, 2 perdants (les 2 = infractions à son
  propre plan : un contre-tendance « degen », un « chase »). Le motif de
  renoncement n°1 : pas de bougie engulfing à la clôture.
- **Parcours accidenté** : semaine 4 perte (15k→8k) + « punition » ; semaine 9
  **−40 k$** (90k→44k) ; semaine 12 **−68 k$** ; **deux changements de broker**
  en cours de route pour slippage ; le trade final 800k→1M **n'est pas détaillé**
  (« I'm going to let the stream speak for itself »).
- **Le sub David (14)** : titre « $1,000 into $9,000 » — la vidéo se termine à
  **5 999,92 $**, après un compte cramé semaine 1, un redépôt, et un margin
  call semaine 2, rationalisé (« we technically did not lose the trade »).

### 2.1bis La comptabilité fine des épisodes 7-12 — trois trous

- **La semaine manquante.** L'ép. 11 finit à ~45 000 $ ; l'ép. 12 ouvre à
  ~200 000 $ (« the account is exactly the same currently at $200,000 »).
  **Le passage 45 k → 200 k (~×4,4) n'est documenté nulle part** : 15 jours
  entre les deux publications (tous les autres épisodes sont hebdomadaires),
  numérotation qui saute, et une référence (« last week we ended off the week
  with the Iguana ») qui ne correspond pas à la fin de l'ép. 11. Un épisode ou
  une semaine manque au dossier public.
- **Les écarts de retraits.** 22 690 $ affichés → 20 000 $ redéposés (ép. 8-9,
  ~2 700 $ non expliqués) ; retrait horodaté « 18 4xx » vs les 22 000 $
  annoncés (ép. 10 vs ép. 7). Deux changements de broker en cours de route
  (slippage invoqué), dont un le jour où le broker n°1 « lost their license ».
- **La preuve tierce s'arrête au 22 août.** Le Myfxbook couvre la phase broker
  n°1 ; après le passage au broker n°3, **aucune preuve tierce n'est plus
  montrée** — MT4/MT5 à l'écran seulement, et la question « demo account ? »
  est tournée en sketch sans réponse (ep10 @ 00:20:3).
- **Le risque réel des épisodes 7-12** : 50 % explicites (ép. 8 : 35 lots,
  SL 30 pips), « almost 100% » (ép. 10), « just risk 100% it's not a big
  deal » (ép. 11), et une perte de −68 k$ = 33 % du compte présentée comme du
  risque *réduit* (ép. 12). Le stop déplacé deux fois sur la perte de −44 k$
  (ép. 10) — la violation exacte que sa propre doctrine interdit.

### 2.2 Preuves : présentes / absentes

| Élément | État |
|---|---|
| Myfxbook | montré à l'écran 2× (13), **lien public jamais cité** |
| Broker | **jamais nommé** — refus explicite ; « LQH live server » cité 1× |
| Taille de compte (challenge $1M de 2025) | **délibérément cachée** (« I don't have to show it », 12 @ 00:04:3) |
| Relevés, audit tiers | **aucun** dans 27 transcripts |
| Compte réel vs démo | affirmé réel à l'écran, jamais démontré |

### 2.3 Lecture honnête

Le moteur des flips est le **sizing** (100 % du compte, margin calls acceptés,
recommencer en cas d'échec), pas un edge démontré. Il le dit lui-même :
« flipping an account is not something that you can rely on to actually make
money » (15 @ 00:25:3), et il enseigne publiquement 1-4 % par trade — en
contradiction frontale avec sa pratique filmée. Avec 3-5 tentatives à sizing
maximal, obtenir une série gagnante spectaculaire est un résultat attendu du
processus, pas une preuve de méthode — le biais du survivant, ici documenté
par le survivant lui-même.

**Sur la richesse** : les revenus d'audience sont, eux, constatables — chaîne à
vidéos millionnaires en vues, communauté payante (claims « $1,000-1,500/week »
répétés dans chaque vidéo), bootcamp 300 places à sa 3e édition, sponsor prop
firm (Rocket21, « 10 out of 10 »), signaux Telegram massifs (« 150,000 people
copying this exact same trade »). Trancher entre trading et audience demanderait
un audit qu'aucun transcript n'offre. Les deux peuvent être vrais ; un seul est
vérifiable de l'extérieur.

---

## 3. Verdict de reproductibilité

**La v2 est codable**, avec un périmètre honnête : ce qu'on code est la version
publique de sa méthode, amputée du « signal secret » et de la pondération des
confluences. Falsifications ex ante recommandées pour un s01-v2 :

1. fréquence produite > 2 trades/semaine en moyenne → la formalisation est trop
   permissive (le facteur 10 de s06 comme précédent) ;
2. win rate hors de [55 %, 75 %] → autre stratégie que la sienne ;
3. le grading n'améliore pas le PnL **par trade** en montant le seuil → la
   couche de sélection est du rituel ;
4. R:R réalisé médian < 1,5 → incompatible avec son profil déclaré ;
5. bras témoin : percentile < 90 → indistinguable du hasard.

## 4. Recommandation

Ne pas refaire un s01-v2 mécanique isolé : la famille « structure + zones » a
déjà un verdict. **La voie utile est s93** (juge IA, mandat d'Adrian) : le
détecteur mécanique v2 produit les candidats avec leurs confluences objectivables
(zone ≤ 60 pips, touches, TF sync, break+retest, engulfing, niveau rond, EMA),
et le juge applique le **grading ×10 %** — la grille d'Alex, littéralement — en
rejeu à l'aveugle d'abord. Son propre système de notation est le cahier des
charges du juge. Les falsifications ci-dessus s'appliquent telles quelles.
