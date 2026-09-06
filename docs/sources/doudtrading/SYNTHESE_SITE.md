# doudtrading.fr et tradermade.io — dépouillement A à Z

> **Méthode** : sitemap XML puis visite de chaque page déclarée, plus les pages
> atteignables par les liens du menu, plus la plateforme partenaire et son blog
> et ses pages légales. Navigateur intégré, lecture seule, aucun formulaire
> soumis, aucun lien d'invitation suivi.
> **Date** : 2026-09-06.

**Ce que ce dépouillement cherchait.** Pas du contenu de méthode — il est ailleurs
(`SYNTHESE_METHODE.md`, `SYNTHESE_TIKTOK.md`). Ici on cherche le **contexte
probatoire** : que promet-elle, à qui, contre quoi, et **existe-t-il quelque part
un relevé de performance auditable** ? Cette dernière question conditionne tout
le crédit qu'on accorde à la source.

---

## 1. Note préalable — ce que son `robots.txt` déclare

```
User-agent: *
Content-Signal: search=yes, ai-train=no, use=reference
Allow: /
```

Réservation de droits **explicite** au titre de l'article 4 de la directive UE
2019/790. Traduction : indexation autorisée, **entraînement de modèle interdit**,
consommation « par référence » autorisée. Notre usage — lire pour analyser, citer
en référençant — relève de `use=reference`. Aucun entraînement n'est fait ni
prévu. Le signal est consigné ici pour que la limite soit écrite, pas supposée.

---

## 2. doudtrading.fr — inventaire complet

Sitemap : 7 URL. Deux pages supplémentaires atteignables par le menu
(`accompagnement-classique.html`, `accompagnement-vip.html`).

| Page | Objet | Prix affiché |
|---|---|---|
| `/` | vitrine | — |
| `/lives.html` | abonnement lives | **39,99 €/mois**, sans engagement, 3-5 sessions/semaine dès 14h |
| `/accompagnement-classique.html` | 3 mois, groupe, 2h/sem + replays + communauté privée | **1 790 €** + **4,99 € pour réserver l'appel** |
| `/accompagnement-vip.html` | 3 mois en privé, 2h/sem + WhatsApp direct | sur candidature, prix non affiché |
| `/pamm.html` | sondage d'intérêt pour un compte PAMM chez « AGBK (broker régulé) » | ticket d'entrée **1 000 €** |
| `/seminaire.html` | séjour 5j/4n camping 4★ presqu'île de Giens, 4 après-midi de trading live | **500 €** sans pension / **770 €** pension complète, acompte 150 € |
| `/challenge.html` | challenge gratuit 3 jours (5-7 nov. 2025), 300 places | gratuit, prix à gagner 1 200 € |
| `/annonces.html` | compte à rebours du prochain rendez-vous | — |
| `/goodies.html` | boutique textile (hoodie 59,99 €, t-shirt 29,99 €, mug 14,99 €) | — |

**Communauté annoncée** : « +3000 traders ». La plateforme communautaire n'est
plus Discord mais **TraderMade** (§ 4).

### 2.1 Les chiffres de performance affichés

Deux pages les répètent à l'identique — `/pamm.html` et `/challenge.html` :

| Métrique | Valeur affichée |
|---|---|
| Performance | **+145 %** sur « 24/25 » — et **+127 % en 2024** plus bas sur la même page PAMM |
| Taux de réussite | **89 %** |
| Drawdown max | **28 %** |
| Ratio de Sharpe | **5,6** |

Trois observations, factuelles :

1. **Contradiction interne** : `+145 % 24/25` en tête de la page PAMM,
   `+127 % en 2024` dans le même document.
2. **Incohérence arithmétique** : un Sharpe de 5,6 coexistant avec 28 % de
   drawdown est très difficile à obtenir simultanément — le Sharpe mesure la
   régularité, le drawdown mesure l'accident ; les deux valeurs décrivent des
   régimes opposés.
3. **Aucune source** : ni relevé de courtier, ni lien Myfxbook/FXBlue, ni période
   de mesure précise, ni méthodologie de calcul.

### 2.2 Une anomalie éditoriale à signaler

