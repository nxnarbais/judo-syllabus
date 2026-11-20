# Référentiel Judo — Ceintures & Chevrons

Application statique sans connexion ni étape de build pour réviser les techniques de Judo par ceinture et chevron.

## Structure

- `index.html` : Interface statique (Alpine.js via CDN), filtres par ceinture, type (`Nage-waza` / `Katame-waza`), statut de révision et recherche instantanée.
- `style.css` : Mise en page responsive mobile-first, thème clair inspiré du judogi (coton écru, tatami, encre sumi, indigo).
- `syllabus.json` : Source de données unique (programme du dojo avec chevrons + référentiel officiel SJV / ASJ).
- `sw.js`, `manifest.webmanifest`, `icon.svg` : Fonctionnement hors ligne et installation sur l'écran d'accueil (PWA).
- `scripts/validate_syllabus.py` : Vérifie la cohérence de `syllabus.json` (à lancer après chaque modification).
- `scripts/discover_videos.py` : Script optionnel (`yt-dlp`) pour récupérer des vidéos candidates à visionner et valider.

## Fonctionnalités

- **Recherche tolérante** : insensible aux accents, à la casse et aux tirets (`osoto` trouve O-soto-gari, `cle` trouve « clé »).
- **Suivi de progression** : chaque technique peut être marquée « acquise » ; la progression par ceinture et par programme est enregistrée dans le navigateur (`localStorage`, propre à chaque appareil). Le filtre « À revoir » n'affiche que ce qui reste à travailler.
- **Révision cumulative** : avec une ceinture sélectionnée, « Inclure les ceintures précédentes » affiche tout le programme jusqu'à ce niveau, utile pour préparer un passage de grade.
- **Liens directs** : l'URL reflète le programme ou la ceinture choisie (`#sjv`, `#ceinture-verte`…).
- **Hors ligne** : après une première visite, l'application fonctionne sans réseau (les miniatures YouTube exceptées).

## Lancer en local

Les navigateurs bloquent `fetch('syllabus.json')` sur `file://`. Lancez un petit serveur HTTP local :

```bash
python3 -m http.server 8000
```

Puis ouvrez `http://localhost:8000`.

## Modifier le référentiel

Après chaque modification de `syllabus.json` :

```bash
python3 scripts/validate_syllabus.py
```

Le script signale les identifiants de technique inconnus, les groupes invalides, les identifiants de ceinture en double et les vidéos mal renseignées.

## Ajouter une vidéo validée

Dans `syllabus.json`, sous `techniques.<id>.videos`, renseignez :

```json
"baseline": {
  "title": "Kodokan Official - O-soto-gari",
  "url": "https://www.youtube.com/watch?v=VIDEO_ID&t=12s",
  "youtube_id": "VIDEO_ID",
  "channel": "KODOKAN"
},
"mistakes_and_counters": [
  {
    "title": "Erreurs fréquentes sur O-soto-gari",
    "url": "https://www.youtube.com/watch?v=VIDEO_ID&t=45s",
    "youtube_id": "VIDEO_ID",
    "channel": "Shintaro Higashi",
    "note": "Ne pas rester loin de uke ; avancer le pied d'appui au niveau du sien."
  }
]
```

## Découvrir des vidéos candidates (optionnel)

```bash
brew install yt-dlp
python3 scripts/discover_videos.py --only-missing --limit 10
```

Les résultats sont enregistrés dans `scripts/candidates.json`, les chaînes de confiance (Kodokan, Shintaro Higashi…) en premier avec `"trusted": true`.

## Déploiement

Déposez simplement `index.html`, `style.css`, `syllabus.json`, `sw.js`, `manifest.webmanifest` et `icon.svg` sur **GitHub Pages** ou **Cloudflare Pages** (HTTPS requis pour le mode hors ligne).

Les modifications de `syllabus.json` sont visibles immédiatement ; celles de `index.html` / `style.css` au rechargement suivant. Si vous changez la version d'Alpine.js, mettez aussi à jour l'URL et `CACHE_VERSION` dans `sw.js`.
