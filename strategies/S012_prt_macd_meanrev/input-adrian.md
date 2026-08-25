# input-adrian — S012 Daily MACD Mean Reversion (ProRealTime)

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S012 · magic `130012`
- **Source** : YouTube — chaîne ProRealAlgos / blog ProRealTime (« If I Started Algo Trading in 2026 ») ; algo gratuit, release publique 2022-06-21
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s12_prt_macd_meanrev\` (lecture seule)

## Principe (résumé)
Mean reversion classique D1, long-only, sur indices : acheter la faiblesse quand le MACD baisse depuis 5 jours et est négatif, que le close est inférieur au close de la veille et se situe près du bas du trading range 20 jours ; sortir dès que le close reprend le plus haut de la veille. La source n'a pas de stop — le prototype impose un proxy 10 ATR (règle R3). SP500 = marché source ; NASDAQ et DAX en transfert à froid.

## État hérité du prototype
- **Statut manifest** : `PAPER` — uniquement parce qu'un forward IA scellé est armé (`studies/macd_ai_paper`). Le manifest précise explicitement que PAPER ne vaut PAS validation.
- **Verdict recherche (commit 773cc4a)** : **PAS D'EDGE**. R1 (causalité) et R5 (conformance) passés ; falsifications gelées avant tout backtest.
  - **F1 déclenchée** : témoin aléatoire long-only à géométrie identique — percentile 51,5 sur SP500 (seuil < 95).
  - **F2 déclenchée** : espérance négative à spread nul — −0,0062 R/trade sur 38 trades (SP500, plein échantillon, config défaut).
  - **F3 déclenchée dans les deux datasets** (test structurel LONGHIST close-only) : SP500 1927-2026, 464 trades — les jours en position font +0,8 %/an contre +6,4 %/an au buy & hold ; NASDAQ 1971-2026, 257 trades — −3,5 %/an contre +10,6 %/an.
  - Le « performed quite well since June 2022 » de la source est reproduit et expliqué : beta pur (un témoin long aléatoire de même géométrie fait pareil sur 2022-2026).
  - Filtre vendredi (l'« amélioration » de la source) : dégrade le R/trade sur SP500 (−0,0126 vs −0,0072) — bruit in-sample, comme anticipé au gel.
  - Risque sans stop quantifié : pire trade −26,3 % en 3 jours (octobre 1987) — profil « WR 85-95 %, pertes rares mais énormes ».
- **Forward IA** : verdict du rejeu accéléré (résumé cc-support) — **NE PAS ARMER l'IA**.
- **Piste transférable notée au VERDICT** : l'entrée « RSI 14 < 30, D1, indices » (même famille, déclencheur différent, deux sources convergentes) — à traiter comme stratégie dédiée séparée, pas comme extension de S012.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC dédié, documenté ; l'archivage n'est pas préjugé malgré le verdict hérité).
- Statuer sur le forward scellé hérité (`macd_ai_paper`) à la lumière du verdict « NE PAS ARMER l'IA » avant tout nouveau travail d'amélioration.