Les deux pages payantes les plus chères décrivent Doud **au masculin** :

> « Doud, c'est **le fondateur** de DoudTrading et **le trader** derrière toute
> la communauté. […] une méthode qu'**il** a forgée trade après trade,
> **il** t'apprend à lire le marché comme **il** le fait »
> — `/accompagnement-classique.html` **et** `/accompagnement-vip.html`

Alors que la page d'accueil, la page PAMM et le challenge disent « **tradeuse** »,
« elle ». L'hypothèse la plus économique est un gabarit de texte non adapté —
mais il s'agit des pages qui vendent un programme à **1 790 €**, et elles ne
disent pas correctement qui l'anime.

### 2.3 Pages légales absentes

`/mentions-legales` et `/cgv` **redirigent vers la page d'accueil** : aucune
mention légale, aucune condition générale de vente publiée sur un site marchand
français qui encaisse des paiements par carte. C'est un constat de fait, pas une
qualification juridique.

### 2.4 Ressorts commerciaux relevés

Rareté et urgence, systématiques : « DERNIER ACCOMPAGNEMENT CLASSIQUE — IL N'Y EN
AURA PLUS APRÈS », « pas de prochaine session, pas de liste d'attente », « places
très limitées », « 300 PLACES LIMITÉES », « BONUS EXCLUSIF — 100 PREMIERS
INSCRITS », « premier arrivé, premier servi ». Les quatre témoignages de la page
d'accueil sont tous signés « — Membre TraderMade », sans nom ni vérifiabilité.

---

## 3. Ce que le challenge révèle de sa méthode

`/challenge.html` décrit le mécanisme de participation, et c'est
opérationnellement instructif :

> « Suivez les sessions live avec Doud · **Tradez sur les points d'entrée qu'elle
> partage** · **Optimisez vos entrées sur les zones partagées** »

Et le classement : « performance globale, **respect du risk management**, nombre
de trades gagnants, **ratio risque/rendement** et **régularité** ». Le jury ne
note donc pas le seul PnL — cohérent avec son discours sur la discipline.

Point de méthode également : « Il n'y a **pas de replay** prévu. Il est donc
important d'être présent en direct » — sa valeur ajoutée est explicitement
**temps réel**, ce qui confirme que ce qu'on ne peut pas reconstruire depuis les
archives, c'est le timing.

---

## 4. tradermade.io — la plateforme, et la piste de l'audit

Doud a quitté Discord pour **Tradermade**, plateforme multi-coachs
(« Learn · Evolve · Trade · Repeat »), où elle figure comme :

> `LIVE · D · Doud · Scalping · Gold (XAU/USD) · US & Asian sessions · 3-5 lives / week`

Inscription gratuite annoncée, sans carte bancaire.

### 4.1 La promesse d'audit — et son démenti dans les CGU

C'était la trouvaille attendue de ce dépouillement : **existe-t-il un relevé
auditable ?** Trois formulations coexistent sur le même site, et elles ne disent
pas la même chose.

| Emplacement | Formulation |
|---|---|
| Page d'accueil (marketing) | « All our coaches actively trade. **All submit their results to an independent audit each quarter.** » |
| Blog, recrutement des coachs | « **Tous nos coachs font auditer leurs résultats par un tiers indépendant.** » — et « **Refuser l'audit trimestriel** » figure dans la liste des rejets systématiques |
| **Avis sur les risques, § 06 (texte contraignant)** | « Elles **peuvent faire l'objet** d'un audit indépendant **à intervalle régulier** » |

Le marketing dit *tous, chaque trimestre, obligatoire*. Le texte juridique dit
*peuvent, à intervalle régulier*. **Et aucun audit n'est publié nulle part sur le
site.**

**Conclusion pour notre dossier** : le relevé auditable que j'espérais **n'est
pas démontré**. La position de `SYNTHESE_METHODE.md` § 4 ne change pas — la
source vaut pour ses hypothèses de marché, pas pour ses résultats.

### 4.2 Ce que le dossier de candidature coach contient — et pourquoi ça compte

C'est l'information la plus utile de tout le dépouillement. Pour être accepté,
un coach Tradermade doit fournir :

