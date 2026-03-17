# Projet 13 — Agent IA ouvertures échecs (FFE)

POC (Proof of Concept) : agent IA pour l'apprentissage des ouvertures aux échecs.

## Démarrage (Étape 1)

Prérequis : Docker + Docker Compose.

1. Copier le fichier d'environnement (optionnel)

```bash
cp .env.example .env
```

Sur Windows (PowerShell) :

```powershell
Copy-Item .env.example .env
```

2. Démarrer l'API FastAPI

```bash
docker compose up --build
```

3. Vérifier le healthcheck

- `GET http://localhost:${API_PORT:-8000}/api/v1/healthcheck`

Réponse attendue :

```json
{"status":"ok"}
```

Test rapide (PowerShell) :

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/healthcheck
```

ou

```powershell
curl.exe -s http://localhost:8000/api/v1/healthcheck
```

## API (Étape 2)

Note : une FEN contient des espaces et des `/` ; elle doit être URL-encodée quand elle est passée dans l'URL.

Exemple de FEN (position initiale) :

```
rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
```

1. Coups théoriques (Lichess)

Si l'API renvoie une erreur `401` côté Lichess, renseigne `LICHESS_TOKEN` dans `.env` (voir `.env.example`).

```powershell
$fen = [uri]::EscapeDataString('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
curl.exe -s "http://localhost:8000/api/v1/moves/$fen"
```

2. Évaluation (Stockfish)

```powershell
$fen = [uri]::EscapeDataString('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
curl.exe -s "http://localhost:8000/api/v1/evaluate/$fen"
```

3. Endpoint agent (LangGraph : théorie sinon éval)

```powershell
$fen = [uri]::EscapeDataString('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
curl.exe -s "http://localhost:8000/api/v1/agent/$fen"
```

## RAG Milvus (Étape 3)

Note : pour garder une image Docker légère, les embeddings sont générés avec `fastembed` (ONNX Runtime), ce qui évite les gros downloads PyTorch/CUDA.

1. Démarrer Milvus (via Docker Compose)

```bash
docker compose up -d --build
```

2. Charger un mini dataset d'exemple dans Milvus

```bash
docker compose exec api python -m app.cli.ingest_sample
```

3. Tester la recherche vectorielle

```powershell
curl.exe -s "http://localhost:8000/vector-search?q=sicilienne%20ouverture&top_k=3"
```

## YouTube (Étape 4)

Cette étape utilise l'API **YouTube Data API v3**.

### Créer une clé API (Google)

1. Ouvrir Google Cloud Console et créer/sélectionner un projet
2. Activer l'API : **YouTube Data API v3**
3. Créer une **API key** (pas OAuth)
4. Mettre la clé dans `.env` : `YOUTUBE_API_KEY=...`

### Endpoint de recherche

```powershell
curl.exe -s "http://localhost:8000/api/v1/youtube/search?q=ouverture%20sicilienne&max_results=5"
```

## Frontend Angular (Étape 5)

Le frontend est dans le dossier `frontend/` et consomme l'API FastAPI sur `http://localhost:8000`.

### Démarrer l'API

Option 1 (recommandé) : via Docker Compose

```bash
docker compose up --build
```

Option 2 : en local (si tu as déjà un environnement Python)

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Démarrer le frontend

```bash
cd frontend
npm install
npm start
```

Puis ouvrir :

- `http://localhost:4200`

Fonctions testables dans l'UI :

- Échiquier (édition de la position) + bouton **Recommander** (appelle `/api/v1/agent/{fen}`)
- Recherche **Milvus** (appelle `/vector-search`)
- Recherche **YouTube** (appelle `/api/v1/youtube/search`)
