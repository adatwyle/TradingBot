# Analyse — AI Pathways "Trend core" (bascule QQQ / GLD sur MM200)

Source : https://www.youtube.com/watch?v=Fb7G5SNpaes
Auteur : Brendan / AI Pathways (73,5k abonnes) — maths/eco UCLA, 3 ans en banque d'investissement
Fiche source : `docs/sources/aipathways_methodology/SOURCE.md`

> **Phase 1 — redigee avant toute mesure.** Les criteres d'invalidation du §7 sont
> fixes maintenant, precisement pour qu'ils ne puissent pas etre ajustes apres coup.

---

## 1. La source et sa credibilite

| | |
|---|---|
| Nature | Video YouTube decrivant une **methode de recherche**, dont sortent 5 survivants |
| Track record audite | **Aucun.** Pas de compte verifie, pas de competition, pas de rapport tiers |
| Ce qui est verifiable | Le rapport de backtest montre a l'ecran — donc ses *chiffres de backtest*, pas des resultats realises |
| Point a son credit | Il **signale lui-meme** la faiblesse de sa strategie A (§6) |
| Point a son credit (2) | Mention explicite : stats are test-window; parameters are conventions or train-selected (no test-window fitting) |

Credibilite methodologique **au-dessus de la moyenne** du contenu trading (fenetre
de test scellee, taux de survie 3 % assume, caveats spontanes). Credibilite *de
performance* nulle au sens strict : rien n'est audite. Le verdict porte donc sur
**la regle**, pas sur l'auteur.

---

## 2. La regle, reformulee

1. A la **cloture** de chaque seance, comparer la cloture de **QQQ** a sa **MM200**.
2. Si close > MM200 -> etre **100 % investi en QQQ**. Sinon -> **100 % en GLD**.
3. Execution a **l'ouverture de la seance suivante**.

Ni stop, ni cible, ni gestion. On est toujours investi ; seul l'actif change.

### Chiffres annonces

| Metrique | Annonce |
|---|---|
| CAGR | **+33,8 %** |
| Sharpe | **1,66** |
| Drawdown max | **-13,6 %** |
| Bascules | **5,3 / an** |
| Fenetre de test scellee | 2023-01 -> 2026-07 |
| Validation additionnelle | ~50 ans d'historique |

### Qui perd de l'argent ? (verification n2 de docs/METHODOLOGY.md)

Honnetement : **cette strategie n'a pas de contrepartie identifiable.** Personne
n'est structurellement de l'autre cote d'un signal MM200 connu depuis les annees 1930.

Le meilleur cas qu'on puisse lui construire (steelman) n'est pas un *edge* au sens
"quelqu'un paie", c'est une **prime de risque conditionnelle** :

- l'equity US a un rendement espere positif structurel (prime de risque actions) ;
- ce rendement se concentre dans les regimes de faible stress, et les krachs se
  produisent majoritairement **sous** la MM200 ;
- la MM200 est donc un filtre grossier d'exposition au risque de queue, pas une prediction ;
- l'or est negativement correle au stress de l'equity dans certains regimes.

**Ce n'est donc pas un edge, c'est une allocation d'actifs a commutation.** Ce qui
la rendrait valable n'est pas de battre le marche mais de capter une part du
rendement actions avec un drawdown reduit. La comparaison au buy & hold est donc
**le seul juge possible** — et c'est deja le critere n1 de notre methodologie.

### Adaptation a l'actif (verification n3)

Suivi de tendance sur deux actifs tendanciels. Coherent. Pas de contre-indication
du type "suivi de tendance sur un actif qui oscille".

---

## 3. Traduction dans notre univers

| Lui | Nous | Ecart |
|---|---|---|
| QQQ (ETF Nasdaq-100) | **NASDAQ** — CFD `#NAS100` | CFD sur l'indice **prix** : **pas de dividendes**. QQQ rend ~0,5 %/an -> notre NASDAQ sous-estime QQQ d'environ 0,5 point de CAGR |
| GLD (ETF or physique) | **XAUUSD** — spot | GLD a 0,40 %/an de frais, XAUUSD n'en a pas mais porte un **swap** non modelise. Ordre de grandeur comparable, signe incertain |
| SPY | **SP500** — CFD `#US500` | idem (indice prix) |
| Seance boursiere US | Barre **D1** du CFD | Le CFD cote plus longtemps que le cash ; le close D1 broker n'est pas le close 16:00 ET |

### Donnees reellement disponibles

```
load_bars("NASDAQ", "D1")  ->  1331 barres, 2021-07-19 -> 2026-08-14   (5,07 ans)
load_bars("XAUUSD", "D1")  ->  1329 barres, meme fenetre
load_bars("SP500",  "D1")  ->  1331 barres, meme fenetre
```