> - « **Un journal de trading sur une période significative. Pas un screenshot.
>   Un export complet, avec les pertes, les hésitations, les jours sans.** »
> - « **Une présentation de la méthode. Écrite. Avec ses limites, ses biais, ses
>   cas où elle ne marche pas.** »
> - Des références (« on appelle »), et une lettre de motivation.

Puis une **session live d'essai** devant un panel, jugée non sur le PnL mais sur
la lisibilité du raisonnement : « On ne cherche pas la performance. On cherche la
lisibilité. »

**Si Doud a passé ce filtre, alors les deux artefacts que j'ai passé cette
session à reconstituer depuis 54 heures de parole existent sous forme écrite** :
un export de journal complet, et une description de sa méthode avec ses limites
et ses cas d'échec. Ils sont détenus par Tradermade, pas publiés — mais leur
existence est affirmée par la plateforme elle-même.

### 4.3 Deux tensions entre les critères affichés et son offre

La liste des rejets systématiques de Tradermade comprend :

> - « **Promettre un pourcentage.** Aucun coach Tradermade ne dit "tu vas gagner
>   X %". On éduque, on n'oracle pas. »
> - « **Vendre des formations à plusieurs milliers d'euros ailleurs.** Si ton
>   modèle économique repose sur des produits à 3 000 € le pack, ce n'est pas le
>   nôtre. »

Or `doudtrading.fr` affiche **+145 %, 89 % de réussite, Sharpe 5,6** en page
PAMM et challenge, et vend un accompagnement à **1 790 €** plus un VIP au prix
non publié. Les deux critères ne sont pas franchis au sens strict — 1 790 € n'est
pas 3 000 € — mais l'écart entre la charte affichée et l'offre réelle est mince,
et il est visible depuis les deux sites.

### 4.4 Identité de l'éditeur

> « Le site tradermade.io est édité par **TRADERMADE LIMITED**, société à
> responsabilité limitée immatriculée à **Hong Kong**. »
> Numéro d'immatriculation (CR No.) : **`[À compléter]`**
> Numéro d'enregistrement (BR No.) : **`[À compléter]`**
> Adresse postale : **`[À compléter — adresse complète enregistrée à HK]`**
> — Mentions légales, dernière mise à jour **mai 2026**

Les mentions légales sont publiées avec **les identifiants de la société laissés
en champs à compléter**, quatre mois après leur dernière mise à jour déclarée.
Constat de fait.

La société déclare par ailleurs, correctement, n'être **pas titulaire d'une
licence SFC de Hong Kong**, ne fournir aucun service d'investissement, aucune
gestion pour compte de tiers, aucun conseil personnalisé — et renvoie vers la
SFC, l'AMF et l'ESMA pour l'information sur les risques. Le dispositif de
décharge est complet et bien rédigé ; c'est le contraste avec les chiffres
affichés en vitrine qui est notable.

---

## 5. Ce que ce dépouillement change pour la mission

| Question | Réponse |
|---|---|
| Existe-t-il un relevé auditable de ses performances ? | **Non démontré.** Promesse marketing d'audit trimestriel, texte contraignant en « peuvent faire l'objet », rien de publié. |
| Une description écrite de sa méthode existe-t-elle ? | **Oui, affirmée** — dossier de candidature Tradermade, avec limites et cas d'échec. Non publique. |
| Un journal de trading complet existe-t-il ? | **Oui, affirmé** — export complet exigé au recrutement. Non public. |
| Le site apporte-t-il du contenu de méthode ? | **Marginalement** : la mécanique du challenge confirme qu'elle partage des « points d'entrée » et des « zones », et que sa valeur est temps réel (pas de replay). |
| Faut-il réviser la lecture de la source ? | **Non.** `SYNTHESE_METHODE.md` § 4 tient : hypothèses de marché oui, résultats non. |

**Piste ouverte, à l'arbitrage d'Adrian** : les deux artefacts du § 4.2 sont
exactement ce qui manque au dossier. Ils ne sont pas publics, mais leur existence
est affirmée par un tiers. Une demande directe — à elle ou à Tradermade — est
un geste gratuit dont le pire résultat est un refus.
