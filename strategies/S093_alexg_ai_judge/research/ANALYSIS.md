# Analyse — AlexG AI Judge (s93)

Source : https://www.youtube.com/@fxalexg__ (fxalexg, 1,3 M abonnés)
Corpus : 27 transcripts analysés — la décomposition complète vit dans
`docs/sources/fxalexg/SYNTHESE.md` (spec v2 §1, comptabilité instruite §2,
falsifications recommandées §3). Ce fichier ne la duplique pas ; il documente
ce qui est PROPRE à s93.

## L'hypothèse testable

s01 a montré que la mécanique « structure + zones » d'Alex, prise en paquet,
n'a pas d'edge (−0,10 R/trade, indiscernable d'une pièce à coût nul). Mais Alex
ne prend que ~26 % de ce qu'il identifie (5/19 sur 4 semaines documentées), via
un grading par confluences : 1 confluence = 10 %, trades notés 50-100 %.

**Hypothèse s93 : la valeur, si elle existe, est dans la SÉLECTION, pas dans le
détecteur.** Test : un juge IA appliquant SA grille publique, en rejeu à
l'aveugle (sans ticker, sans date), sur les candidats du détecteur v2 —
bat-il une sélection aléatoire de même taux ? Falsifications chiffrées
d'avance : `research/FALSIFICATION.md` (écrit avant le premier jugement).

## Architecture

1. **Détecteur v2** (`strategy.py`, magic 130093) — portes mécaniques de la
   spec 2025 (2 TF consécutifs sync, AOI ≤60 pips ≥3 touches corps W/D dans le
   dernier HH/HL, prix revenu DANS la zone, shift H1 par body close, SL
   structurel, TP au prochain point de structure daily, R:R ≥ 2, lun-jeu).
   Confluences objectivables consignées par candidat (largeur/touches de zone,
   netteté du break en ATR, engulfing, H&S break+retest de neckline, niveau
   rond, EMA, session…). R1 passé couche indicateur incluse, R5 passé.
2. **Rejeu à l'aveugle** (`judge/`) — anonymisation (prix en unités d'ATR,
   heures -> sessions, ordre mélangé graine 20260816, mapping séparé jamais
   montré au juge), 8 sous-agents juges, grille = ses 10 confluences + 2 COT,
   mesure par permutation (200 tirages, même graine).

## Substitutions assumées (dégradations honnêtes)

| Composant source | Substitution | Dégradation |
|---|---|---|
| Paires GBPJPY, GBPCHF | GBPUSD, EURJPY (données/catalogue disponibles) | couverture GBP/JPY conservée, crosses exacts non testés |
| TF d'entrée 2H/1H/30m | H1 uniquement | granularité du déclencheur réduite |
| « Touches en corps » de l'AOI | pivots-corps (k=2) groupés ≤60 pips | un pivot = une touche rejetée ; touches sans pivot non comptées |
| Période EMA (jamais publiée) | EMA 50 H1 | inconnue par construction |
| « Signal secret » d'entrée | absent (il le dit lui-même : jamais publié) | on teste sa version publique, comme s01 |
| Grading pondéré (non publié) | 1 confluence = 10 %, non pondéré (sa description publique) | fidèle à ce qu'il décrit |
| Sortie discrétionnaire (jamais de TP posé, cf. SYNTHESE §2.1) | TP structurel posé (sa doctrine « set and forget ») | on teste la doctrine, pas la pratique filmée |

## Confluence « positionnement des traders » (addendum au mandat)

**Volet historique (backtestable proprement) : le COT CFTC uniquement.**
Position nette des non-commercials / open interest, percentile glissant 3 ans,
7 devises (EUR JPY CHF GBP AUD CAD + USD via l'indice ICE). Anti-fuite : la
donnée du mardi n'est utilisable qu'à partir du vendredi 15h30 ET
(`available_from = as_of + 3 j 22:30 heure serveur`) — jointure `<=` sur la
publication, jamais sur l'as-of. Deux champs par candidat : alignement
directionnel (différentiel de percentiles base−cotation dans le sens du trade)
et extrême (>90e / <10e). Contribution marginale mesurée séparément (F6).

**Volet live (phase paper future — design seulement, PAS dans le rejeu) :**
- Myfxbook Community Outlook et IG Client Sentiment : sentiment RETAIL, usage
  classiquement contrarien (la foule est majoritairement du mauvais côté des
  tendances). **Note honnête : leurs historiques point-in-time ne sont pas
  archivés publiquement -> non backtestables proprement, intégrables uniquement
  en prospectif** (journaliser la valeur au moment de la décision, dès le
  paper).
- Crypto (hors périmètre s93) : ratios long/short top traders des exchanges.
- Le COT reste la seule source de positionnement admissible en backtest.

## Ce que ce test ne peut pas voir

- Le « signal secret » et la pondération réelle de son grading.
- Sa sélection discrétionnaire d'AOI à l'œil (nos zones = clusters de pivots).
- Un seul régime macro (2021-2026), folds emboîtés, ~5 ans H1.
- Le juge est un LLM : même anonymisé, il n'est pas Alex — il applique la
  grille publique d'Alex, c'est précisément l'objet du test (mandat Adrian :
  « une IA qui le remplace lui »).
