# Étape 7 — Étude de faisabilité : système avancé d’analyse vidéo (échecs)

Date : 2026-03-17

## 1) Contexte et objectif

Le responsable demande de **concevoir** (sans implémenter) un système capable d’analyser des vidéos d’échecs (cours, parties filmées, contenus pédagogiques) pour :

- **Détecter l’échiquier** dans une vidéo et suivre sa position dans le temps.
- **Reconnaître les pièces et les coups** (séquence de mouvements) de manière robuste.
- **Interpréter** la partie (ou l’exercice) : ouverture, plans typiques, erreurs fréquentes.
- **Produire des recommandations** (moteur Stockfish) et des ressources (théorie, vidéos).

L’enjeu business principal est d’augmenter la valeur pédagogique : transformer un support vidéo « passif » en support « actif » (extraction de positions, quiz, recommandations, parcours d’apprentissage).

Cette note propose une architecture **modulaire, évolutive** et compatible avec le **Model Context Protocol (MCP)**, afin de connecter proprement les composants « vision », « moteur d’échecs », « stockage » et « recherche ».

## 2) Bénéfices attendus

### 2.1 Bénéfices produit / pédagogie

- **Indexation automatique** d’une vidéo : chapitrage par positions clés (tactiques, transitions d’ouverture, moments critiques).
- **Génération d’exercices** : « rejouer la position à t=12:34 », « trouver le meilleur coup », etc.
- **Personnalisation** : relier les erreurs du joueur à un plan d’apprentissage (ouvertures associées, vidéos FR, exercices).
- **Réutilisation** : un même pipeline d’analyse peut servir à plusieurs formats (cours en salle filmés, streaming, contenus pédagogiques internes).

### 2.2 Bénéfices techniques

- **Découplage** via MCP : chaque brique peut évoluer (nouveau modèle vision, nouveau stockage, nouveau moteur) sans réécrire l’orchestrateur.
- **Observabilité** : journaliser outils MCP + artefacts (frames, FEN, PGN) pour débogage.

## 3) Limites et contraintes

- **Vision en conditions réelles** : angles obliques, reflets, mains qui masquent, pièces partiellement visibles.
- **Variabilité** : échiquiers, thèmes, pièces non standard, résolution vidéo, compression.
- **Ambiguïtés** : deux pièces proches, promotions, roque, prise en passant, pièces hors champ.
- **Coût** : traitement vidéo (CPU/GPU) + stockage frames/artefacts peut vite devenir dominant.
- **Conformité** : droits sur les vidéos, consentement si visages/voix, durée de conservation.

Conclusion : un système « 100% automatique » doit être envisagé avec un **mode “assisté”** (validation humaine / correction) pour atteindre la qualité attendue en production.

## 4) Hypothèses de dimensionnement (pour chiffrage)

Les coûts varient fortement. Pour rester réaliste, on chiffre sur un scénario « POC → pilote → prod ».

### 4.1 Hypothèses vidéo

- Vidéo typique : 30 minutes, 1080p, 30 fps.
- Analyse :
  - extraction à 1 fps pour la détection plateau (réduction x30),
  - + bursts plus fins (ex: 5–10 fps) autour des moments où un mouvement est détecté.

### 4.2 Volumes

- POC : 10–50 vidéos / mois.
- Pilote : 200 vidéos / mois.
- Prod : 2 000 vidéos / mois.

### 4.3 Qualité cible

- POC : succès partiel acceptable (ex: 70% des coups corrects sur vidéos contrôlées).
- Pilote : viser >90% sur un corpus « standardisé ».
- Prod : viser >95% sur plusieurs conditions (sinon prévoir un workflow de correction).

### 4.4 Métriques de succès (à instrumenter dès le POC)

Pour éviter un débat subjectif (« ça marche / ça ne marche pas »), on définit des métriques mesurables :

- **Board ROI success rate** : % de frames où le plateau est localisé avec confiance > seuil.
- **Homography stability** : variance de la grille (dérive) d’une frame à l’autre.
- **Square classification accuracy** : exactitude par case (top-1), et matrice 8×8 complète.
- **Move accuracy** : % de coups (UCI) corrects vs vérité terrain (PGN de référence).
- **Move completeness** : % de coups manquants (skip) ou inventés (hallucination).
- **Time-to-result** : latence batch (minutes/vidéo) et coût/vidéo.

Recommandation : publier automatiquement un rapport par vidéo (JSON) contenant ces métriques, pour itérer rapidement.

## 5) Panorama technologique : détection échiquier & pièces

