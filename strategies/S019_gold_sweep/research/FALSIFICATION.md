# S019 — critères de falsification

**Écrit le 2026-09-06, AVANT toute exécution du harnais.** C'est la seule
garantie qui vaille : un critère rédigé après lecture des résultats n'est pas un
critère, c'est une justification.

---

## L'hypothèse, en une phrase

Sur XAUUSD, une entrée déclenchée par un **balayage de liquidité suivi d'une
réintégration**, protégée par un **stop structurel** placé sous l'extrême du
balayage, produit une espérance positive nette de frais.

## D'où elle vient

Elle ne vient pas d'un discours mais d'une mesure faite le 2026-09-06 sur
20 entrées réelles de la source, extraites de ses lives publics et alignées sur
nos barres M5 :

| Fait mesuré | Valeur | Référence |
|---|---|---|
| Entrées précédées d'un balayage | 60 % contre 39 % au hasard, p = 0,047 | `VERDICT_croisement-entrees.md` |
| Mèche de rejet à l'entrée | p = 0,136 — **non significatif** | idem |
| Stop métrique 1,5 × ATR(H1) | couperait 40 % de ses entrées dans l'heure | idem |
| Distance atteinte en sa faveur | 60 % atteignent 1,5 × ATR | idem |
| Délai après choc d'annonce | T+6 min médian | `VERDICT_annonces.md` |

Le raffinement « mèche de rejet » est **volontairement exclu** du code : mesuré
non significatif, l'inclure serait coder une croyance.

## Ce qu'on ne reproduit pas, et pourquoi ça compte

Les **clôtures partielles** et le **stop suiveur** ancré sur la zone jaune sont
le cœur de sa gestion, et probablement l'essentiel de son avantage. Le moteur
commun ne sait pas les exprimer (TCK-014). S019 mesure donc son **entrée** avec
une sortie que l'on sait inférieure à la sienne.

Conséquence directe sur la lecture des résultats : **un échec de S019 ne réfute
pas sa méthode**, il réfute « son déclencheur d'entrée avec notre sortie ». Seule
une réussite serait concluante dans les deux sens. Cette asymétrie est admise
d'avance et ne sera pas oubliée au moment de conclure.

---

## Les seuils

### Ce qui vaut réussite

Toutes ces conditions, simultanément, sur une même cellule :

1. **Hors échantillon** — au moins une cellule STRICT au walk-forward ancré, avec
   ≥ 20 trades hors échantillon.
2. **Témoin** — percentile ≥ 90 contre le bras aléatoire à gabarit identique.
   En dessous, le résultat est un effet du dispositif de risque, pas du signal.
3. **Coût absorbé** — R/trade positive **à spread réel (52 pips)**, pas seulement
   au spread catalogue (25 pips). Une cellule qui ne survit qu'au tarif fictif
   est morte.
4. **Multiplicité** — 16 cellules à 5 % donnent ≈ 0,8 réussite par pur hasard.
   **Une seule** cellule STRICT ne prouve rien : il en faut ≥ 3, ou une cellule
   dont le percentile témoin dépasse 97.

### Ce qui vaut échec

L'une de ces conditions suffit :

- Aucune cellule STRICT, ou aucune ne dépasse le percentile 90 du témoin.
- Le coût de bord dépasse **35 % du R médian** — la stratégie paie alors ses
  frais avant de parier, et aucun réglage de `tp_r` ne rattrape ça.
- Le signal disparaît entre plein échantillon et hors échantillon (surajustement
  du walk-forward).
- Les résultats tiennent à moins de 20 trades hors échantillon par cellule.

### Ce qui vaut échec du *dispositif*, pas de l'hypothèse

À distinguer d'un vrai échec, et à traiter autrement :

- R1 en défaut → bogue de causalité, on corrige et on remesure.
- Moins de 20 trades sur **toutes** les cellules → la règle est trop rare en M15 ;
  remesurer en M5 (`S019_TF=M5`) avant de conclure quoi que ce soit.
- Résultat positif porté par une seule année → non concluant, pas positif.

---

## Ce qui ne sera pas fait

- **Aucun ajout de commutateur après lecture des résultats.** La grille est
  arrêtée à 16 cellules. Si l'envie vient d'en ajouter un « pour voir », c'est le
  signe qu'on est en train de pêcher.
- **Aucun réglage fin de `sweep_lookback` ou `sweep_window`.** Ils sont fixés à
  60 et 5 par la mesure, pas optimisés.
- **Aucune promotion PAPER** quel que soit le résultat : décision Adrian
  exclusivement (R10).

---

## Ce que le résultat, quel qu'il soit, nous apprendra

| Issue | Lecture |
|---|---|
| Réussite | Le déclencheur porte, même avec une sortie dégradée. TCK-014 devient prioritaire : sa vraie sortie ne peut qu'améliorer. |
| Échec avec coût > 35 % du R | Le stop structurel est incompatible avec nos frais sur XAUUSD. La question devient celle du courtier, pas de la stratégie. |
| Échec avec coût acceptable | Le déclencheur seul ne suffit pas. Ce qui manque est ailleurs : la porte directionnelle (zones fatidiques) ou la gestion (TCK-014). |
| Non concluant, trop peu de trades | Descendre en M5 et remesurer avant tout jugement. |
