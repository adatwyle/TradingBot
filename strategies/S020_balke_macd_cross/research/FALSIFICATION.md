# S020 — critères de falsification

**Écrit le 2026-09-12, AVANT toute exécution du harnais.** Un critère rédigé après
lecture des résultats n'est pas un critère.

---

## L'hypothèse

Sur les instruments où René Balke la fait tourner (US Tech en démo) et sur ceux
de notre portefeuille, un croisement MACD/signal filtré par le signe de la MACD,
avec stop et cible en pourcentage du prix, produit une espérance positive nette de
frais, hors de l'échantillon qui aurait servi à la régler.

## Ce qui est reproduit, et ce qui ne l'est pas

Reproduit tel quel : la règle dictée à [01:00]-[08:30] de la vidéo — croisement,
filtre zéro optionnel, SL/TP en %, une position par symbole. Non reproduit : le
sizing (couche risque, R2), et les particularités du Strategy Tester MT5 (modèle
de ticks). Ajouté par la plateforme : coût de bord réel, refroidissement et
coupe-circuit communs, bras témoin.

**Donnée d'entrée connue, à ne pas confondre avec un verdict** : S013 a mesuré le
croisement MACD nu (sorties ATR, forex D1) et l'a trouvé nul. La cellule de Balke
n'est pas celle-là. Elle a droit à son run complet.

---

## Les seuils

### Réussite — toutes ces conditions, sur une même cellule et un même instrument

1. **Hors échantillon** : cellule STRICT au walk-forward ancré (4 fenêtres), avec
   ≥ 20 trades hors échantillon.
2. **Témoin** : percentile ≥ 90 contre le bras aléatoire à gabarit identique.
3. **Coût absorbé** : R/trade > 0 au spread **mesuré** (colonne `spread` des barres),
   pas seulement au spread catalogue.
4. **Multiplicité** : 18 cellules × 7 instruments = 126 tests. À 5 %, ≈ 6 réussites
   par pur hasard. Il faut donc, pour un instrument donné, ≥ 3 cellules STRICT
   **ou** une cellule au percentile témoin ≥ 97 ; et la même cellule doit rester
   positive sur au moins un second instrument.

### Échec — l'une suffit

- Aucune cellule STRICT sur aucun instrument, ou aucune ne dépasse le percentile 90.
- Le signal disparaît entre plein échantillon et hors échantillon.
- Le coût de bord dépasse 35 % du R médian de la cellule (stop en % trop serré
  pour l'instrument).
- Résultat porté par une seule année sur un seul instrument.

### Échec du dispositif, pas de l'hypothèse

- R1 en défaut → on corrige et on remesure.
- Moins de 20 trades sur toutes les cellules d'un instrument → cet instrument est
  non concluant à cette maille, pas négatif.
- Intraday indices indisponible (MT5 hors ligne) → la démo de l'auteur (US Tech)
  n'est mesurée qu'en D1 ; **la conclusion sur les indices reste ouverte** tant que
  l'intraday n'a pas été mesuré.

---

## Ce qui ne sera pas fait

- Aucun ajout de commutateur ou d'instrument après lecture des résultats.
- Aucun réglage fin de MACD(12,26,9) : ce sont les défauts MT5 que l'auteur applique.
- Aucune promotion PAPER : décision Adrian (R10).

## Ce que chaque issue nous apprendra

| Issue | Lecture |
|---|---|
| Réussite | La règle porte sur cet instrument à cette maille. Étape suivante : forward scellé, décision Adrian. |
| Échec avec coût < 35 % | Le croisement filtré ne contient pas d'information à cette maille. Cohérent avec S013 ; la piste « indices intraday » reste à mesurer. |
| Échec par coût | La géométrie en % de la vidéo est trop serrée pour nos frais sur cet instrument — la règle vaut peut-être ailleurs. |
| Non concluant | Remesurer à la maille manquante avant tout jugement. |
