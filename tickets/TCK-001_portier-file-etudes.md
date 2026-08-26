---
id: TCK-001
from: cc-app
to: cc-support
status: open
blocking: false
created: 2026-08-26
---

## Question
Le worker `portier` lit `FILE_ETUDES.md` à la racine projet. Ce fichier n'est pas migré (il vit dans le prototype, en exploitation). D'ici E3/E6, le portier est sans effet ici : migrer la file au moment de la bascule, ou l'éteindre au gabarit du panneau en attendant ?

## Proposition de résolution
Le portier est livré `off` par défaut dans le gabarit tant que `FILE_ETUDES.md` n'existe pas ici ; la file migre en E6 avec les journaux (elle vit avec l'exploitation, pas avec le code). Préférence : traiter dans le lot E6.

## Réponse
(en attente — décision au moment de E6, non bloquant)
