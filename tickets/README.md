# Ticketting inter-CC

Un ticket = un fichier `TCK-NNN_<slug>.md` dans ce dossier. Numérotation séquentielle.

## Format

```markdown
---
id: TCK-001
from: cc-S013
to: cc-support
status: open | answered | closed
blocking: true | false
created: 2026-08-25
---

## Question
<question précise, contexte minimal suffisant>

## Proposition de résolution
<la ou les options vues par le demandeur, avec sa préférence>

## Réponse
<remplie par le destinataire ; si escaladé à Adrian : préconisation + décision>
```

## Règles

1. **Autonomie d'abord** : un CC décide seul des thématiques évidentes. Un ticket n'est ouvert que pour une vraie question — pas de bureaucratie, pas d'excès d'échanges.
2. **Bloquant** : `blocking: true` seulement si le développement est réellement arrêté. Le start hook de cc-support scanne les bloquants ; réponse évidente → cc-support répond seul immédiatement ; sinon QA Adrian avec préconisation.
3. Le demandeur propose toujours au moins une résolution — jamais de question nue.
4. `closed` par le demandeur une fois la réponse appliquée.
