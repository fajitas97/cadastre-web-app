# Cadastre Finder — déploiement rapide

Ce dépôt contient une application **Streamlit** (MVP) qui reprend la logique de ton notebook Colab :
- Chargement du GeoJSON cadastre (départemental)
- Sélection multiple de communes (recherche intégrée)
- Saisie de la surface recherchée
- Tableau final avec nom parcelle, code INSEE, nom commune, surface, liens (Géoportail / Maps / Street View / API Adresse)
- Export CSV téléchargeable
- Cache pour éviter les téléchargements répétés

---

## Contenu
```
cadastre-web-app/
├─ streamlit_app.py
├─ requirements.txt
├─ Procfile
└─ .streamlit/config.toml
```

## 1) Tester localement (recommandé avant déploiement)

Prérequis : Python 3.9+ et (idéalement) un environnement virtuel.

```bash
python -m venv .venv
source .venv/bin/activate      # mac/linux
.venv\\Scripts\\activate       # windows (PowerShell)
pip install --upgrade pip
pip install -r requirements.txt
streamlit run streamlit_app.py
```

> **Remarque importante** : `geopandas` et ses dépendances (GDAL, Fiona, etc.) requièrent souvent des paquets système (libgdal, proj, etc.).
> - Sur une machine locale (Linux), installez via `apt` (ex: `sudo apt-get install -y gdal-bin libgdal-dev libproj-dev proj-bin libgeos-dev`)
> - Si l'installation pip échoue, préférez un conteneur Docker (instructions plus bas) ou conda/mamba.

---

## 2) Déployer rapidement : Streamlit Community Cloud (le plus simple)

1. Crée un dépôt GitHub et pousse ce projet.
2. Va sur https://streamlit.io/cloud et connecte ton compte GitHub.
3. Crée une nouvelle app en liant ton dépôt, choisis la branche `main` (ou `master`) et `streamlit_app.py` en tant que fichier d'entrée.
4. Lance le déploiement. Streamlit Cloud installera `requirements.txt` automatiquement.

**Limite** : Streamlit Cloud peut échouer à construire `geopandas` si les dépendances système ne sont pas présentes. Si cela échoue, passe à l'option Docker / Render ci-dessous.

---

## 3) Déployer avec Docker (forte compatibilité, recommandé si dépendances géospatiales posent problème)

### a) Créer un `Dockerfile` (exemple simplifié)
```dockerfile
FROM python:3.11-slim

# installer dépendances système pour GDAL / PROJ
RUN apt-get update && apt-get install -y --no-install-recommends \ 
    build-essential gdal-bin libgdal-dev libproj-dev proj-bin proj-data \ 
    libgeos-dev libspatialindex-dev \
    && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /app
COPY . /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.headless", "true"]
```

### b) Construire et tester localement
```bash
docker build -t cadastre-app .
docker run -p 8501:8501 cadastre-app
```

### c) Déployer sur Render / Railway / Heroku (via image Docker)
- Sur Render : créer un service Web "Docker" en pointant sur ton repo et Render construira l'image.
- Sur Heroku : `heroku container:push web && heroku container:release web`

---

## 4) Remarques d'optimisation
- Le GeoJSON complet peut être massif. Pour accélérer :
  - Prétraite et exporte un fichier contenant uniquement les colonnes utiles (id, commune, contenance, geometry) en GeoPackage ou CSV + centroid, puis héberge-le.
  - Ou découpe le cadastre par communes et charge uniquement les communes demandées.
- Si tu veux, je peux t'aider à :
  - Prétraiter le GeoJSON et générer un fichier allégé,
  - Préparer un `Dockerfile` et le tester ici pour toi,
  - Générer un repo GitHub automatiquement avec ces fichiers.
