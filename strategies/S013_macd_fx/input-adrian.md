# input-adrian — S013 MACD FX Design Search (extrême MACD)

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S013 · magic `130013`
- **Source** : Idée Adrian (mandat : « développe une stratégie MACD gagnante sur forex »), prolongement de s12
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s13_macd_fx\` (lecture seule)

## Principe (résumé)
Exploration de conception : 756 cellules testées (3 familles × 2 sens × 9 paires, D1, 20 ans de données MT5 Swissquote). Seule survivante : famille C « extrême MACD » — quand MACD/ATR passe sous son 10e percentile glissant sur 252 jours, entrée LONG au close, cible +1,5 ATR, stop −1,5 ATR. Paire survivante : AUDCAD (EURJPY en observation d'hypothèse). Le motif n'existe qu'en D1 : la variante H4/session est négative.

## État hérité du prototype
- **Statut manifest** : `PAPER` — config figée par le hold-out (ne pas re-régler), symboles `AUDCAD, EURJPY`, `lookback 252`, `q 0,10`, sortie `atr_1.5_1.5`.
- **Verdict (research/VERDICT.md)** : **EDGE CANDIDAT (faible)** — la seule candidate positive du dépôt.
- **Chiffres clés vérifiés** :
  - Exploration AUDCAD : +0,093 R/t net × 130 trades (≈ 7/an), OOS 4/4 fenêtres positives, percentile témoin 100 (5/5 graines), voisinage 4/4.
  - Transfert à froid poolé sur les 8 autres paires : +0,020 R/t × 1 226 trades (positif — inédit dans les dossiers du dépôt).
  - Hold-out scellé 18 mois, ouvert une seule fois : +0,58 R/t × 11 trades (WR 81,8 %), percentile témoin 96.
  - Familles A (s12 transposé) et B (croisements) : mortes ; côté SHORT de C : négatif.
- **Réserves déclarées** : effectif hold-out de 11 trades (limite dominante) ; la jumelle EURJPY (+0,49 R/t au hold-out, percentile 74) n'a pas battu son beta long aléatoire ; asymétrie long/short affaiblit le récit « retour à la moyenne » pur ; ~7 trades/an = jugement lent.
- **Suivi en cours** : forward scellé zéro argent armé (`studies/s13_forward`, 0 trade clos à ce jour, ~7 trades/an attendus), motif calqué sur gold_forward. Verdict aux règles écrites d'avance.
- **Rigueur héritée** : protocole de falsification gelé avant backtest (commit `6405c80`), liste close des candidates avant ouverture du hold-out (commit `5fbedec`), R1/R5 passés 36/36.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC, documenté).
- Respecter le scellé du forward en cours : la config survivante est figée ; toute amélioration s'explore à côté, jamais en re-réglant la cellule hold-out.
