# SPEC — Canal Telegram TradingBot (notifier + gateway, reporting)

**Version** : 1.0.0 — 2026-08-26 · **Auteur** : cc-spec · **Statut** : prête pour implémentation
**Sources** : input-adrian 07 (formats exacts), 03, 09 ; PLAN T7 ; TCK-007 (tokens = geste
Adrian) ; héritage `app/orchestrator/robinbot-notify.py` (curseurs après envoi) et
`robinbot-gateway.py` (bot dédié, lecture seule, allowlist).
**Implémente** : refonte `robinbot-notify.py` (source = ledger), adaptation
`robinbot-gateway.py` (tokens + menu skills), skills projet `.claude/skills/tbot-*/`.

## 1. Objectif

Nouveau canal Telegram **TradingBot** — les bots du prototype ne sont pas réutilisés.
Deux bots dédiés (`getUpdates` exclusif par bot) : **notifier** (sortant) et **gateway**
(entrant). Reporting aux formats exacts d'Adrian, agrégats fournis par le ledger.
Code inerte sans tokens (sortie 2, réessai) — TCK-007.

## 2. Décisions tranchées

| # | Décision | Motivation (1 ligne) |
|---|----------|----------------------|
| D-TG-1 | Fichiers : `C:\db\tradingBot\notifier\token.txt` et `C:\db\tradingBot\gateway\token.txt` (token brut, 1 ligne, BOM toléré) + `config.json` (chat_id) par bot | Convention actée dans TCK-007 ; hors repo, jamais commitables (`.gitignore` exclut de toute façon `*token*.txt`). |
| D-TG-2 | Ligne par trade envoyée **en direct à la clôture** ET reprise dans le récap du soir (flag `live_lines`, défaut `true`) | Le format d'Adrian décrit le récap (liste + total) ; les lignes live sont l'héritage prouvé du notify et le récap sert de filet si un envoi live a échoué. |
| D-TG-3 | Récap hebdo envoyé le **vendredi** avec le récap quotidien (une section, un seul message) | Semaine de trading FX = lundi-vendredi ; c'est aussi la mécanique du digest hérité (constante FRIDAY). |
| D-TG-4 | Récaps mensuel et annuel envoyés au **premier créneau quotidien du mois/de l'année suivant(e)** | Déterministe quel que soit le jour de semaine du 31, et le mois est complet au moment de l'envoi. |
| D-TG-5 | Montants arrondis au CHF entier, signés, suffixe `chf` collé (`-100chf`, `+210chf`) | C'est la forme exacte des exemples d'Adrian (chapitre 07). |
| D-TG-6 | Curseur des trades notifiés = tuple `(close_time, id)` dans `state.json`, avancé **après envoi réussi** | Le close est un UPDATE (l'ordre des id ne suit pas l'ordre des clôtures) ; règle héritée : un doublon est toléré, un trade manqué est interdit. |
| D-TG-7 | Gateway : offset Telegram avancé **avant** l'appel Claude (payant) | Règle héritée cc-app : on préfère perdre une question (Adrian la repose) que payer deux fois la même session. |

## 3. Exigences — notifier (worker `notify`, sortant)

- **TG-1** — Résolution : `db_dir()/notifier/` (`token.txt`, `config.json`, `state.json`),
  seam `ROBINBOT_NOTIFY_DIR`. `config.json` : `{"chat_id": int, "digest_hour": 22,
  "live_lines": true}`. Token ou chat_id absents → **sortie 2** sans bruit (inerte, TCK-007).
- **TG-2** — Source des trades : le **ledger** (SPEC_ledger), modes `PAPER` et `LIVE`
  uniquement (jamais BACKTEST — le backtest n'est pas de l'activité du jour). Sélection :
  trades clos avec `(close_time, id)` > curseur (D-TG-6).
- **TG-3** — **Format exact d'une ligne de trade** (heure de clôture **locale** `HH:MM`,
  instance, motif de sortie, `net_pnl` arrondi CHF entier signé) :
  ```
  10:53 S001.CHF-USD SL -100chf
  22:05 S001.CHF-USD TP +210chf
  ```
  Motifs affichés tels que stockés (`SL`, `TP`, `TRAIL`, `MANUAL`, `HALT`, `EOD`).
