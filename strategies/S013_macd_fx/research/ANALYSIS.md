# Analyse — s13_macd_fx « MACD Forex Design Search »

Source : mandat Adrian (verbatim : « teste cette méthode [Daily MACD mean
reversion] sur des paires forex également » puis « développe une stratégie MACD
gagnante sur des paires forex — débrouille-toi pour la rendre gagnante »).
Trader : interne. Magic : 130013.

---

## 0. Le cadrage honnête (à lire avant les chiffres)

« Se débrouiller pour la rendre gagnante » a deux lectures. La mauvaise :
ajuster des paramètres jusqu'à ce que le backtest soit vert — c'est fabriquer
un faux positif qui perdra en réel, et le harnais de ce projet est précisément
construit pour l'empêcher (13 verdicts le prouvent). La bonne, qui est le
mandat exécuté ici : **explorer LARGEMENT et honnêtement l'espace de
conception MACD sur forex**, avec des protections statistiques à la hauteur de
la largeur de la recherche, et livrer ce qui survit — ou le constat chiffré
que rien ne survit. Les deux issues sont des livrables de pleine valeur.

RÈGLE CENTRALE : plus la recherche est large, plus le seuil de preuve monte.
Sur ~750 cellules il Y AURA des cellules vertes. La question n'est jamais
« y a-t-il du vert » mais « qu'est-ce qui survit au témoin, au voisinage, aux
graines, et au hold-out scellé ».

## 1. Ce que le projet sait déjà (état de l'art interne)

| Dossier | Enseignement réutilisé ici |
|---|---|
| s12 (MACD mean reversion D1 indices) | PAS D'EDGE long-only indice, mais **le terrain D1 est bon** (péage 0,46 pt de WR) et le harnais (gel → WF → témoin → hold-out) est le bon. La transposition FX est précisément la demande initiale d'Adrian. |
| s91 (scratch H1 forex) | Un signal de session brut réel (+0,05 R/t) **tué par le péage H1** (facteur ~1,5 du besoin). → D1 en priorité absolue, H4 en variante unique. |
| s90 (fade de l'échec, clos) | Le fade d'extension **de prix** en ATR est réfuté hors découverte (−0,15 R/t net, 1 337 trades). Notre famille C fade une extension **d'indicateur** (percentile glissant du MACD/ATR, D1, sans déclencheur d'échec) — différence déclarée a priori au §4.3, pour ne pas re-fabriquer la sélection réfutée. |
| Synthèse aipathways + verdicts trend (s01, s04, s06) | Le momentum/croisement MACD est probablement mort — il est dans la grille comme RÉFÉRENCE INTERNE, pas comme espoir. S'il ressortait meilleur que la mean reversion, c'est une information en soi. |
| s93 / rejeu | La gestion fine détruit. → sorties simples uniquement (cible symétrique s12, cible/stop ATR, temps fixe). |

## 2. Données et instruments

- **Source** : MT5 Swissquote D1, ~20 ans (2006-08 → 2026-08, ≈ 6 200 barres
  par paire), cache `C:\db\tbot\bars_cache\*_D1_7300d.pkl`, épinglé par les
  runners (`max_age_hours` énorme) pour la reproductibilité. H4 (~32 000
  barres) disponible pour LA variante session.
- **Univers (9 paires)** : EURUSD, USDJPY, USDCHF, AUDUSD, USDCAD, EURJPY,
  CHFJPY, EURCHF, AUDCAD. Toutes au catalogue `core/data/instruments.py`.
  **GBPUSD est ABSENT du catalogue** (pas de spec broker) — l'ajouter serait
  toucher `core/`, interdit ici : exclu, signalé au coordinateur.
- **Coupe des données** : toute barre datée ≥ 2026-08-16 est écartée (barre
  hebdo partielle). Fin de données effective : 2026-08-15.
- real_volume = 0, pas de carnet : aucune famille testée n'en a besoin.

## 3. Pourquoi le forex change (ou pas) la donne vs s12

- **Pas de dérive séculière** : un indice monte structurellement (le témoin
  long-only de s12 absorbait ce beta). Une paire FX est un prix relatif sans
  drift de long terme comparable → le long-only n'a AUCUNE justification
  structurelle. **Les deux sens, toujours, mesurés séparément.**
- **Péage D1 mesuré a priori** (§Économie du FALSIFICATION) : ~1-4 % du R pour
  un stop 3 ATR — négligeable. Le terrain permet à un petit edge de survivre.