### 5.1 Approche classique (OpenCV / géométrie)

Idée : détecter une grille (coins internes), corriger la perspective (homographie), puis segmenter cases/pièces.

- Avantages :
  - explicable, rapide sur CPU,
  - performant en conditions « propres » (éclairage stable, plateau visible, peu d’occlusion).
- Limites :
  - fragile en présence de mains, motion blur, reflets,
  - échoue si la grille n’est pas clairement détectable.

Briques typiques (OpenCV) :

- Détection de pattern type « chessboard corners » (utile aussi en calibration) : `findChessboardCorners`, `cornerSubPix`.
- Estimation de pose / projection : `solvePnP`.
- Homographie : redresser l’échiquier pour obtenir une vue « top-down ».

### 5.2 Approche par modèles de vision (DL)

Idée : utiliser des modèles entraînés (ou fine-tunés) pour :

- localiser l’échiquier (detection/segmentation),
- détecter et classer les pièces,
- éventuellement, estimer directement l’état du plateau.

- Avantages :
  - meilleure robustesse aux variations,
  - peut gérer la perspective et des plateaux non “parfaits”.
- Limites :
  - besoin de données et d’annotation,
  - coût d’inférence (souvent GPU si on veut du quasi temps réel),
  - dérive avec nouveaux styles de pièces/plateaux.

Technos possibles :

- Détection d’objets : YOLO/RT-DETR (échecs : classes {roi échiquier} et/ou {pièces}).
- Segmentation : Mask R-CNN / SAM2-like pour isoler plateau et pièces.
- Estimation d’état : modèle « case → classe pièce » via CNN/ViT après redressement.

### 5.3 Stratégie recommandée (réaliste)

Une stratégie robuste et industrialisable combine :

1. **Détection ROI échiquier** (DL) pour être robuste à la scène.
2. **Redressement géométrique** (homographie) pour obtenir une grille stable.
3. **Reconnaissance par case** (modèle léger + règles) pour obtenir une matrice 8×8.
4. **Vérification “règles d’échecs”** (python-chess) : un état doit être légal.

Cette “boucle de cohérence” réduit fortement les erreurs (ex: une pièce qui disparaît impossible sans capture, etc.).

### 5.4 Données & annotation (souvent le vrai facteur limitant)

Pour une approche DL (ou hybride), il faut prévoir un plan de données :

- **Corpus pilote** : vidéos captées dans des conditions proches de la cible (même angle, même échiquier) + quelques variations (lumière, caméra).
- **Vérité terrain** : idéalement le PGN fourni par l’enseignant / arbitre, sinon une annotation manuelle.
- **Annotation minimale utile** :
  - bounding box/masque de l’échiquier (pour ROI),
  - état du plateau à des timestamps clés,
  - ou directement une timeline PGN+timestamps.

Ordre de grandeur (pilotage) :

- 30 minutes vidéo = 1 800 secondes.
- Si on annote 1 fps → 1 800 frames : trop cher.
- Stratégie réaliste :
  - annote ROI + états seulement sur des **segments**,
  - capture “keyframes” autour des coups,
  - utilise un mode assisté (pré-remplissage + correction) pour réduire le coût.

## 6) Exigences fonctionnelles (MVP vs avancé)

### 6.1 MVP (objectif pilote)

- Ingestion vidéo (fichier local ou URL)
- Extraction frames + détection échiquier
- Reconstruction d’une séquence de positions (FEN) et d’un PGN approximatif
- Évaluation Stockfish de positions clés
- Export : PGN + timestamps + mini “chapitrage”

### 6.2 Avancé

- Détection de coups quasi temps réel
- Détection d’événements : roque/promotion, prise en passant
- Mode “assisté” : interface de correction (valider/corriger coups)
- Alignement audio/visuel (si le coach annonce le coup)

## 7) Architecture technique proposée (modulaire, MCP-first)

### 7.1 Principes

- Un **orchestrateur** (service “Analysis Orchestrator”) pilote l’analyse.
- Les capacités sont exposées comme des **tools MCP** via **FastMCP** (serveurs spécialisés).
- L’orchestrateur peut être appelé par l’API FastAPI existante (P13) ou par un batch.

### 7.1.1 Pourquoi MCP ici (bénéfice concret)

- **Interface stable** : l’orchestrateur appelle `vision.classify_squares(...)` quelle que soit l’implémentation (OpenCV → YOLO → ViT).
- **Déploiement flexible** : Vision peut tourner sur GPU, Stockfish sur CPU, stockage sur un service managé.
- **Audit / traçabilité** : chaque appel tool peut être loggé (inputs/outputs/latence/coût), crucial pour un système vidéo.

