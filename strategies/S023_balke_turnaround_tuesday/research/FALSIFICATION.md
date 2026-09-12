# S023 — critères de falsification

**Écrit le 2026-09-12, AVANT toute exécution du harnais.** Un critère rédigé après
lecture des résultats n'est pas un critère.

---

## L'hypothèse

Sur les trois indices que René Balke trade (DE40, US Tech, US30), acheter le lundi
lorsque le prix est sous la moyenne mobile simple journalière de sa période, et
tenir jusqu'au mardi soir, produit une espérance positive nette de frais, hors de
l'échantillon qui aurait servi à la régler — et cette espérance vient du FILTRE,
pas de la dérive haussière de l'indice.

## Ce qui est reproduit, et ce qui ne l'est pas

Reproduit tel quel : le jour d'ouverture (lundi), le filtre SMA journalière sur les
clôtures avec sa période par instrument (US30 25, NASDAQ 9, DAX 40), le sens unique
(achat), l'absence de TP, l'absence de gestion, la sortie par l'heure le mardi soir.

**Non reproduit, et déclaré** :
1. **Le stop.** Il n'en a pas. La plateforme en exige un (R3). S023 déclare sa
   propre règle : `guard_pct`, garde CATASTROPHE à 5 % sous l'entrée (grille
   3 / 5 / 10 %). Ce n'est pas un stop de gestion. **Critère de dispositif** : si
   plus de 5 % des trades de la cellule de fidélité touchent la garde, elle cesse
   d'être une garde — la reproduction n'est plus fidèle et le résultat doit être
   relu comme celui d'une AUTRE stratégie.
2. **L'heure exacte d'ouverture et de clôture.** Lui : 01:05 → 23:50 (DE40
   09:05 → 22:55). Nous : close de la première barre H1 du lundi (01:00 serveur ;
   09:00 pour le DAX) → close de la dernière barre du mardi, approximée par
   `max_hold_bars` fixe (45 / 45 / 27, calibré sur les données AVANT la mesure).
   L'écart nominal est de cinq minutes ; la dérive réelle vient des semaines
   incomplètes (jours fériés) et, en `any_bar`, des entrées tardives. **Le harnais
   publie la distribution des heures et des jours de sortie.**
3. **Le sizing** (25 000 € de notionnel par trade) : couche risque, R2, hors
   stratégie. Conséquence directe : nos chiffres en R ne sont PAS comparables aux
   siens en euros. C'est pourquoi tout est aussi rapporté **en % du prix d'entrée**.
4. **Le modèle de ticks du Strategy Tester MT5** et ses données (IC Markets /
   Dukascopy). Nous : barres H1 Swissquote, exécution pessimiste du moteur commun.

Ajouté par la plateforme : coût de bord réel, bras témoin aléatoire, bras
« règles communes » (refroidissement + coupe-circuit) mesuré À PART.

---

## Les bras, déclarés avant de lancer

| Bras | Réglage moteur | Rôle |
|---|---|---|
| **Fidèle** | `max_positions=1, cooldown_bars=0, cb_losses=999, cb_cooldown_bars=0, max_hold_bars=<45/45/27>` | la stratégie telle qu'il la trade |
| **Règles communes** | `cooldown_bars=2, cb_losses=3, cb_cooldown_bars=24` + même `max_hold_bars` | information seulement, sur la cellule de fidélité. Ne peut PAS invalider le bras fidèle (doctrine Adrian 2026-09-12) |
| **Témoin** | entrées aléatoires, même effectif, même gabarit de risque, même `max_hold_bars` | « entrer le lundi sous la SMA bat-il entrer au hasard avec la même durée de détention ? » |
| **Référence non filtrée** | `sma_period=0` — achat de CHAQUE lundi, même sortie | le rendement 2 jours nu de l'indice. **Étalon, pas candidat** : hors grille, hors décompte de multiplicité |

---

## Références de fidélité (pré-enregistrées)

Ce qu'il annonce : ~160 trades sur les trois indices depuis mars 2024 (≈ 2,5 ans),
+16 k€ pour 25 000 € de notionnel par trade, soit **≈ +0,4 % du notionnel par
trade** en moyenne ; profit factor « much better » que Go Long ; profitable sur les
trois. Réserve qu'il pose lui-même : effectif faible, période possiblement favorable.