- **Régimes** : 20 ans couvrent 2008, 2011 (plancher EURCHF), 2015 (dé-peg),
  2022 (dollar fort), etc. EURCHF a un régime administré 2011-2015 — les
  chiffres par paire se lisent avec ça en tête.

## 4. L'espace de conception (familles, pas cellules infinies)

Constantes hors grille (déclarées avant toute mesure) : MACD 12/26/9 (ligne =
EMA12−EMA26 ; signal = EMA9 de la ligne), ATR 14, warmup 60 barres, entrée au
close de la barre de signal, stop TOUJOURS renseigné (R3).

### 4.1 Famille A — mean reversion s12 transposé (la demande initiale)
LONG : ligne MACD en baisse `n_down` jours consécutifs ET MACD < 0
(optionnellement close dans le bas du range 20 j). Sortie « reprise » :
cible = max(high[jour], close[veille]) — la sortie s12. **MIROIR SHORT
systématique** : MACD en hausse `n_down` jours ET MACD > 0, cible =
min(low[jour], close[veille]).

### 4.2 Famille B — croisement (référence interne)
Croisement ligne/signal ou ligne/zéro, entrée dans le sens du croisement,
sorties ATR ou temps fixe. Trois sources concordantes + nos verdicts trend la
donnent morte — elle sert d'étalon : tout candidat A ou C doit AU MOINS la
dominer.

### 4.3 Famille C — extrême MACD + retour (fade d'extension d'indicateur)
MACD normalisé par l'ATR (comparable à travers 20 ans) sous son percentile
glissant bas → LONG ; miroir au-dessus du percentile haut → SHORT.
**Différences déclarées vs s90 (motif clos)** : (a) l'état est un extrême
d'OSCILLATEUR relatif à sa propre histoire (percentile glissant adaptatif),
pas une excursion de prix en ATR depuis un extrême récent ; (b) D1, pas H1 ;
(c) aucune condition « échec/retournement » — on fade l'extension elle-même ;
(d) les deux sens dès la conception. Si C ne survit pas, cela ÉTEND la
conclusion s90 à la version indicateur ; si C survit, ce n'est pas une
résurrection de s90 mais un objet distinct — dans les deux cas l'information
est propre parce que la différence est posée ICI, avant les chiffres.

### 4.4 Sorties (communes, petites, justifiées a priori)
- `sym` : cible de reprise s12 (voir 4.1), stop `sl_atr` ∈ {3, 10} (10 = proxy
  « sans stop », chiffre le gap au lieu de l'ignorer) ;
- `atr` : cible/stop ATR ∈ {(1.5, 1.5), (2, 3)} — les géométries défendables
  déjà utilisées par s90/s09 ;
- `hold` : temps fixe `max_hold_bars=20` + stop 3 ATR, cible None (famille B
  seulement — le momentum se juge à horizon fixe).
PAS de gestion fine (trailing, break-even, pyramidage) : s93/rejeu ont montré
qu'elle détruit.

### 4.5 Variante session (UNE, déclarée)
H4, fenêtre d'entrée limitée au chevauchement Londres/NY (heures serveur
12-19, calibration `docs` : pic ~16h serveur), appliquée UNIQUEMENT à la
meilleure configuration D1 par candidate finale, à titre informatif. C'est la
seule synergie plausible (signal session brut réel de s91) — une variante,
pas une dimension de grille.

## 5. Hypothèse testable

Sur forex D1, un état MACD de sur-extension (A : élan baissier persistant sous
zéro ; C : extrême de distribution) précède un retour vers l'équilibre
suffisant pour payer spread + slippage, dans AU MOINS un sens, de façon stable
à travers les fenêtres, supérieure au hasard à dispositif de risque identique
(témoin p ≥ 95), robuste au voisinage de paramètres et confirmée UNE fois sur
un hold-out scellé de 18 mois. La famille B teste l'hypothèse inverse
(persistance de l'élan) comme référence.

## 6. Reproductibilité

Tout est réalisable avec nos barres OHLC : MACD, ATR, ranges, percentiles
glissants causaux. Aucune substitution dégradante. Deux dégradations mineures
héritées de s12, déclarées : cible « reprise » statique (posée au signal, pas
recalée chaque jour) et remplissage de cible au toucher intrabar.

## 7. Ce qui est figé où

Le protocole complet (seuils, grille exacte, règle de sélection des candidates,
hold-out scellé) est dans `research/FALSIFICATION.md`, gelé et commité AVANT le
premier backtest. Le présent document ne sera plus modifié après le gel, hormis
la section verdict croisé du VERDICT.
