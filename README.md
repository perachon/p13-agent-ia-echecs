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