---

## 4. Difficulte n1 — l'echantillon est hors de portee. Dit avant de commencer.

L'auteur annonce 5,3 bascules/an. Sur 5 ans on attendrait ~27 episodes. La mesure
reelle sur nos donnees est **pire** :

```
MM200 sur NASDAQ D1, 1331 barres
  -> 200 barres consommees en warmup, 1131 barres de signal (4,3 ans)
  -> 13 changements de regime au total
  -> 2,56 bascules / an
```

**Treize episodes.** Le walk-forward ancre decoupe des tranches de test de 10 %,
soit **environ 1 episode par fenetre**.

Rappel du precedent de `docs/METHODOLOGY.md` : un "strict pass" sur **19** trades
avait un IC 95 % du taux de reussite de **[27,3 % ; 68,3 %]**, seuil de rentabilite
**dedans**. Nous sommes a 13, sur un decoupage qui en laisse 1 par fenetre.

> **Consequence assumee des maintenant : aucun resultat par comptage de trades ne
> pourra etre concluant.** Un 4/4 fenetres positives sur 1 episode par fenetre
> ne serait pas une preuve, ce serait quatre pile-ou-face.
>
> **NON CONCLUSIF (donnees insuffisantes) est, des la Phase 1, l'issue la plus
> probable du volet statistique.** Elle ne sera pas contournee.

### Ce qu'on peut mesurer malgre tout

Mesures s'appuyant sur les ~1130 rendements journaliers, non sur 13 evenements :

| Mesure | Effectif utile | Ce qu'elle dit |
|---|---|---|
| Courbe d'equity vs buy & hold | 1131 jours | Le critere n1 : bat-on l'effort zero ? |
| CAGR / Sharpe / DD max | 1131 jours | Directement comparable aux chiffres annonces |
| Temps passe dans chaque regime | 1131 jours | La strategie etait-elle du bon cote ? |
| Rendement **par jour de detention** de chaque jambe | ~730 j / ~400 j | **Attribution par jambe** — test decisif du §6 |
| Rendement conditionnel au regime | 1131 jours | La MM200 separe-t-elle deux populations de rendements ? |

---

## 5. Difficulte n2 — le contrat ne couvre pas ce type de strategie

### Le probleme, precisement

`core/contracts/strategy.py` modelise une decision comme `Signal(entry, stop,
target)`. **R3 impose stop non nul** ; `__post_init__` leve sinon. Le moteur
`core/backtest/engine.py` ne connait que trois sorties : **SL**, **TP**, ou fin de
tranche (RESIDUAL / EOD).

Or Trend core :

- est **toujours investie** — il n'existe pas d'etat flat ;
- **change d'instrument**, ce qu'un backtest mono-symbole ne peut pas representer ;
- a pour **unique condition de sortie la bascule de regime**, qui n'est ni un niveau
  de prix ni une duree fixe.

Il n'existe donc **aucune facon d'exprimer la sortie reelle** dans le moteur commun.
Un stop ne peut pas etre place la ou la MM200 sera dans 40 jours.

### Les options, et celle qui est retenue

| Option | Evaluation |
|---|---|
| **A — stop catastrophe large** | Le Signal devient valide, mais **la sortie reste fausse** : le moteur garde la position au-dela de la bascule. Les chiffres produits ne sont **pas** ceux de la strategie |
| **B — un trade par periode de detention, sortie = bascule** | Modelisation correcte. **Le moteur ne sait pas le faire** : pas d'ordre de sortie sur signal, et `max_hold_bars` (duree fixe) ne convient pas a une duree variable — il n'est de toute facon pas expose par `run_walk_forward` |
| **C — documenter que le contrat ne couvre pas cette famille** | **Conclusion architecturale, et livrable en soi** |
| **D — bricoler un faux stop pour satisfaire le validateur** | **Refuse.** Malhonnete |

**Decision : C, avec A comme volet de transparence.**

1. `strategy.py` est implementee pour de vrai, sous-classe `StrategyModule`, respecte
   R1..R10, passe la causalite et le walk-forward — **avec le stop catastrophe de
   l'option A**, dont la nature est ecrite dans le champ reason de chaque signal.
2. **Les chiffres du walk-forward sont publies en les qualifiant** : ils mesurent
   la qualite du moment d'entree en regime, avec un plancher de desastre, pas la
   strategie. Ils ne servent **pas** de base au verdict.
