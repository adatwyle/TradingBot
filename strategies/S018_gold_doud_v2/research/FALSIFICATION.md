# FALSIFICATION — S018, or v2

> Ce qui tuerait chaque hypothèse. À lire **avant** `VERDICT.md`.
>
> **Statut d'honnêteté de ce fichier.** Les seuils et la lecture principale
> (effet marginal, effectif minimal, attente de multiplicité) étaient
> pré-enregistrés dans `manifest.yaml` et `backtests/run_wf.py`, commités avant
> la première exécution. Ce fichier les rédige explicitement. Il a été écrit
> **après** la première mesure : il ne peut donc pas se prévaloir d'un scellé
> comme celui de `studies/gold_forward/PROTOCOL.md`. Ce qu'il fixe engage la
> suite, pas le passé.

---

## 1. Le critère qui prime sur tous les autres

**Un ingrédient n'est retenu que si son effet marginal est positif en moyenne
sur les 16 cellules où il est actif, ET s'il survit hors échantillon avec un
effectif.** Une cellule isolée brillante ne sauve rien : 32 cellules produisent
**≈ 1,6 réussite par pur hasard** à 5 %, et les cellules ne sont pas
indépendantes — deux voisines partagent l'essentiel de leurs trades, ce qui rend
cette attente optimiste, pas conservatrice.

Seuil d'effectif : **20 trades hors échantillon**. En dessous, la case est vide,
pas gagnante. Le projet a déjà pris un « strict pass » sur 19 trades pour un
succès (`docs/METHODOLOGY.md`) ; l'intervalle de confiance du win rate contenait
le seuil de rentabilité.

---

## 2. Par hypothèse

| # | Hypothèse | Ce qui la valide | Ce qui la tue |
|---|---|---|---|
| **D1** long_only | effet marginal R/trade **> 0** et cellule long_only survivant en hors échantillon avec ≥ 20 trades | effet marginal ≤ 0, **ou** gain de R/trade payé par une dégradation du drawdown et du R total telle que le portefeuille n'y gagne rien |
| **D2** biais journalier | effet marginal > 0 **et** le filtrage ne se contente pas de retirer des trades perdants par réduction d'effectif | effet ≤ 0, ou gain qui disparaît dès qu'on compense la baisse du nombre de trades |
| **D3** canal sur les corps | effet marginal > 0 | effet ≤ 0 — l'affirmation « structure et non mèche » serait alors fausse **dans cette traduction** (elle peut rester vraie dans la sienne) |
| **D4** entrée à l'équilibre | effet marginal > 0 **et** ≥ 20 trades hors échantillon sur au moins une cellule d'équilibre | effet ≈ 0, ou effet positif porté par des cellules à effectif mince |
| **D5** sessions | effet marginal > 0 | effet ≤ 0 |
| **D10** sortie au temps | R/trade amélioré à effectif comparable | R/trade dégradé |

---

## 3. Ce qui tuerait la v2 dans son ensemble

1. **La cellule neutre cesse d'égaler la v1** → la grille n'est plus lisible.
   Vérifié à chaque exécution (`grid.txt` § 1) et par test. Non négociable.
2. **R1 échoue sur une cellule** → tout chiffre du dossier est retiré jusqu'à
   correction. Le mode `equilibrium` est le suspect désigné.
3. **Aucun ingrédient n'a d'effet marginal positif** → la source n'apporte rien
   de mécanisable ici, et le dossier se conclut par un `NON RETENU` propre.
4. **Le meilleur candidat n'améliore pas le témoin aléatoire** au-delà de ce que
   la v1 fait déjà (percentile 100) → l'ajout n'apporte rien qu'un tirage au
   sort ne donnerait.
5. **Le résultat reste concentré sur 2025** comme celui de la v1 → la v2 hérite
   du défaut qu'elle était censée instruire, et ne peut pas prétendre le corriger.

---

## 4. Ce qu'un résultat positif ne prouvera PAS

- **Que « la méthode Doud » fonctionne.** Ce dossier mesure cinq de ses lectures
  d'entrée, en H1, sans ses sorties (partielles, SL suiveur), sans son
  calendrier économique et sans son biais macro. Un ingrédient qui paie ici dit
  quelque chose sur *notre* signal de cassure, pas sur *sa* méthode.
- **Que l'or a un edge.** Deux méthodes sans rapport (S01 et S011) ont déjà
  laissé XAUUSD comme unique résidu sur 2021-2026. Une troisième lecture qui
  marche sur le même instrument et la même fenêtre renforce l'hypothèse
  « propriété de l'or sur cette période » au moins autant que celle de la règle.
- **Que le côté long est le bon côté.** Sur 2021-2026 l'or monte. Un `long_only`
  qui gagne sur cette fenêtre est indiscernable du beta — c'est exactement le
  reproche que `S011/research/VERDICT.md` § 2.4 adresse déjà au panier entier
  (« du beta déguisé en système »).

---

## 5. Condition de promotion

Aucune promotion `BACKTESTED → PAPER` sans, cumulativement : R1 et R5 passés,
effet marginal positif, ≥ 20 trades hors échantillon, percentile témoin ≥ 95,
et un **forward-test scellé dédié** sur le modèle de `studies/gold_forward/`
(protocole écrit avant le premier signal, hash des paramètres, critères d'arrêt
chiffrés d'avance). La décision reste à Adrian (R10).
