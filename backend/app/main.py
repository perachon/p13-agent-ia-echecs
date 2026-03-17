from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent.graph import build_agent_graph
from app.core.config import settings
from app.rag.embeddings import embed_texts
from app.rag.milvus_service import MilvusService
from app.services.fen import validate_fen
from app.services.lichess_service import LichessService
from app.services.stockfish_service import StockfishService
from app.services.youtube_service import YouTubeService

app = FastAPI(title="FFE Chess Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_graph = build_agent_graph()


@app.get("/api/v1/healthcheck")
def healthcheck() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/moves/{fen:path}")
def get_theory_moves(fen: str) -> dict:
    try:
        validate_fen(fen)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid FEN")

    service = LichessService()
    try:
        moves = service.get_theory_moves(fen)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "fen": fen,
        "source": "lichess",
        "moves": [
            {
                "uci": m.uci,
                "san": m.san,
                "games": m.games,
                "white": m.white,
                "draws": m.draws,
                "black": m.black,
            }
            for m in moves
        ],
    }


@app.get("/api/v1/evaluate/{fen:path}")
def evaluate_position(fen: str) -> dict:
    try:
        board = validate_fen(fen)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid FEN")

    service = StockfishService()
    try:
        evaluation = service.evaluate(board)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "fen": fen,
        "source": "stockfish",
        "evaluation": {"type": evaluation.type, "value": evaluation.value},
    }


@app.get("/api/v1/agent/{fen:path}")
def agent_recommendation(fen: str) -> dict:
    """Minimal agent endpoint (LangGraph routing: Lichess -> Stockfish)."""
    try:
        result = agent_graph.invoke({"fen": fen})
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid FEN")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Agent failed: {exc}")

    moves = result.get("theory_moves") or []
    evaluation = result.get("evaluation")
    rag_results = result.get("rag_results")
    rag_error = result.get("rag_error")

    payload: dict = {"fen": fen, "source": result.get("source")}
    if result.get("lichess_error"):
        payload["lichess_error"] = result.get("lichess_error")
    if moves:
        payload["moves"] = [
            {
                "uci": m.uci,
                "san": m.san,
                "games": m.games,
                "white": m.white,
                "draws": m.draws,
                "black": m.black,
            }
            for m in moves
        ]
    if evaluation is not None:
        payload["evaluation"] = {"type": evaluation.type, "value": evaluation.value}

    # Optional enrichment from the vector DB (best-effort).
    if rag_error:
        payload["rag_error"] = rag_error
    if rag_results is not None:
        payload["rag_results"] = rag_results

    return payload


@app.get("/vector-search")
def vector_search(q: str, top_k: int = 5) -> dict:
    """Simple vector search endpoint for opening knowledge."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query is required")

    try:
        query_embedding = embed_texts([q])[0]
        service = MilvusService()
        hits = service.search(query_embedding=query_embedding, top_k=top_k)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vector search failed: {exc}")

    return {"query": q, "top_k": top_k, "results": hits}


@app.get("/api/v1/youtube/search")
def youtube_search(q: str, max_results: int = 5) -> dict:
    """Search YouTube videos related to a query (public search via API key)."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query is required")

    service = YouTubeService()
    try:
        videos = service.search_videos(query=q, max_results=max_results)
    except RuntimeError as exc:
        # configuration / upstream failures
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "query": q,
        "max_results": max_results,
        "results": [
            {
                "video_id": v.video_id,
                "title": v.title,
                "channel_title": v.channel_title,
                "published_at": v.published_at,
                "url": v.url,
                "thumbnail_url": v.thumbnail_url,
            }
            for v in videos
        ],
    }