### 7.2 Schéma d’architecture (MCP)

```mermaid
flowchart LR
  UI[Frontend (Angular/Nginx)] -->|upload URL / fichier + paramètres| API[FastAPI API]
  API --> ORCH[Video Analysis Orchestrator]

  subgraph MCP[Tooling via MCP (FastMCP servers)]
    ING[Ingestion MCP Server\n- fetch_video\n- probe_metadata]
    VISION[Vision MCP Server\n- detect_board_roi\n- rectify_board\n- classify_squares\n- track_state]
    CHESS[Chess MCP Server\n- validate_position\n- infer_move\n- stockfish_eval]
    RAG[RAG MCP Server\n- embed\n- retrieve_opening_knowledge]
    STORE[Storage MCP Server\n- put_blob\n- get_blob\n- put_json\n- get_json]
  end

  ORCH -->|tools| ING
  ORCH -->|tools| VISION
  ORCH -->|tools| CHESS
  ORCH -->|tools| RAG
  ORCH -->|tools| STORE

  STORE --> OBJ[(Object Storage\nS3/MinIO)]
  STORE --> DB[(Metadata DB\nPostgres/SQLite)]

  ORCH --> OUT[Artifacts\nPGN + FEN timeline + highlights]
  OUT --> API
  API --> UI
```

### 7.3 Description des modules MCP

- **Ingestion MCP Server**
  - `fetch_video(source)` : récupère un fichier vidéo (ou utilise un chemin déjà local)
  - `probe_metadata(path)` : durée, fps, résolution (ffprobe)

- **Vision MCP Server**
  - `detect_board_roi(frame)` : bounding box/masque plateau
  - `rectify_board(frame, roi)` : homographie vers vue top-down
  - `classify_squares(board_img)` : renvoie matrice 8×8 de classes (vide, P/p, N/n, …)
  - `track_state(prev_state, new_obs)` : stabilise l’état dans le temps

- **Chess MCP Server**
  - `validate_position(fen)` : légalité (python-chess)
  - `infer_move(prev_fen, next_fen)` : déduit le coup probable
  - `stockfish_eval(fen)` : évaluation / top moves

- **RAG MCP Server**
  - `retrieve_opening_context(fen|pgn)` : théorie + plans

- **Storage MCP Server**
  - `put_blob/get_blob` : frames clés, miniatures
  - `put_json/get_json` : timeline, logs, résultats

Cette modularité permet :

- d’exécuter Vision sur une machine GPU, le reste sur CPU,
- de faire évoluer Vision (nouveau modèle) sans toucher l’orchestrateur.

## 8) Pipeline de traitement (batch)

1. **Ingestion** : récupérer la vidéo, calculer hash, extraire metadata.
2. **Frame sampling** : 1 fps + détection de segments “mouvement” (optionnel).
3. **Board ROI + redressement** : stabiliser une vue top-down.
4. **Reconnaissance état** : matrice 8×8 par frame (avec smoothing temporel).
5. **Déduction des coups** : comparer états successifs et inférer un coup légal.
6. **Nettoyage** : suppression doublons, correction via contraintes (ex: un coup doit être légal).
7. **Sorties** : timeline (timestamp→FEN), PGN, positions clés.
8. **Post-traitement** : Stockfish sur positions clés + RAG (théorie) + recommandations.

### 8.1 Orchestration et robustesse (files/queues)

Pour l’industrialisation, on recommande une exécution asynchrone :

- **Job queue** (ex: Redis Queue / Celery / Temporal) : soumission d’un job d’analyse.
- **Étapes idempotentes** : si la phase “rectify” échoue, on peut relancer sans réingérer la vidéo.
- **Artefacts persistés** dès que possible : frames clés, ROI, FEN intermédiaires.

Cela évite de tout recalculer lors des itérations (très utile en vision).

### 8.2 Qualité : mécanismes anti-erreurs

- **Smoothing temporel** : un état ne doit pas “clignoter” (pièce présente/absente) sans événement “mouvement”.
- **Contraintes légales** : si un coup déduit est illégal, le système doit :
  1) chercher une alternative proche (petites corrections),
  2) sinon marquer le segment “à valider” (mode assisté).
- **Score de confiance** : pour chaque coup, conserver un score et les raisons (ex: occlusion détectée).

## 9) Faisabilité : complexité et risques

### 9.1 Principaux risques techniques

