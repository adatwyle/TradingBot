# input-adrian — S017 ireland_gex

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S017 · magic `130017`
- **Source** : YouTube — Nick Ireland, « Why I stopped trading price action & only use gamma exposure ($1k/day strategy) », https://www.youtube.com/watch?v=bXVHsViQuyE (22 juin 2026, 23 min)
- **Sources locales** : `sources/video/transcript.txt` (transcript complet horodaté) + `sources/video/frames/` (22 captures d'écran clés : carte GEX ITMatrix, zones gamma +/-, stack EMA, compressions, les 2 trades démontrés)
- **Pas de prototype G3** : stratégie nouvelle, ne vient pas de RobinBot.

## Principe (résumé)

Day trading directionnel sur **SPY** (options calls/puts courts terme dans la vidéo), piloté par les niveaux de **Gamma Exposure (GEX)** des dealers. Les market makers delta-hedgent mécaniquement leurs books d'options ; les strikes à forte concentration de gamma deviennent des niveaux où le prix réagit (rebond, aimant, ou accélération en cas de cassure). On ne trade QUE lorsque le prix est sur un niveau GEX majeur, dans le sens de la tendance EMA, sur cassure de compression confirmée par le volume.

## Les 5 composantes du système (checklist d'entrée — TOUTES vertes = setup A+)

1. **Niveau GEX majeur** : identifier en pré-market les plus grosses concentrations de gamma exposure par strike (carte GEX). Règle : prix pas à/proche d'un niveau majeur → pas de trade (« no man's land » interdit, peu importe la beauté du pattern).
2. **Environnement gamma** (donné par la carte) :
   - *Gamma positif* (dealers net long gamma → hedging contre le marché) : volatilité comprimée, tendances propres. Taille normale, objectif 2R complet, les pullbacks tiennent. Les gros niveaux positifs agissent comme des **aimants** (pinning).
   - *Gamma négatif* (dealers net short gamma → hedging avec le marché) : mouvements amplifiés, retournements violents. Taille réduite de 30-50 %, prise partielle à 1R au lieu de tenir 2R.
3. **Direction par stack EMA 9/21/50** :
   - 9 > 21 > 50 avec bon espacement = séquence haussière → calls uniquement.
   - 50 > 21 > 9 avec espacement = séquence baissière → puts uniquement.
   - EMAs entassées (chop) → pas de trade.
   - **Alignement multi-timeframe obligatoire** : la séquence du daily doit correspondre à celle de l'intraday (5 min).
4. **Déclencheur d'entrée** : compression / flag au contact du niveau GEX majeur, entrée sur la cassure avec **volume nettement supérieur** sur la bougie de cassure. Pas de spike de volume → on skippe systématiquement (exemple montré : cassure sans volume = fake-out évité).
5. **Risque** : max 1-2 % du compte par trade, calculé avant l'entrée. Stop structurel : sous les EMAs pour un long, au-dessus pour un short. Ratio minimal 2:1 sinon on passe. Stop jamais déplacé. En gamma négatif : réduction de taille supplémentaire.

Exemples démontrés dans la vidéo (frames 16-22) : niveaux 750 (nég., 60 M$ cumulés) / 755 (pos., 180 M$) → hold 750 = chemin vers 755 ; niveaux 735 / 745 (pos., >100 M$, aimant) → hold 735 = chemin vers 745. Cassure d'un niveau majeur à fort volume = flip résistance→support, information tradable aussi.

## Données et outils identifiés (analyse cc-support 2026-08-26)

- **itmatrixhq.com** = la plateforme GEX utilisée dans la vidéo. Free tier existant ; Basic 89.99 $/mois ; Pro 149.99 $/mois (inclut SPX/NDX/VIX, dark pool, accès API) ; **offre API dédiée 119.99 $/mois (REST, 120 req/min, 50k req/jour, live + tout l'historique, equities & ETFs)**. Dispose d'un replay historique intraday (STEP 5/10/15/30 min) — utile pour valider visuellement.
- **Gratuit pour démarrer** : chaîne d'options CBOE en différé (~15 min, CSV/JSON publics) + calcul GEX maison (méthodologie Perfiliev, repo GitHub `Matteo-Ferrara/gex-tracker`) ; dashboards gratuits GravityGEX, AlgoStorm, FlashAlpha.
- **Backtest historique** : FlashAlpha propose une API GEX historique minute pour SPY depuis 2018 (tier gratuit limité, tiers payants) ; ITMatrix API inclut aussi l'historique. À évaluer par cc-S017 (coût vs profondeur).
- **ninjagex.com/checklist** : checklist « 11 points » du même auteur, derrière une capture d'email — non extraite. Le contenu de la vidéo (5 composantes) suffit pour la V1 ; Adrian peut s'inscrire s'il veut la version exacte.
- **Swissquote** : accès de TRADING aux dérivés US (OPRA, CBOE) — exécution possible d'options SPY —, mais **aucune API de données de chaîne d'options** exploitable : Swissquote n'est pas une source de données pour cette stratégie.
- **TradingView** : pas nécessaire. Pas d'API data publique officielle ; les EMA 9/21/50 et le volume se calculent depuis des OHLCV SPY 5 min/daily sourcés librement (CBOE/Yahoo/Alpaca/Polygon).

## Attentes d'Adrian (2026-08-26)

1. **Reproduire et mettre en place la stratégie** telle que décrite, puis la **tester** (backtest), la **debugger**, la **perfectionner**.
2. **Tester toutes les variantes imaginables** pour la rendre profitable (paramètres, filtres, gestion, sous-régimes gamma +/-, seuils de volume, définitions de « niveau majeur », proxy sous-jacent vs options, etc.).
3. **Ajouter des idées d'amélioration propres**, de manière ciblée, une fois les lacunes identifiées (pas d'inventions avant d'avoir mesuré).
4. Objectif de sortie : stratégie **prête pour le paper trading live test** → Adrian décidera alors la mise en phase d'essais (promotion PAPER = décision Adrian uniquement, R4).
5. Cloisonnement et contrats R1-R10 applicables (causalité, stop obligatoire, backtester commun R9, manifest source de vérité, magic 130017).

## Points ouverts (avec préconisations cc-support)

- **Actif de backtest** : la vidéo trade des options SPY (levier), mais la logique des signaux est sur le sous-jacent. Préco : valider d'abord le signal sur SPY spot/CFD (mesurable proprement avec le backtester commun), puis modéliser la couche options si le signal est validé.
- **Backtester commun (R9) vs asset US intraday** : si le socle ne supporte pas encore SPY 5 min + niveaux GEX exogènes, ouvrir un ticket `tickets/` avec proposition (extension par cc-app plutôt que moteur privé).
- **Données GEX historiques** : commencer gratuit (CBOE + calcul maison pour le live ; FlashAlpha free pour l'historique) ; ne souscrire ITMatrix API que si la valeur est démontrée — décision d'abonnement = Adrian.
- **Horaires** : marché US 15:30-22:00 heure suisse ; la préparation pré-market (carte GEX + niveaux) se fait avant 15:30 CH.