3. **La mesure qui fait foi** est une comptabilite de courbe d'equity
   (`backtests/run_analysis.py`), seule capable de representer une position toujours
   investie qui change d'actif, et seule capable de produire les benchmarks buy &
   hold. Ce n'est pas un moteur de backtest concurrent (R9) : elle ne simule ni stop,
   ni cible, ni file d'ordres — **il n'y en a pas dans cette strategie**. Elle applique
   des rendements journaliers a un actif detenu et facture le spread aux bascules.

### Remontee architecturale (pour core/, hors de mon perimetre)

> Le contrat Signal suppose qu'une strategie est **episodique** (entree ->
> invalidation -> objectif). Il ne peut pas exprimer une strategie **d'allocation** :
> toujours investie, sortie sur signal, multi-instruments. Toute la famille
> rotation / commutation de regime — dont **2 des 5 survivants de cette source**
> (Trend core et Rotation 52 semaines) — est aujourd'hui hors du domaine de la
> plateforme.
>
> Ce qui manquerait : un signal de **sortie** (ou un exit_signals), et un backtest
> multi-symbole a exposition unique.

**Anomalie reperee dans `core/backtest/engine.py` (~ligne 224)** — non utilisee ici,
signalee par honnetete : quand `max_hold_bars` est renseigne et que la sortie
temporelle se declenche, `exit_at = idx[limit-1]` mais `exit_price = last_close`,
c'est-a-dire `closes[n-1]`, la fin de **tranche** et non la fin de **detention**.
Meme famille que le bug `closes[-1]` documente en en-tete du module. Aucune de nos
mesures n'emploie `max_hold_bars`.

---

## 6. Difficulte n3 — le caveat de l'auteur est le coeur du test

L'auteur ecrit lui-meme que *le repli sur GLD tient en partie a la vigueur recente
de l'or, et que 2005-09 aurait plutot favorise un repli en cash*.

C'est **exactement** le piege attrape sur USDJPY : +69,7 R long contre -10,0 R short,
un pari directionnel deguise en systeme.

Notre fenetre 2021-2026 contient un bull market majeur de l'or. Si la jambe GLD porte
l'essentiel du resultat, la strategie n'est pas un systeme de regime : c'est **du beta
or avec un habillage MM200**.

### Trois diagnostics obligatoires, definis maintenant

1. **Attribution par jambe.** Contribution de la jambe NASDAQ vs jambe XAUUSD, en
   absolu **et par jour de detention** (le PnL total d'une jambe depend mecaniquement
   du temps passe dedans — cf. ne jamais juger un filtre sur le PnL total).
2. **Variante cash.** Rester hors marche sous la MM200. Si elle fait presque aussi
   bien, **la jambe or n'apporte rien** et le caveat de l'auteur est confirme.
3. **Controle long/short.** Il est ici **degenere et il faut le dire** : la strategie
   est **100 % longue en permanence**, par construction. Elle n'a jamais de short. Le
   controle directionnel ne peut donc pas la disculper — il la classe d'office du cote
   exposition directionnelle, et c'est pour ca que le benchmark buy & hold est le
   seul juge.

---

## 7. Hypothese testable et criteres d'invalidation

### L'hypothese

> **H** — Le filtre cloture au-dessus / en dessous de la MM200 separe deux
> populations de rendements journaliers suffisamment differentes pour que l'allocation
> commutee produise, **apres couts**, un couple rendement/risque superieur a celui d'un
> simple buy & hold sur l'un des actifs.

### Ce qui invaliderait la strategie — fixe avant les mesures

| # | Condition d'invalidation | Verdict induit |
|---|---|---|
| I1 | CAGR inferieur au buy & hold NASDAQ **et** Sharpe ne le depassant pas nettement | `PAS D'EDGE` — n'a pas battu l'effort zero |
| I2 | Le resultat vient tres majoritairement de la jambe XAUUSD (par jour de detention) | Beta or deguise — au mieux `NON CONCLUSIF`, jamais `EDGE CONFIRME` |
| I3 | La variante cash fait aussi bien ou mieux | La regle testee n'est pas celle qui produit le resultat ; caveat de l'auteur valide |
| I4 | Rendements journaliers au-dessus et en dessous de la MM200 statistiquement indiscernables | Le filtre ne filtre rien |
| I5 | Le resultat depend du choix exact de la periode de MM (100/150/200/250) | Sur-ajustement — pas de plateau |

### Ce qui ne pourra **jamais** etre conclu ici

- Un `EDGE CONFIRME` fonde sur le comptage de trades (13 episodes, §4).
- Une validation de robustesse inter-regimes : **l'auteur dispose de ~50 ans, nous de
  5**, et nos 5 ans ne contiennent **aucun marche baissier durable** (2022 est une
  correction de 10 mois, pas 2000-2002 ni 2007-2009). Or c'est precisement dans ces
  regimes-la que la MM200 est censee gagner sa vie. **Limite n1, irreductible.**