- **Occlusions** (mains, pièces soulevées) : état incomplet pendant plusieurs frames.
- **Blur / compression** : pièces mal classées.
- **Perspective extrême** : cases non carrées, erreurs d’homographie.
- **Plateaux non standard** : couleurs, motifs, pièces “fantaisie”.
- **Règles** : promotions/roque mal détectés si un état manque.

### 9.2 Risques business / opérationnels

- Qualité perçue : une erreur de coup ruine la confiance.
- Coût : GPU/stockage si on analyse massivement.
- Droits : vidéos externes (YouTube) vs contenu interne.

### 9.3 Mesures de mitigation

- Standardiser le format des vidéos (angle, éclairage) pour un pilote.
- Mode “assisté” : interface de correction rapide.
- Monitoring : score de confiance par coup + détection d’anomalies.
- Tester sur un corpus représentatif avant d’annoncer un taux de succès.

### 9.4 Sécurité, conformité et gouvernance des données

Même si le projet est “tech”, la vidéo implique des risques spécifiques :

- **Données personnelles** : visages/voix (si la scène montre autre chose que l’échiquier) → minimiser, flouter, ou cadrer strictement.
- **Conservation** : définir une durée (ex: 30 jours pour brut, 6 mois pour artefacts) + purge.
- **Droits d’auteur** : préférer du contenu interne ou autorisé ; si URL externe, stocker des métadonnées plutôt que la vidéo brute.
- **Accès** : artefacts (frames) doivent être protégés (URLs signées, ACL) si vidéos privées.

## 10) Estimations de coûts (build + opex)

> Les chiffres ci-dessous sont des **ordres de grandeur** (les prix cloud évoluent). L’objectif est de donner une **fourchette réaliste**.

### 10.1 Coûts de build (personnes/temps)

Hypothèse équipe : 1 lead + 1 ML/vision + 1 backend, sur un prototype.

- Cadrage + dataset pilote + métriques : 1–2 semaines
- Prototype Vision (ROI + homographie + baseline classification) : 2–4 semaines
- Pipeline batch + stockage artefacts : 1–2 semaines
- Orchestrateur + MCP (FastMCP tools) : 1–2 semaines
- Évaluation + itérations + documentation : 2–4 semaines

Total POC : **6 à 12 semaines** (≈ 30 à 60 j.h selon profil)

Pilote (avec UI de correction + durcissement) : + **6 à 10 semaines**

### 10.2 Opex : stockage

On distingue :

- stockage vidéo brut (si conservé),
- stockage artefacts (frames clés, miniatures, timelines JSON/PGN).

Ordres de grandeur (1080p H.264, 30 min) :

- Taille vidéo : ~200–600 MB selon bitrate.
- Artefacts :
  - frames clés (ex: 200 images JPEG) : ~20–80 MB,
  - JSON/PGN : négligeable.

Exemple prod (2 000 vidéos/mois, conservation 6 mois) :

- Vidéos : 2 000 × 0,4 GB × 6 ≈ **4,8 TB**
- Artefacts : 2 000 × 0,05 GB × 6 ≈ **0,6 TB**

Formule simple (à réutiliser avec vos prix) :

$$\text{Coût stockage / mois} \approx (GB\_video + GB\_artefacts) \times \text{prix}(€/GB\cdot mois)$$

Ordre de grandeur courant (object storage) : quelques centimes €/GB·mois. Le stockage n’est généralement pas le poste #1 tant qu’on ne conserve pas “toutes les frames”.

### 10.3 Opex : traitement

Deux modes :

- **CPU batch** (moins cher, plus lent) : viable si latence non critique.
- **GPU batch** (plus cher, plus robuste/rapide si modèles lourds).

Ordre de grandeur par vidéo (30 min) :

- CPU (pipeline classique + modèle léger) : 2–10 minutes de compute.
- GPU (détection + classification) : 1–5 minutes.

Exemple pilote (200 vidéos/mois) :

- si 5 min GPU/vidéo → 1 000 min GPU/mois (~17 h) → faible, même sur une seule machine.

Exemple prod (2 000 vidéos/mois) :

- 5 min GPU/vidéo → 10 000 min (~167 h) : besoin d’auto-scaling ou d’une machine GPU dédiée.

Formules (coût de compute) :

$$\text{Heures CPU} = \frac{N\_videos \times t\_{cpu\_min}}{60}$$
$$\text{Heures GPU} = \frac{N\_videos \times t\_{gpu\_min}}{60}$$
$$\text{Coût compute / mois} \approx h\_{cpu}\times prix\_{cpu}(€/h) + h\_{gpu}\times prix\_{gpu}(€/h)$$

