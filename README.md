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

## Package Docker (Étape 6)

Objectif : une application prête pour démo avec **un seul** `docker compose up --build`.

### Démarrage complet (fresh install)

1. (Optionnel) Réinitialiser conteneurs + volumes (⚠️ supprime les données Milvus persistées)

```bash
docker compose down -v
```

2. Démarrer tous les services

```bash
docker compose up --build
```

3. Ouvrir l'application

- Frontend (Nginx) : `http://localhost:${FRONTEND_PORT:-8080}`
- API (FastAPI) : `http://localhost:${API_PORT:-8000}/api/v1/healthcheck`

Accès depuis un autre appareil du réseau (LAN) :

- Frontend : `http://<IP_DE_TA_MACHINE>:${FRONTEND_PORT:-8080}`
- API : `http://<IP_DE_TA_MACHINE>:${API_PORT:-8000}/api/v1/healthcheck`

(Selon Windows/pare-feu, il peut falloir autoriser Docker à écouter sur ces ports.)

Note CORS :

- Si tu utilises le frontend Docker (Nginx) via `http://<IP>:${FRONTEND_PORT}`, le navigateur appelle l'API via le même origin (`/api/...` et `/vector-search` reverse-proxy) : **pas besoin de CORS**.
- CORS est surtout utile quand tu appelles **directement** l'API depuis un autre origin (ex: `ng serve` ou une page différente). Dans ce cas, ajoute l'origin à `CORS_ALLOW_ORIGINS` (ex: `http://<IP_DE_TA_MACHINE>:4200`).

Sécurité (POC) : ne commit pas ton `.env` (tokens/clé YouTube). Utilise `.env.example` comme modèle.

Si le port `8080` est déjà utilisé sur ta machine, change `FRONTEND_PORT` dans `.env` (ou exporte la variable au moment du lancement) :

```powershell
$env:FRONTEND_PORT=8081
docker compose up --build
```

4. (Recommandé pour la démo) Charger le mini dataset Milvus

```bash
docker compose exec api python -m app.cli.ingest_sample
```

Optionnel (si tu as un export Wikichess en JSONL) :

```powershell
$env:WIKICHESS_JSONL_PATH = "C:\\path\\to\\wikichess.jsonl"
docker compose exec -e WIKICHESS_JSONL_PATH=$env:WIKICHESS_JSONL_PATH api python -m app.cli.ingest_wikichess
```

Sans ingestion, l'endpoint `/vector-search` peut répondre vide (aucun résultat), ce qui est normal.

Smoke test rapide via le frontend (PowerShell) :

```powershell
curl.exe -sS http://localhost:${FRONTEND_PORT:-8080}/api/v1/healthcheck
curl.exe -sS "http://localhost:${FRONTEND_PORT:-8080}/vector-search?q=sicilienne&top_k=3"
```

### Vérifier la persistance des volumes (Milvus)

Lister les volumes (PowerShell) :

```powershell
docker volume ls | Select-String milvus
```

Inspecter un volume (adapter le nom exact vu dans `docker volume ls`) :

```powershell
docker volume inspect <VOLUME_NAME>
```

Test de persistance conseillé :

1. Lancer l'ingestion (`ingest_sample`)
2. Vérifier `/vector-search`
3. `docker compose down` (sans `-v`)
4. `docker compose up -d`
5. Re-vérifier `/vector-search` : les données doivent toujours être là

## Étape 7 — Étude de faisabilité (analyse vidéo)

Note détaillée : [docs/etape7_etude_faisabilite_analyse_video.md](docs/etape7_etude_faisabilite_analyse_video.md)
