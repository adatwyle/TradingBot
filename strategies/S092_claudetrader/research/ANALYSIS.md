# ClaudeTrader — analyse et conception

**Source d'inspiration** : AI Pathways, agent de trading bâti sur Hermes (framework
open source de Nous Research), piloté depuis Telegram sur un VPS.
**Adaptation** : Claude Code en mode headless, lancé cycliquement par un
orchestrateur — le même schéma que le projet d'Adrian où un orchestrateur lance
des Claude Code autonomes pour développer une application.

---

## 1. Ce que décrit la source

Hermes fournit quatre briques :

| Brique | Rôle |
|--------|------|
| **Mémoire persistante** | Retient portefeuille, style, positions à travers les conversations |
| **Planificateur** | Tâches cron : briefing matinal, scan, alertes |
| **Boucle d'auto-apprentissage** | Écrit des fichiers *skills* à partir de ce qu'on lui demande |
| **Interface de messagerie** | Telegram — on discute avec l'agent comme avec un employé |

Usages montrés : briefing matinal, recherche d'activité d'initiés, scan
d'opportunités, pré-trade checks, suggestion de ticket avec taille et stop.

L'auteur recommande de **séparer les agents par tâche** (un trader, un chercheur,
un briefing) plutôt qu'un agent unique — chacun excelle sur son périmètre.

---

## 2. Correspondance avec notre pile

**Rien de ce que fait Hermes ne nous manque.** Claude Code en headless possède
déjà les outils ; ce qui manque est l'enveloppe qui le lance en boucle.

| Hermes | Chez nous |
|--------|-----------|
| Mémoire persistante | **Fichiers sur disque** (`memory/`) + le ledger SQLite. Versionnés dans git → auditables |
| Planificateur | **L'orchestrateur** — même schéma que le projet existant d'Adrian |
| Skills auto-écrits | `skills/*.md` relus à chaque invocation |
| Navigation web, exécution de code | Natifs dans Claude Code |
| Telegram | **Plugin déjà installé** (`telegram 0.0.6`) |
| VPS | PC rack 19", 24/7/365 |

**Différence de fond** : Hermes est une conversation persistante. Notre agent est
**sans état entre deux invocations** — il reconstruit son contexte depuis des
fichiers à chaque réveil. C'est moins fluide, mais c'est **auditable** : on peut
lire exactement ce qu'il savait au moment d'une décision. Pour du trading, cette
propriété vaut plus que la fluidité.

---

## 3. La difficulté centrale : ce n'est pas backtestable

Un agent discrétionnaire piloté par un LLM ne peut pas passer notre pipeline —
ni R1, ni le walk-forward ancré. Ses décisions ne sont pas déterministes et ne
peuvent pas être rejouées sur l'historique.

**Ce n'est pas un défaut à corriger, c'est une nature différente.** Il faut donc
un régime de validation distinct :

| Stratégie mécanique | ClaudeTrader |
|---------------------|--------------|
| Validée par walk-forward sur historique | **Validée par paper trading forward uniquement** |
| R1 : invariant de causalité | R1 sans objet — pas de fonction à tronquer |
| Preuve : OOS positif sur 4 fenêtres | Preuve : N mois de paper avec journal complet |
| Peut être promue sur backtest | **Ne peut JAMAIS être promue sur backtest** |

D'où le choix d'Adrian — paper d'abord — qui est le seul chemin possible.

---

## 4. Architecture

```
   ORCHESTRATEUR (cyclique)
   réveille l'agent selon un calendrier
            │
            ▼
   claude -p  (headless, une invocation = une décision)
   contexte reconstruit depuis :
     memory/     état du portefeuille, positions, faits
     skills/     méthode, règles apprises
     core/data   prix Swissquote
     ledger      historique réel des trades
            │
            ▼  SORTIE STRUCTURÉE (JSON), jamais du texte libre
   ┌─────────────────────────────────────┐
   │ {"action": "OPEN"|"CLOSE"|"HOLD",   │
   │  "symbol", "side", "entry",         │
   │  "stop"  ← OBLIGATOIRE (R3),        │
   │  "target", "confidence", "reason"}  │
   └─────────────────────────────────────┘
            │
            ▼
   VALIDATEUR — rejette toute sortie non conforme
            │
            ▼
   core/risk  — taille, limites, halt  (l'agent ne dimensionne JAMAIS)
            │
            ▼
   Swissquote DÉMO  ·  ledger mode=PAPER  ·  notification Telegram
```

### Le principe non négociable

**L'agent propose, la plateforme dispose.** Il émet un `Signal` exactement comme
n'importe quelle stratégie mécanique — mêmes règles R2 (il ne calcule aucune
taille), R3 (stop obligatoire), R8 (tout passe par le ledger).