Cadence attendue sur nos 5 ans : ≈ 52 lundis/an × la part des lundis sous la SMA.
Cette part est une propriété des DONNÉES, pas un résultat de la stratégie ; elle a
donc été mesurée AVANT d'écrire ce document, pour dimensionner le dispositif :
34 à 45 % selon l'instrument et la période (NASDAQ SMA9 42,5 % ; US30 SMA25
40,6 % ; DAX SMA40 36,7 %). **Attendu : 85 à 120 trades par instrument sur 5 ans**
— cohérent avec ses ~21 trades/an/indice.

**Critères de fidélité** (cellule de fidélité, bras fidèle) :

| Grandeur | Attendu | Si loin du compte |
|---|---|---|
| Nombre de trades / instrument | 85-120 | question de DISPOSITIF d'abord (frontière de jour, définition de la SMA, heures de séance), pas d'hypothèse |
| Rendement moyen par trade, en % du prix d'entrée | positif, ordre de +0,3 à +0,6 % | idem |
| Trades touchant la garde | ≈ 0, et < 5 % | la garde n'est plus une garde (cf. ci-dessus) |
| Part des sorties tombant le mardi soir (`first_bar`) | > 85 % | l'approximation `max_hold_bars` ne tient pas, à corriger avant de conclure |

---

## Les seuils

### Réussite — TOUTES ces conditions

1. **Cellule** : la cellule de FIDÉLITÉ de l'instrument, **ou** une cellule STRICT
   au walk-forward ancré (4 fenêtres) avec ≥ 20 trades hors échantillon.
2. **Témoin** : percentile ≥ 90 contre le bras aléatoire à gabarit identique.
3. **Coût absorbé** : rendement moyen par trade > 0 au spread **mesuré**
   (DAX 23, NASDAQ 12, US30 35 pips), pas seulement au spread catalogue.
4. **Apport du filtre** : le résultat filtré doit dépasser la **référence non
   filtrée** (`sma_period=0`) sur le même instrument. Sinon l'avantage n'est pas
   le filtre mais la dérive de l'indice — et il faut le dire ainsi.
5. **Reproductibilité inter-instruments** : conditions 1-4 vérifiées sur **au
   moins 2 des 3 indices**.

### Échec — l'une suffit

- Aucune cellule au percentile témoin ≥ 90 sur aucun instrument.
- Résultat porté par une seule année (table par année obligatoire : si retirer
  l'année la plus forte rend l'ensemble négatif, c'est un échec).
- Le filtre SMA ne fait pas mieux que la référence non filtrée sur les trois
  instruments : la stratégie n'est alors qu'un « acheter l'indice deux jours ».
- Le signal disparaît entre plein échantillon et hors échantillon.

### Non concluant — pas un verdict négatif

- Moins de 20 trades sur toutes les cellules d'un instrument.
- Échec de dispositif : R1 en défaut, garde touchée > 5 %, sorties hors du mardi
  soir > 15 % en `first_bar` → on corrige le dispositif et on remesure.

### Multiplicité

18 cellules × 3 instruments = 54 tests (la référence non filtrée et le bras
« règles communes » n'en font pas partie). À 5 %, ≈ 2,7 « réussites » par pur
hasard. Les cellules voisines étant fortement corrélées (même jour, même sortie),
ce chiffre SURESTIME le hasard — c'est précisément le rôle du bras témoin, qui
mesure la distribution nulle au lieu de la supposer. **La cellule de fidélité
échappe à ce décompte** : elle n'a pas été choisie par nous, elle est dictée par
la source.

---

## Ce qui ne sera pas fait

- Aucun ajout de cellule, d'instrument ou de commutateur après lecture des résultats.
- Aucun réglage de la période SMA hors des trois qu'il trade.
- Aucune promotion PAPER/LIVE : décision Adrian (R10).
- Aucun avis sur la stratégie avant que les chiffres existent.

## Ce que chaque issue nous apprendra

| Issue | Lecture |
|---|---|
| Réussite | L'effet « turnaround Tuesday » est mesurable chez notre courtier sur 5 ans. Étape suivante : forward scellé, décision Adrian. |
| Échec par le filtre (non filtré ≥ filtré) | Ce qui est mesuré est la dérive haussière des indices, pas un effet de calendrier. Conséquence directe pour Go Long (même famille), à instruire séparément. |
| Échec par le témoin | Tenir deux jours au hasard vaut autant : le lundi n'a rien de spécial. |
| Non concluant | Remesurer après correction du dispositif ; ne rien conclure sur l'hypothèse. |
