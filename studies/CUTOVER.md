# CUTOVER — bascule des études en vol : robinbot (prototype) → tbot factory

**Source de vérité du protocole** : `support/input-adrian/09_reprise-prototype.md`
§ « Études en vol — migration vers la tbot factory » (directive Adrian 2026-08-26).
**Préparation** : TCK-009 / T10 (code migré, workers au catalogue off, outil
`studies/verify-journal.py`). **La bascule elle-même n'est PAS couverte par T10** :
chaque étude bascule sur **GO Adrian explicite**, une à la fois, pilotée par
cc-support au moment choisi.

## Lois non négociables

1. **Jamais deux factories actives sur le même journal.** Un entrelacement
   robinbot/tbot produit une fausse alarme d'altération (chaîne + empreinte
   d'état divergent) — interdit par le protocole.
2. **Le journal migre INTACT, curseurs compris.** Un journal recommencé à zéro
   perd la collecte (s14 : 1 706 lignes au 2026-08-26). Aucune copie partielle,
   aucun « repartir propre ».
3. **Le prototype est en exploitation** : `C:\Datas\Projects\TradingBot_9.0.0.x`
   et `C:\db\tbot\` restent en lecture seule pour tout le monde SAUF les deux
   gestes du protocole ci-dessous (édition du panneau robinbot, déplacement du
   dossier d'étude) — exécutés à la main au GO, jamais par un agent en avance.
4. **L'extinction complète de la robinbot factory reste conditionnée à la
   checklist E6** (études migrées ou scellées, Telegram migré, supervision
   reprise, ~1 semaine de cohabitation sans incident).

## Indépendance chemin ↔ chaîne de hachage (vérifié T10, point 4)

**La chaîne de hachage ne dépend PAS du chemin absolu du fichier.**
Lecture du code (identique dans les 5 études, héritage prototype) :

- chaque ligne du journal porte `chain` = SHA-256 **des octets du fichier
  avant elle** — contenu pur, aucun chemin n'entre dans le hash
  (`append_journal` / `verify_journal` dans `*_step.py`) ;
- `state.json` mémorise l'empreinte du dernier passage sous forme
  (`journal_bytes`, `journal_sha256`) — contenu pur également ; aucun chemin
  absolu n'est stocké dans l'état.

Conséquence : déplacer `C:\db\tbot\<étude>\` vers `C:\db\tradingBot\<étude>\`
préserve l'intégrité vérifiable à l'identique. Preuves : test dédié
`studies/test_verify_journal.py::test_journal_deplace_rend_0` + vérification
lecture seule des 5 journaux vivants du prototype le 2026-08-26 (tous exit 0
avec le code migré — équivalence de format prouvée avant toute bascule).

## Pré-requis (une fois, avant la première bascule)

- [ ] tbot factory opérationnelle sur ce poste (`app/orchestrator/tbot-factory.py`),
      les 5 workers visibles au catalogue et `off` au panneau
      `C:\db\tradingBot\tbot-panel.txt`.
- [ ] `python -m pytest studies -q` vert sur HEAD déployé.
- [ ] **s14_sentiment uniquement** : la clé Finnhub doit exister côté cible —
      copier (ne pas déplacer) `C:\db\tbot\secrets\finnhub_key.txt` →
      `C:\db\tradingBot\secrets\finnhub_key.txt` (geste Adrian/cc-support au GO ;
      le coffre cible n'existe pas encore au 2026-08-26). Sans clé : exit 2 à
      chaque tick, la factory réessaie sans crier — pas de trou de journal,
      mais pas de collecte non plus.
- [ ] **macd_ai_paper / alexg_paper / s14_sentiment** : CLI `claude` accessible
      dans le PATH du poste (juge IA headless — appelé uniquement sur signal).

## Séquence PAR ÉTUDE (une à la fois, à chaud — GO Adrian préalable)

Cadences : ticks de 1800 s (s14) à 3600 s (les 4 autres) → la fenêtre entre
deux ticks laisse plusieurs minutes, largement assez. Gap de quelques minutes
= zéro trou de données (les pas de mesure sont idempotents et rattrapent les
barres closes à la reprise).

1. **Vérifier AVANT** (lecture seule, sans danger) :
   `python studies/verify-journal.py <étude> --dir C:/db/tbot/<étude>`
   → exit 0 exigé. Exit 4 = STOP, enquête, pas de bascule.
2. **OFF côté robinbot, à chaud** : éditer `C:\db\tbot\robinbot-panel.txt`,
   passer `<étude> = off`. Prise d'effet au tick suivant du superviseur.
3. **Attendre la fenêtre** : vérifier dans la console/logs robinbot que le
   dernier tick de l'étude est terminé et qu'aucun ne redémarre (le worker
   n'apparaît plus dans les lancements). En cas de doute : attendre 2-3 min
   de plus — la fenêtre est large.
4. **Déplacer le journal** (même volume → rename instantané) —
   **STOP OBLIGATOIRE d'abord** :
   `Test-Path C:\db\tradingBot\<étude>`
   → doit rendre **False**. `True` = **STOP net, aucune bascule** : un
   `Move-Item` vers un dossier existant IMBRIQUE silencieusement la source
   DANS la cible (`C:\db\tradingBot\<étude>\<étude>\`) au lieu de la
   remplacer — le journal semblerait disparu et le runner démarrerait un état
   neuf. Enquête (d'où vient la cible ? un premier passage accidentel ?)
   avant toute reprise.
   Puis seulement :
   `Move-Item C:\db\tbot\<étude> C:\db\tradingBot\<étude>`
   Le dossier part ENTIER : `journal.csv`, `state.json`, `status.json`,
   `run.log` (et tout fichier annexe).
5. **Vérifier APRÈS** :
   `python studies/verify-journal.py <étude>`
   (défaut = emplacement cible) → exit 0 exigé.
6. **ON côté tbot, à chaud** : éditer `C:\db\tradingBot\tbot-panel.txt`,
   passer `<étude> = on`. Prise d'effet au tick suivant.
7. **Surveiller le premier tick** dans la console tbot : exit 0 attendu
   (« passage » — PAS « PREMIER PASSAGE », qui signifierait un état neuf donc
   un journal ignoré : STOP immédiat si ça apparaît, voir Rollback).
   Exit 2 = ressource indisponible (MT5/clé), la factory réessaie. Exit 3/4 =
   AUTO-OFF automatique + enquête.

## Rollback (si l'étape 5 ou 7 échoue)

1. `<étude> = off` dans `C:\db\tradingBot\tbot-panel.txt` (si déjà allumée).
2. `Move-Item C:\db\tradingBot\<étude> C:\db\tbot\<étude>` (retour intact).
3. `python studies/verify-journal.py <étude> --dir C:/db/tbot/<étude>` → 0.
4. `<étude> = on` dans `C:\db\tbot\robinbot-panel.txt` — le prototype reprend.
5. Enquête côté repo (ticket), AUCUNE nouvelle tentative sans nouveau GO.

## Ordre conseillé et notes par étude

| Ordre | Étude | Cadence | Notes de bascule |
|---|---|---|---|
| 1 | `macd_ai_paper` | 3600 s | Verdict RENDU (NE PAS armer l'IA — VERDICT_REPLAY.md). Journal quasi vide (en-tête seul) : bascule au risque minimal, idéale pour valider la procédure. Les outils replay_* lisent `datasets/LONGHIST` sous `C:\db\tradingBot\` — copie des datasets HORS scope bascule (décision Adrian séparée, le tick horaire n'en a pas besoin). |
| 2 | `s13_forward` | 3600 s | ARMÉE, 0 trade clos (~7/an attendus), journal en-tête seul. D1 : fenêtre géante. |
| 3 | `gold_forward` | 3600 s | ARMÉE, 6 lignes de journal (+1,64 R). H1. |
| 4 | `alexg_paper` | 3600 s | ARMÉE 22.08, 26 paires, 4 bras, ~3 mois avant verdict. Journal en-tête seul. Le runner LIT un compte MT5 réel mais n'envoie JAMAIS d'ordre (R10). |
| 5 | `s14_sentiment` | 1800 s | Le journal le plus précieux (1 706 lignes, verdict mi-octobre). Basculer en DERNIER, après que la procédure a été validée 4 fois. Pré-requis clé Finnhub (voir plus haut). |

## Ce que T10 a préparé (état 2026-08-26)

- Code des 5 études migré verbatim dans `studies/` (un commit par étude),
  chemins d'état vers `C:\db\tradingBot\<étude>\` via `app/core/paths.py`
  (seam `TBOT_DB_DIR`), scellés `params.json` copiés octet pour octet et
  protégés par `.gitattributes` (`params.json -text`).
- Workers au catalogue tbot (`app/orchestrator/tbot-factory.py`), cadences
  identiques au prototype, `off` par défaut dans le gabarit du panneau.
- `studies/verify-journal.py` + tests (7) — réutilise `verify_journal` des
  études elles-mêmes.
- Dry-runs sur état isolé (`TBOT_DB_DIR` → tmp) : gold/s13/macd/alexg exit 0
  (premier passage scellé en environnement jetable), s14 exit 2 (clé absente,
  comportement contractuel). Les vrais `C:\db\tradingBot\` et `C:\db\tbot\`
  n'ont PAS été touchés.
- Les `run_*.bat` du prototype n'ont pas été migrés : la tbot factory est le
  lanceur (`python -m studies.<étude>.<runner>` depuis la racine du dépôt).
