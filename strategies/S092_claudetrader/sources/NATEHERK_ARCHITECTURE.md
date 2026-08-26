# Source d'architecture — Nate Herk, agent de trading 24/7 en routines Claude Code

**Vidéo** : https://www.youtube.com/watch?v=6MC1XqZSltw
**Transcript** : `nateherk_routines.txt`
**Captures** : `../frames_nateherk/*.jpg`

Cette source ne fournit **pas une stratégie**. Elle fournit une **architecture
d'exécution**, et c'est précisément ce qui manquait à `s92_claudetrader`.

---

## 1. Pourquoi il n'y a rien à backtester ici

Ses décisions ne viennent pas d'un jeu de règles fixe : elles sont produites par
le modèle à chaque réveil, à partir de recherche web et de fichiers de mémoire.
On ne peut donc pas rejouer l'historique — l'agent n'existait pas à l'époque des
barres, et deux exécutions sur le même état ne rendent pas la même décision.

**Cela ne rend pas la chose intestable ; cela déplace le test.** On ne teste pas
une règle sur le passé, on mesure un processus en avant, contre des références
calculées en parallèle. C'est exactement ce que fait `core/backtest/allocation_engine.py`,
qui rend systématiquement le buy & hold de chaque constituant, l'équipondéré
naïf et le cash.

## 2. Ce qu'il annonce, et ce que ça vaut

> « I gave Opus $10,000 and we were able to beat the S&P by about 8% » — sur
> **30 jours**, une seule exécution.

Trente séances, un seul tirage, aucun témoin, aucun intervalle de confiance. Ce
n'est pas une preuve d'edge : c'est une observation. Il est à son crédit qu'il le
présente comme une expérience et non comme un résultat (« this is an experiment
for me »), et qu'il recommande explicitement de commencer en paper trading.

Il est également honnête sur un point que beaucoup escamotent : le benchmark
« agentic financial analysis » d'Anthropic **ne mesure pas** la capacité à
trader.

> « This benchmark rewards models that can digest filings and write coherent
> fundamentals-driven theses. And that maps to long-term or swing or
> fundamentals-driven strategies, not day trading. »

C'est juste, et ça cadre le périmètre : fondamental et horizon long, pas
scalping.

## 3. L'architecture, telle qu'il la décrit

### 3.1 Le problème central : un agent réveillé est amnésique

> « Every routine fires at 7 a.m., Claude Code basically wakes up essentially
> stateless. How do you make a stateless agent act disciplined and remember
> rules and learn over time? You do that with files and with context. »

Boucle : **réveil → lecture des fichiers → travail → réécriture des fichiers**.
Le fichier n'est pas un journal accessoire, c'est le seul vecteur de continuité.
Sa formule de fin le résume mieux que sa vidéo : *les fichiers ne sont pas la
mémoire de l'agent, ils sont sa discipline*.

### 3.2 La table des réveils (relevée sur la capture `t21m58s.jpg`)

Cinq déclencheurs, fuseau America/Chicago, jours ouvrés uniquement.

| # | Commande | Cron (CT) | Rôle | Écrit dans | Notifie ? |
|---|---|---|---|---|---|
| 1 | `/pre-market` | `0 6 * * 1-5` | recherche des catalyseurs, brouillon d'idées | `RESEARCH-LOG.md` | silencieux sauf urgence |
| 2 | `/market-open` | `30 8 * * 1-5` | exécute les trades planifiés, pose des stops suiveurs à 10 % | `TRADE-LOG.md` | seulement si un trade est passé |
| 3 | `/midday` | `0 12 * * 1-5` | coupe les perdants à −7 %, resserre les stops des gagnants | `TRADE-LOG.md` | seulement si action |
| 4 | `/daily-summary` | `0 15 * * 1-5` | clôture + récapitulatif | `TRADE-LOG.md` | toujours |
| 5 | `/weekly-review` | `0 16 * * 5` | bilan hebdomadaire + leçons | `WEEKLY-REVIEW.md` | toujours |

Deux seuils chiffrés et donc reproductibles : **stop suiveur 10 %**, **coupe des
perdants à −7 %**.

### 3.3 Garde-fous explicites

Il insiste : un agent autonome est *zélé*, il faut le borner avant de le lâcher.
Exemples qu'il cite : maximum 5 % du portefeuille par position, plafond de perte
quotidien, pas plus de trois nouvelles positions par semaine, jamais d'options.

Chez nous, ces bornes ne vivent pas dans le prompt : elles appartiennent à
`core/risk/` (R2 — la stratégie exprime une intention, la couche risque décide de
l'exposition). C'est plus robuste que sa version, où le garde-fou n'est qu'une
phrase que le modèle peut négliger.

### 3.4 Persistance en exécution distante

Point d'ingénierie non trivial. Une routine distante **clone le dépôt, travaille,
puis détruit son environnement**. Si l'agent ne pousse pas ses fichiers, la
mémoire est perdue à chaque cycle.

> « Make sure that all of these files that it's actually updating, it's able to
> push back and commit back to main. Otherwise the next agent's not going to pick
> it up and then what's even the point? »

Implique : dépôt Git dédié, poussées autorisées sur la branche principale, et
secrets en variables d'environnement — **jamais dans le dépôt**. Il rapporte
d'ailleurs avoir eu une clé Alpaca en clair dans les fichiers migrés, détectée
par Claude, et l'avoir fait tourner.

### 3.5 Pile technique

Alpaca (courtier, compte papier à 100 k$ par défaut), Perplexity (recherche),
ClickUp (notifications). Interchangeables.

## 4. Ce qu'on reprend, ce qu'on ne reprend pas

| Élément | Décision |
|---|---|
| Boucle réveil → lecture → action → réécriture | **repris**, c'est le cœur |
| Découpage en réveils par moment de marché | **repris**, avec nos fuseaux |
| Stop suiveur 10 %, coupe à −7 % | **repris comme paramètres**, à balayer, pas à graver |
| Garde-fous d'exposition | **repris mais déplacés** dans `core/risk/` (R2) |
| Persistance Git + secrets en variables d'environnement | **repris** |
| Alpaca / Perplexity / ClickUp | **remplacés** — notre courtier est Swissquote (MT5) |
| « +8 % contre le S&P » comme preuve | **rejeté** — n = 1 sur 30 séances |

## 5. Ce que nous ajoutons, et qui manque chez lui

1. **Une référence calculée en continu.** Il compare une courbe à un indice au
   bout de 30 jours. Notre harnais d'allocation rend le buy & hold et
   l'équipondéré naïf à chaque pas — la question « bat-on l'effort zéro ? » est
   répondue en permanence, pas rétrospectivement.
2. **Un journal de décision exploitable.** Chaque décision doit être écrite avec
   son état d'entrée, de sorte qu'on puisse plus tard mesurer la contribution de
   chaque famille de décision — pas seulement lire le récit de l'agent.
3. **L'aveu d'incertitude.** Sur 30 séances, l'écart contre l'indice est
   indistinguable du bruit. Toute restitution de `s92` doit afficher l'effectif
   et l'intervalle, sous peine de reproduire l'erreur qui a déjà coûté à ce
   projet (un « strict pass » sur 19 trades pris pour un succès).
