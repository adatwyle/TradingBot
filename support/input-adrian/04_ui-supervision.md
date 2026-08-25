# 04 — UI de supervision

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Constat sur le prototype

Les dashboards de la version 9.0.0.x ne sont pas vraiment connectés aux résultats de chaque stratégie. La nouvelle UI corrige cela.

## Exigences

1. **Découverte dynamique** : l'UI affiche une nouvelle stratégie **dès qu'un nouveau dossier est créé**. Zéro câblage manuel.
2. **Contrat de données standardisé** : chaque stratégie maintient/fournit ses données de performance dans un format standardisé ; l'UI les affiche. Le choix technologique (fichier alimenté par la stratégie, DB SQL, autre) est laissé à cc-spec — critère : affichage **live**.
3. **Vues d'ensemble** :
   - stratégies en cours de développement ;
   - stratégies en cours de validation paper trading ;
   - stratégies en production ;
   - courbes de tendance des gains et pertes de chaque stratégie.
4. **Drill-down** : sélectionner le dashboard d'une stratégie amène sur une **page dédiée** avec le détail de ses performances.
5. **Services communs visibles** : l'UI permet de visualiser les services communs de l'application, leur vie et leur contenu (console/factory, Telegram, datas, backtester, orchestrateur, tickets).
6. **Multi-paires** : les performances s'affichent par stratégie et par instance (`S0NN.XXX-YYY`).