Il n'a **aucun accès direct au broker**. C'est ce qui permet de le brancher,
débrancher ou plafonner depuis le dashboard sans toucher à son prompt.

---

## 5. Le vrai risque : la boucle d'auto-apprentissage

C'est la fonctionnalité vendue par Hermes, et **c'est la plus dangereuse**.

Un agent qui réécrit ses propres règles à partir de ses résultats va apprendre
du bruit. Avec une à deux décisions par jour, quelques mois de paper donnent
quelques dizaines d'observations — aucune base statistique. Il développera des
superstitions : *« j'évite les entrées le mardi »*, *« l'or marche bien en ce
moment »*. Ce sont exactement les faux motifs que tout notre travail de
validation cherche à éliminer.

Ce projet a déjà mesuré ce piège sous d'autres formes : un « strict pass » sur
19 trades dont l'intervalle de confiance contenait le seuil de rentabilité ;
USDJPY qui semblait un système et n'était qu'une tendance directionnelle.

### La parade — séparer faits et croyances

| `memory/` — **FAITS** | `skills/` — **CROYANCES** |
|----------------------|---------------------------|
| Positions ouvertes, P&L, ce qui s'est passé | Méthode, règles de décision |
| Écrit automatiquement par l'agent | **Modifiable uniquement sur validation humaine** |
| Toujours vrai par construction | Toujours contestable |

L'agent peut **proposer** une modification de `skills/` — elle atterrit dans
`decisions/proposals/` et attend un accord explicite. Rien ne change en silence.

C'est plus lent que l'auto-amélioration d'Hermes. C'est aussi la différence entre
un système auditable et un système qui dérive sans qu'on sache pourquoi.

---

## 6. Découpage en agents

La source recommande de spécialiser plutôt que d'avoir un agent unique. On suit,
avec quatre rôles et des cadences distinctes :

| Agent | Cadence | Rôle | Peut trader ? |
|-------|---------|------|---------------|
| **briefing** | 1×/jour avant ouverture | État du portefeuille, calendrier, régime | Non |
| **scanner** | toutes les 4 h en séance | Cherche des setups selon `skills/` | Non — propose seulement |
| **trader** | sur proposition du scanner | Pré-trade checks, émet le `Signal` | **Oui** |
| **reviewer** | 1×/semaine | Analyse les trades clos, propose des ajustements | Non |

Seul **trader** produit un signal exécutable. Le reviewer ne peut rien modifier
directement — il rédige des propositions.

---

## 7. Étapes

| Phase | Contenu | Sortie |
|-------|---------|--------|
| **0** | Runtime : orchestrateur + invocation headless + sortie structurée + validateur | Un cycle qui tourne à vide, sans décision réelle |
| **1** | Journalisation seule — l'agent décide, **rien n'est exécuté**. On compare ses décisions au marché a posteriori | Un mois de décisions journalisées |
| **2** | Paper sur démo Swissquote, allocation plafonnée | 3 mois minimum |
| **3** | Revue : ses décisions battent-elles un buy & hold ? Un tirage aléatoire ? | Verdict |
| **4** | Décision d'Adrian sur la suite | — |

**La phase 1 est celle qu'on ne doit pas sauter.** Journaliser sans exécuter coûte
un mois mais révèle les défauts de format, les hallucinations de prix, les
incohérences — avant tout risque, même en démo.

---

## 8. Ce qu'on saura mesurer

Un agent discrétionnaire n'a pas de courbe de backtest. Mais il a des décisions
datées, et ça suffit à répondre à des questions dures :

- Ses décisions battent-elles **buy & hold** sur la même période ?
- Battent-elles un **tirage aléatoire** de même fréquence et même taille ?
- Le **taux de réussite** est-il stable ou décroissant dans le temps ?
- Ses **niveaux de confiance** sont-ils calibrés — les décisions à confiance 0,9
  réussissent-elles plus souvent que celles à 0,5 ?

La dernière est la plus révélatrice. Un agent dont la confiance ne prédit rien
n'a pas de modèle du marché : il génère du texte plausible.

---

## 9. Question ouverte

Le coût. Une invocation headless avec contexte marché coûte quelques dizaines de
centimes. À quatre agents et plusieurs réveils par jour, l'ordre de grandeur est
de quelques euros par jour — soit plus que ce que 1 000 CHF de capital peut
raisonnablement produire.

**En phase de recherche c'est acceptable** : on paie pour savoir. En exploitation,
ça impose soit un capital très supérieur, soit une cadence réduite. À trancher
avant la phase 2, pas après.
