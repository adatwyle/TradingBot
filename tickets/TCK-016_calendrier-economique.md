---
id: TCK-016
from: cc-S018
to: cc-spec
status: open
blocking: false
created: 2026-09-06
---

## Question

Nos données (`core/data/source.py`, MT5 Swissquote) contiennent des barres OHLC et
rien d'autre. Aucune stratégie ne peut donc aujourd'hui exprimer une règle du type
« ne pas entrer dans les X minutes autour d'une annonce », ni son inverse
« n'entrer que là ».

Deux besoins concrets, déjà rencontrés :

1. **S018 / méthode Doud** — la source revendique d'entrer **2 minutes avant**
   l'annonce (@ 10:54) et construit sa semaine sur le calendrier (@ 25:34). Faute de
   calendrier, l'hypothèse D9 n'a pas pu être testée du tout — elle est absente du
   dossier, pas infirmée.
2. **Hygiène générale** — plusieurs dossiers du dépôt supposent implicitement que les
   trades pris pendant une annonce sont « comme les autres ». Sur l'or, une annonce
   déplace le prix de l'ordre de 3000 points (≈ 30 $) en quelques minutes : ce n'est
   pas la même population statistique.

Un demi-calendrier serait pire que rien : le NFP seul est déterministe (premier
vendredi du mois, 8h30 ET), mais CPI, FOMC et les décisions de la BCE ne le sont pas.
Coder le seul NFP donnerait l'illusion d'un filtre d'annonces tout en en laissant
passer l'essentiel.

## Proposition de résolution

Spécifier une source de calendrier économique dans `core/data/` :

- **A (préférée)** — fichier historique versionné (`data/calendar/econ_<année>.csv` :
  timestamp UTC, pays, événement, importance), alimenté une fois depuis une source
  publique, puis figé. Avantages : reproductible, hors ligne, backtestable, aucun
  appel réseau dans le chemin de mesure. Inconvénient : à rafraîchir à la main.
- **B** — API tierce interrogée au runtime. Rejetée par cc-S018 : une donnée qui
  change entre deux exécutions rend les backtests non reproductibles, et le projet a
  déjà payé ce genre de dépendance.

Contrat minimal attendu : `is_near_event(ts, minutes_before, minutes_after,
min_importance) -> bool`, causal par construction (le calendrier est connu à l'avance,
c'est sa seule propriété commode), et **testé sur un jeu figé**.

À trancher : la profondeur d'historique nécessaire (nos barres remontent à 2021-08),
et si l'importance est une échelle publiée ou une convention interne.

## Réponse

<cc-spec>