- **TG-4** — **Récap quotidien** : au premier tick après `digest_hour` locale, une fois par
  jour (curseur date en state.json). Message :
  ```
  📒 TradingBot — 26.08.2026
  10:53 S001.CHF-USD SL -100chf
  22:05 S001.CHF-USD TP +210chf
  Total jour : +110chf
  ```
  Aucun trade → `📒 TradingBot — 26.08.2026` + `Aucun trade aujourd'hui.` (le silence
  total est indistinguable d'une panne).
- **TG-5** — **Récap hebdomadaire** (vendredi, section ajoutée au message quotidien,
  D-TG-3) — gains/pertes par jour puis total, source `pnl_by_day` sur la semaine ISO :
  ```
  — Semaine 35 (25.08–29.08) —
  Lu +110chf
  Ma -40chf
  Me +0chf
  Je +75chf
  Ve -25chf
  Total semaine : +120chf
  ```
- **TG-6** — **Récap mensuel** (premier créneau du mois suivant, D-TG-4) — par semaine ISO
  puis total, puis rétrospective 12 mois :
  ```
  📒 Mois d'août 2026
  S32 +210chf
  S33 -80chf
  S34 +45chf
  S35 +120chf
  Total mois : +295chf

  — 12 derniers mois —
  09.2025 +130chf
  …
  08.2026 +295chf
  ```
- **TG-7** — **Récap annuel** (premier créneau de janvier) — par mois puis total :
  ```
  📒 Année 2026
  01 +85chf
  …
  12 -30chf
  Total année : +1250chf
  ```
- **TG-8** — Tout ce qu'un même tick récolte part en **un seul message** (sections
  séparées par une ligne vide), découpé à **4000 caractères** max par envoi (limite
  héritée, marge sous les 4096 Telegram), coupure sur une frontière de ligne.
- **TG-9** — `state.json` (écriture atomique) n'est sauvegardé **qu'après** envoi
  Telegram réussi (HTTP 200 + `ok:true`). Échec réseau/API → sortie 2, mêmes lignes
  retentées au tick suivant.
- **TG-10** — Alertes héritées conservées : lignes AUTO-OFF du panneau (empreinte
  sha256, une alerte par ligne nouvelle) ; sources « études scellées » héritées
  conservées mais inertes tant que leurs dossiers n'existent pas (E6).
- **TG-11** — Le token n'apparaît **jamais** dans un log, un message d'erreur ou une
  exception (les URL d'API sont loggées tronquées).
- **TG-12** — Codes de sortie : `0` passage effectué (y c. rien de neuf), `2`
  token/config absents ou Telegram injoignable, `1` erreur inattendue. Jamais 3/4.
- **TG-13** — Cadence : worker `notify` de la factory, tick, 300 s (catalogue inchangé).

## 4. Exigences — gateway (worker `gateway`, entrant)

- **TG-14** — Résolution : `db_dir()/gateway/` ; `token.txt` (D-TG-1 — le défaut hérité
  `gateway_token.txt` est remplacé), `config.json` `{"chat_id": int}`, `state.json`
  `{"offset", "n_served"}`. Token/config absents → sortie 2 (inerte).
- **TG-15** — Sécurité héritée intégralement conservée : session Claude headless en
  **lecture seule** (`--allowedTools Read,Grep,Glob`), allowlist stricte sur `chat_id`
  (autre expéditeur : ignoré, message consommé), timeout et max-turns configurables.
- **TG-16** — Offset avancé et persisté **avant** l'appel Claude (D-TG-7).
- **TG-17** — **Skills projet** : un skill = un dossier `.claude/skills/tbot-<nom>/SKILL.md`
  avec en-tête frontmatter `command: /<nom>` + `description:` (1 ligne). Le gateway
  scanne ce répertoire à chaque tick :
  - message commençant par `/<nom>` connu → la consigne de session pointe le SKILL.md
    correspondant (« suis .claude/skills/tbot-<nom>/SKILL.md ») ;
  - message libre → consigne générale héritée (réponse courte, chiffres depuis les fichiers).
- **TG-18** — **Menu auto** : si la liste `(commande, description)` diffère de celle
  mémorisée dans `state.json`, le gateway appelle `setMyCommands` — le menu Telegram
  reflète les skills sans geste manuel. Échec de l'appel : log, non bloquant.
- **TG-19** — Skill minimal livré : `tbot-etat` (`/etat`) — état de situation : factory
  vivante, workers on/off, PnL du jour (ledger), positions ouvertes, dernier passage par
  instance, tickets bloquants. Extensible : tout nouveau dossier skill est pris en
  compte au tick suivant (TG-17/TG-18), sans modification du code.
- **TG-20** — Réponses découpées à 4000 caractères ; token jamais loggé (TG-11) ;
  codes de sortie identiques à TG-12 ; cadence : catalogue factory inchangé (30 s).

## 5. Tests attendus (cc-app)

- **TG-T1** — Formats : pour un ledger de fixtures, les messages TG-3→TG-7 sont
  reproduits **caractère par caractère** (golden tests).
- **TG-T2** — Curseur trades : envoi simulé en échec → state.json inchangé, retenté ;
  succès → curseur `(close_time, id)` avancé ; close antidaté jamais perdu.
- **TG-T3** — Découpage 4000 chars sur frontière de ligne.
- **TG-T4** — Inertie : dossier notifier/gateway vide → sortie 2, aucun appel réseau.
- **TG-T5** — Gateway : offset persisté avant l'appel Claude (mock) ; expéditeur hors
  allowlist ignoré et consommé.
- **TG-T6** — Menu : ajout d'un dossier skill → `setMyCommands` appelé avec la nouvelle
  liste ; liste inchangée → aucun appel.
- **TG-T7** — Anti-fuite : aucun test/log ne contient le token de fixture (grep).
