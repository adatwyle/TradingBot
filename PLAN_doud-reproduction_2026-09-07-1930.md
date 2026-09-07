# PLAN — reproduction de la méthode Doud, mesure et validation

**Verrouillé le 2026-09-07 19:30, avant exécution.** Mandat Adrian : « GO pour les
P1 → P3 — analyse puis reproduit la stratégie de Doud, teste puis améliore la stratégie
reconstruite, une fois prête passe au paper trade pour validation. »

**Override de périmètre signalé** : reproduire et améliorer une stratégie relève de
cc-S0NN, pas de cc-support. Instruction directe d'Adrian, donc exécutée
(`~/.claude/CLAUDE.md`, principe d'autorité).

---

## L'idée directrice

L'audit du 2026-09-07 a établi que le déclencheur de S019 produit un chemin de prix
**sans dérive** — donc réfuté, et non rattrapable par une meilleure sortie. Cette mesure
a coûté quatre minutes et a économisé plusieurs sessions de moteur.

**On en fait la méthode de travail** : avant de construire une stratégie sur une
hypothèse d'entrée, on mesure d'abord si cette entrée produit une dérive. Un criblage
qui coûte des minutes remplace des campagnes de walk-forward qui coûtent des heures.

Contre la multiplicité — le criblage de N candidats puis la construction sur le gagnant
est exactement du p-hacking —, trois garde-fous **écrits avant de voir les résultats** :

1. la liste des candidats est **arrêtée en T5.1** et ne bougera plus ;
2. le criblage se fait sur **2021-2024 seulement** ; 2025-2026 est un **holdout** jamais
   regardé avant T6 ;
3. un candidat survivant n'est **pas** un résultat : il doit encore passer walk-forward
   ancré + bras témoin + falsification écrite d'avance en T6.

---

## Tâches

| # | Tâche | Acteur | Dépend de |
|---|---|---|---|
| T1 | Spread au régime courant, **sans toucher le scellé** | cc-app | — |
| T2 | Corpus bilatéral : sens des entrées, purge, rejeu | cc-support | — |
| T3 | Orphelins M15/M5 de S018, en addendum daté | cc-S018 | — |
| T4 | Garde-fou de production aligné sur la CI | cc-app | — |
| T5 | Cribleur de dérive + criblage des candidats | cc-S020 | T1 |
| T6 | S020 sur le candidat survivant, mesure complète | cc-S020 | T2, T3, T5 |
| T7 | Forward scellé (= paper) si et seulement si T6 réussit | cc-S020 + Adrian | T6 |

### T1 — Spread au régime courant, sans toucher le scellé

**Le piège** : `studies/gold_forward/PROTOCOL.md` § 2.2 fige le spread à 25 pips en
citant le catalogue `app/core/data/instruments.py`. Modifier cette constante **change un
test scellé qui tourne depuis le 14 août**.

**Donc** : on n'y touche pas. On **ajoute** une table de spreads mesurés par année, avec
un accesseur distinct, que seules les mesures neuves consomment.

- Livrable : table + accesseur dans `app/core/data/instruments.py`, tests.
- Critère : la constante lue par le scellé est **inchangée** (test de non-régression
  explicite qui l'affirme) ; l'accesseur rend 90,8 pips pour XAUUSD en 2026.

### T2 — Corpus bilatéral

- Règle de purge **écrite avant** relecture : doublons exacts (même vidéo, même prix),
  observations dont le contexte marque un récit au passé.
- Établir le **sens** des observations survivantes par relecture des `ctx` et des
  transcriptions autour du timecode.
- Rendre `croisement_entrees.py` **symétrique** : balayage baissier détecté aussi,
  MFE/MAE orientés selon le sens.
- Critère : le 60/39 est confirmé, corrigé ou tombe. **Les trois issues sont
  acceptables** ; un verdict est écrit dans les trois cas.

### T3 — Orphelins S018

- `results_M15.json` et `results_M5.json` existent depuis le 2026-09-06, jamais lus.
- Livrable : `strategies/S018_gold_doud_v2/research/VERDICT_addendum_M15-M5_2026-09-07.md`.
- Critère : **addendum daté, jamais réécriture** du VERDICT ; le § 6 « nous mesurons en
  H1 », devenu faux, est corrigé par renvoi et non par effacement.

### T4 — Garde-fou de production

- `app/orchestrator/tbot-prod-watcher.py:212` lance `pytest app -q` ;
  `.github/workflows/ci.yml:71` lance `pytest app strategies studies`.
- Critère : même périmètre des deux côtés, test qui l'atteste. Le changement rend la
  porte **plus stricte** — donc sûr par construction.

### T5 — Cribleur de dérive

Pour une règle d'entrée quelconque, mesurer si le chemin qui suit a une dérive :
P(atteindre +b avant −1 R | +a) contre la martingale `(a+1)/(b+1)`, avec intervalle de
confiance et effectif.

**Liste des candidats, arrêtée maintenant** (aucun ajout après lecture des résultats) :

1. balayage haussier + réintégration (S019, témoin négatif connu)
2. balayage **baissier** + réintégration — jamais testé, et les seules entrées dont on
   connaît le sens sont des ventes
3. entrée à l'équilibre (repli 50 %, D4 de S018)
4. cassure Donchian de la v1 (S011) — **témoin positif attendu**, sert d'étalonnage
5. niveaux psychologiques ronds (multiples de 50 et de 100)
6. mi-asiatique — milieu de la session asiatique comme support/résistance
7. extrêmes de la veille (plus-haut / plus-bas du jour précédent)
8. compression de volatilité puis expansion (« salade de doji » → impulsion)

- Critère : chaque candidat rend une dérive chiffrée avec IC 95 %, sur **2021-2024
  seulement**. Le candidat 4 doit ressortir positif, sinon le cribleur est faux et rien
  d'autre n'est interprétable.

### T6 — S020

- Construite sur le **seul** candidat le mieux classé en T5, s'il existe.
- `research/FALSIFICATION.md` écrit **avant** la première mesure, seuils chiffrés.
- Grille **petite** (≤ 16 cellules), walk-forward ancré, bras témoin, spread 90,8 pips.
- Critère de réussite : ≥ 3 cellules STRICT hors échantillon **ou** une cellule au
  percentile témoin ≥ 97, avec ≥ 20 trades hors échantillon et R/trade positive au
  spread réel.
- **Si aucun candidat ne survit à T5 : T6 n'a pas lieu**, et le dossier se clôt sur un
  verdict. C'est une issue acceptable, écrite d'avance.

### T7 — Forward scellé

- **Seulement si T6 réussit.** Protocole scellé sur le modèle de `studies/gold_forward/` :
  hash des paramètres, journal à chaîne de hachage, critères d'arrêt écrits d'avance.
- La **décision de promotion reste à Adrian** (R10). Le mandat « passe au paper trade »
  autorise la préparation et le lancement du dispositif virtuel ; aucun capital réel
  n'est engagé et rien ne s'arme tout seul.

---

## Contraintes valables pour toutes les tâches

- `studies/gold_forward/` et `strategies/S011_legacy_breakout/` : **lecture seule**.
- R9 : pas de moteur parallèle. R1 : causalité testée. R3 : stop obligatoire.
- Rien qui touche `core/backtest/engine.py` — l'audit a montré que le bras témoin du
  scellé y est recalculé à chaque lecture.
- Toute mesure : falsification écrite avant, bras témoin, effectif affiché.