---

## 8. Economie du trade — le peage, chiffre avant d'implementer

Le cout ne se compare pas a une distance de stop (il n'y en a pas) mais au
**rendement de la periode de detention**.

| Instrument | pip | spread | demi-spread | prix median | aller-retour |
|---|---|---|---|---|---|
| NASDAQ | 0,1 | 8,0 pips | 0,40 | 17 371 | **0,0046 %** |
| XAUUSD | 0,01 | 25,0 pips | 0,125 | 2 040 | **0,0123 %** |
| SP500 | 0,1 | 5,0 pips | 0,25 | 4 938 | **0,0101 %** |

Une bascule = sortie d'un actif + entree dans l'autre ~ **0,017 %**.
A 2,56 bascules/an mesurees : **~ 0,04 % par an.**

> **Le peage est negligeable — environ 1/800e du CAGR annonce.** Difference
> structurelle avec le cas S5/H1 (drag 8,57 %, penalite 2,14 points de WR) : ici le
> cout de transaction ne peut **pas** etre la cause d'un echec, ni l'excuse d'un succes.
>
> Corollaire annonce d'avance : **l'ablation du spread sera un non-evenement.** Elle
> sera faite quand meme — diagnostic obligatoire — mais son resultat est previsible et
> il faudra le dire au lieu de le presenter comme une decouverte.

Le vrai cout non modelise n'est pas le spread : c'est le **swap/financement** sur des
positions detenues des mois (CFD indice et or spot), non modelise par la plateforme.
Sur une detention permanente, potentiellement **plusieurs points de CAGR**. Limite a
porter au verdict.

---

## 9. Tableau de reproductibilite, composant par composant

| Composant | Realisable ? | Substitution | Degradation |
|---|---|---|---|
| Univers QQQ | **Oui** | NASDAQ CFD `#NAS100` | Indice prix : pas de dividendes (~-0,5 pt de CAGR vs QQQ) |
| Univers GLD | **Oui** | XAUUSD spot | Pas de frais d'ETF ; swap non modelise |
| MM200 sur la cloture | **Oui** | identique | Close D1 broker != close cash 16:00 ET |
| Signal a la cloture | **Oui** | identique | — |
| Execution a l'ouverture suivante | **Oui** dans la comptabilite d'equity ; **non** dans le moteur commun | Le moteur entre au close de la barre de signal | Ecart d'un demi-jour sur 13 evenements — mesure et rapporte |
| Position 100 % permanente | **Non** dans le moteur commun | Comptabilite d'equity | Voir §5 |
| Sortie sur bascule de regime | **Non** dans le moteur commun | Comptabilite d'equity | Voir §5 |
| Absence de stop | **Non** (R3 l'interdit) | Stop catastrophe declare comme tel | Le volet moteur ne mesure pas la strategie ; publie comme tel |
| Validation sur 50 ans | **Non** | Aucune | **Irreductible.** Limite n1 |
| Stress 2000-2009 | **Non** | Aucune | **Irreductible.** Aucun marche baissier durable dans l'echantillon |

---

## 10. Plan de mesure

Grille volontairement minuscule — la source n'a **qu'un** parametre reel.

```
ma_len   in {100, 150, 200, 250}      200 = la valeur de la source
buffer   in {0,0 %, 0,5 %, 1,0 %}     bande morte anti-oscillation autour de la MM
                                       (0,0 % = la regle litterale)
                                   ->  12 configurations
```

**12 configurations -> ~0,6 reussite attendue par pur hasard.** A reporter partout.

Sequence :

1. `python -m core.validation.causality --strategy s04_aipathways_trendcore --save` — **bloquant**
2. Walk-forward ancre -> `backtests/anchored_wf.txt` (publie qualifie, cf. §5)
3. Comptabilite d'equity -> CAGR / Sharpe / DD / bascules, contre **buy & hold NASDAQ, XAUUSD et SP500**
4. Attribution par jambe, en absolu **et par jour de detention**
5. Variante cash
6. Ablation du spread (resultat prevu : nul, cf. §8)
7. Controle long/short (degenere, cf. §6 — a enoncer, pas a maquiller)
8. Test de plateau sur ma_len et buffer
9. `research/VERDICT.md`

---

## 11. Ce que je m'interdis

- Conclure `EDGE CONFIRME` sur 13 episodes, quelle que soit la beaute de la courbe.
- Presenter les chiffres du moteur comme etant ceux de la strategie (§5).
- Chercher la periode de MM qui sauve le resultat.
- Omettre un benchmark buy & hold qui battrait la strategie.
- Traiter l'ablation du spread comme une decouverte alors que son issue est calculee
  d'avance (§8).
