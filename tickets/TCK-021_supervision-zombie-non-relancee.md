---
id: TCK-021
from: cc-support
to: cc-app
status: open
blocking: false
created: 2026-09-12
---

## Question

Le journal de la fabrique du 10.09 à 02:02:43 (dernier tick avant le reboot) montre le
worker `supervision` dans cet état :

```
supervision   EN VOL   340h25 ago   4294967295 · code inattendu 4294967295 · 2475.0s en cours (340h25)
```

Un service persistant **« en vol » depuis 340 heures avec un code de sortie
anormal** (`4294967295` = −1 non signé : processus tué ou planté) n'est ni vivant ni
mort aux yeux de la fabrique. Le catalogue le déclare `SERVICE persistant — relance si
mort`, mais la relance ne s'est jamais déclenchée en quinze jours : la fabrique
considère qu'un processus dont elle détient encore un handle est « en vol », même
quand ce processus a rendu un code de sortie.

Conséquence : l'UI de supervision (port 8790) était injoignable pendant deux semaines
sans qu'aucune alerte ne parte — et la seule façon de le savoir était de lire le
journal.

## Proposition de résolution

Dans `app/orchestrator/tbot-factory.py`, pour les workers de nature `service` :

1. **Détecter la mort réelle** : un service dont `poll()` rend un code de sortie —
   quel qu'il soit — est mort ; le libellé « EN VOL » ne doit plus jamais coexister
   avec un code de sortie dans le tableau.
2. **Relancer avec recul** (`SERVICE_RESTART_BACKOFF_SEC` existe déjà) et compter les
   relances ; au-delà de N relances en 1 h, passer le worker en `AUTO-OFF` avec motif,
   comme pour les ticks.
3. **Sonde de vivacité** optionnelle par service (pour `supervision` : un GET sur
   `http://127.0.0.1:8790/` avec délai court) — un processus vivant qui ne répond plus
   est un zombie, à relancer aussi.
4. **Émettre une alerte** via le worker `notify` à chaque relance de service et à
   chaque passage AUTO-OFF.
5. Test : simuler un service qui rend un code de sortie sans être relancé aujourd'hui,
   vérifier la relance ; simuler un service qui vit mais ne répond pas à la sonde.

Préférence cc-support : 1 + 2 + 4 tout de suite (petit, testable), 3 en second temps.

## Réponse

<cc-app>