Table d’exemples (hypothèses réalistes, à ajuster) :

| Scénario | Volume | t/vidéo (GPU) | Heures GPU/mois | Coût GPU/mois (si 1–3 €/h) |
|---|---:|---:|---:|---:|
| POC | 50 | 5 min | ~4,2 h | ~4–13 € |
| Pilote | 200 | 5 min | ~16,7 h | ~17–50 € |
| Prod | 2 000 | 5 min | ~167 h | ~170–500 € |

Ces chiffres montrent un point important : le coût compute peut rester modéré en batch si on optimise (sampling, modèles légers). Le vrai risque de coût vient plutôt de :

- vouloir du **temps réel** (fps élevé),
- conserver des volumes massifs de données intermédiaires,
- multiplier les itérations de ré-entrainement.

### 10.4 Opex : APIs externes

- YouTube Data API : dépend du quota et du nombre de requêtes (dans ce projet, usage « recherche de ressources », pas traitement vidéo).
- Lichess explorer : gratuit mais limites et tokens possibles.

Recommandation : **cacher** les résultats et limiter les appels via un cache (Redis) pour lisser les pics.

### 10.5 Opex : exploitation

Postes souvent oubliés :

- Observabilité (logs/metrics/traces) : stockage et outil de monitoring.
- Support & maintenance : temps humain (incidents, qualité, amélioration modèle).
- MLOps : versioning modèles, validation, rollbacks.

Recommandation : démarrer simple (logs structurés + dashboards) et monter en gamme si le volume augmente.

## 11) Deux alternatives réalistes

### Alternative A — “Semi-auto” (recommandée pour un pilote)

- Vision détecte l’échiquier + propose coups avec score.
- Un humain valide/corrige les segments douteux.

Avantage : qualité perçue élevée, coûts maîtrisés, time-to-market plus court.

### Alternative B — “No-vision” (si risque trop élevé)

- On ne tente pas d’extraire les coups depuis la vidéo.
- On indexe la vidéo via :
  - script fourni par l’auteur (PGN),
  - ou saisie assistée (UI),
  - ou jeux déjà numériques (Lichess/Chess.com) → import direct.

Avantage : robustesse et coût très bas ; limite : moins “magique”.

## 12) Roadmap (étapes de développement)

1. **Semaine 0–2 : cadrage**
   - définir le corpus pilote, critères de qualité, consentements.

2. **Semaine 2–6 : POC vision**
   - ROI échiquier + homographie + classification case.

3. **Semaine 6–10 : pipeline & artefacts**
   - timeline FEN, PGN, stockage, replay.

4. **Semaine 10–16 : pilote**
   - UI correction + monitoring + optimisation.

5. **Industrialisation**
   - autoscaling, coût, observabilité, sécurité.

### 12.1 Livrables attendus par phase

- POC : 1 pipeline batch + rapport qualité + exports (PGN/timeline)
- Pilote : UI correction + monitoring + dataset & protocole d’évaluation
- Prod : SLA, sécurité, gouvernance, processus de mise à jour modèle

## 13) Recommandations finales

- Prioriser un **pilote** sur vidéos standardisées (caméra fixe, plateau visible) avant de viser les streamings.
- Concevoir le système comme un **pipeline batch** au départ (plus simple, coûts bas), puis optimiser vers temps réel si nécessaire.
- Adopter MCP/FastMCP pour isoler la complexité : Vision évolue vite, l’API produit doit rester stable.
- Prévoir dès le départ un **mode assisté** (correction) : c’est le meilleur compromis qualité/coût/risque.

## Références (sélection)

- Model Context Protocol (MCP) : https://modelcontextprotocol.io/
- FastMCP : https://gofastmcp.com/ et dépôt https://github.com/PrefectHQ/fastmcp
- OpenCV (calibration / chessboard corners) : https://docs.opencv.org/

---

## Annexe — Exemples de “tools” MCP (pseudo-spécification)

- `vision.detect_board_roi(frame_bytes) -> {bbox, confidence}`
- `vision.rectify_board(frame_bytes, bbox) -> board_image_bytes`
- `vision.classify_squares(board_image_bytes) -> {grid: 8x8, confidence_map}`
- `chess.validate_position(fen) -> {is_legal, issues[]}`
- `chess.infer_move(prev_fen, next_fen) -> {uci, san, confidence}`
- `chess.stockfish_eval(fen, depth) -> {type, value, top_moves[]}`
- `store.put_blob(bytes, mime, key) -> {url}`
- `store.put_json(obj, key) -> {url}`
