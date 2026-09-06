# doudtrading — provenance du corpus

**Chaîne** : `Doud Trading` — <https://www.youtube.com/@TheQueenDoud> (8 010 abonnés).
**Ce qui est ici** : les **lives publics et gratuits**, pas le produit payant.

| | |
|---|---|
| Streams listés sur la chaîne | 40 |
| Transcriptions obtenues | **35** (5 échecs : piste absente ou stream sans sous-titres) |
| Durée cumulée | **54 heures** |
| Segments horodatés | **68 984** |
| Langue | `fr`, sous-titres **générés automatiquement** |
| Date de collecte | 2026-09-06 |

## Ce que sont ces lives

Du scalping XAUUSD en direct, sur événement identifié — la série la plus fournie
est « scalping GOLD pendant les inscriptions hebdomadaires au chômage » (jeudi,
publication à 14h30 CET), plus des lives NFP, FOMC, discours de Powell, et des
sessions asiatiques de nuit. Durées de 43 à 191 minutes.

Elle y annonce ses points d'entrée, ses stops, ses TP, ses clôtures partielles et
ses ratios à voix haute, en temps réel, à sa communauté. C'est la raison d'être de
ce corpus : le podcast (`docs/sources/moneytalk/`) la fait **raconter** sa méthode,
ces lives la montrent l'**exécuter** — et sur quatre points les deux divergent
(cf. `SYNTHESE_METHODE.md` § 0).

## Obtention

`yt-dlp -J --flat-playlist` sur l'onglet `/streams` pour l'inventaire (l'accès web
direct bute sur le mur de consentement YouTube), puis `youtube_transcript_api`
piste `fr` par vidéo. Un segment par ligne, horodatage `[mmm:ss]` en tête, aucune
retouche.

**Limite de la source, à garder en tête pour toute citation** : la reconnaissance
vocale déforme systématiquement les nombres et les termes techniques — « SL » →
« essel » / « celle », « lot » → « l'eau », « mèche de rejet » → « mèche de
Roger », prix tronqués (« les 68 » pour 4368). `SYNTHESE_METHODE.md` ne s'appuie
donc que sur des énoncés de **règle**, qui restent lisibles malgré le bruit, et
jamais sur une extraction chiffrée automatique.

## Fichiers

- `lives/<video_id>.txt` — 35 transcriptions brutes, en-tête titre + métadonnées.
- `INDEX_lives.md` — inventaire trié par durée.
- `EXTRAIT_regles.txt` — 104 passages de 90 s sélectionnés pour leur densité en
  vocabulaire de règle (entrée, SL, TP, break-even, taille, niveaux) : c'est le
  sous-corpus effectivement lu pour produire la synthèse.
- `SYNTHESE_METHODE.md` — la méthode reconstituée, et les quatre corrections
  qu'elle impose au dossier `strategies/S018_gold_doud_v2/`.


---

## Addendum 2026-09-06 — les trois autres plateformes, passées au crible

Sur demande d'Adrian, les trois liens restants ont été testés un par un.

### TikTok `@doudtrading_` — **exploité**, et plus riche que prévu

**276 clips listés**, 168 minutes cumulées. Sous-titres `fra-FR` fournis par
TikTok, donc transcriptibles. 120 clips retenus sur critère de titre (terme de
méthode), **67 transcrits** et versionnés dans `tiktok/`.

Première évaluation (sur 15 clips) : « remontages du podcast, faible valeur ».
**Elle était fausse**, et la correction vaut d'être notée : les publications
d'août-septembre 2026 sont effectivement des remontages, mais les clips
**originaux de 2025** contiennent les énoncés doctrinaux les plus précis de tout
le corpus — dont ses deux sources d'information, sa définition de l'équilibre, et
sa règle de placement du stop. Voir `SYNTHESE_TIKTOK.md`.

### Instagram `@doudtrading` — **inaccessible**

Mur de connexion. `yt-dlp` signale son extracteur Instagram comme cassé et
échoue à extraire quoi que ce soit sans session authentifiée. Contourner une
authentification n'est pas une option. **Aucune donnée collectée.**

### Discord *🌕 Doud Trading 🌕* — **fermé, sauf métadonnées publiques**

| Donnée | Valeur |
|---|---|
| guild id | `1284955967188107385` |
| membres | **3 467** (245 en ligne au moment de la mesure) |
| boosts | 4 |
| **niveau de vérification** | **4 — le plus élevé** (téléphone vérifié exigé) |
| canal d'accueil | `⚠️｜avertissements` |
| widget public | **désactivé** (HTTP 403) |

Rien d'autre n'est lisible sans rejoindre le serveur, ce qui suppose de créer un
compte et d'accepter des conditions — deux gestes qui me sont interdits. Le
niveau de vérification 4 signifie qu'**Adrian lui-même** aurait besoin d'un
compte à téléphone vérifié.

**Ce qui reste derrière cette porte, et pourquoi ça vaut le geste** : la
*météo de Doudi*, publiée gratuitement chaque dimanche, que ses propres clips
confirment (« retrouve la météo des marchés sur mon Discord tous les dimanches »,
`tiktok/7430957771475930400`). C'est un historique daté de prévisions
directionnelles chiffrées — le seul matériau permettant de scorer ses 65 %/35 %
contre le mouvement réel de l'or.
