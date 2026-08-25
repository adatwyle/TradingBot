# 07 — Telegram et reporting

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Canal

Nouveau canal Telegram **TradingBot** (les bots du prototype ne sont pas réutilisés). Le canal échange quotidiennement avec Adrian sur l'activité du jour du bot. Il sert aussi à cc-support pour poser à Adrian des questions de clarification en mode QA, avec propositions de résolution et préconisation.

Contrainte technique héritée : `getUpdates` est exclusif par bot → bots dédiés (entrant / sortant séparés si nécessaire).

## Formats de compte rendu

### Quotidien
Une ligne par trade :

```
10:53 S001.CHF-USD SL -100chf
22:05 S001.CHF-USD TP +210chf
```

À la fin de la liste : un summary **total gain ou total perte** du jour.

### Fin de semaine
Résumé des gains/pertes **par jour** → **total gain/perte de la semaine**.

### Fin de mois
1. Résumé gains/pertes **par semaine** → **total gain/perte du mois**.
2. Résumé des **12 derniers mois**, mois par mois.

### Fin d'année
Résumé de l'année **par mois**.

## Règles

- Une ligne = une instance (`S0NN.XXX-YYY`), horodatée, motif de sortie (SL/TP), résultat en CHF.
- Fiabilité héritée du prototype : les curseurs de lecture n'avancent qu'après envoi réussi (un doublon est toléré, un trade manqué est interdit).
