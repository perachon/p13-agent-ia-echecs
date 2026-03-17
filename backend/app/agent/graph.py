from __future__ import annotations

import chess
from langgraph.graph import END, StateGraph

from app.agent.state import AgentState
from app.rag.embeddings import embed_texts
from app.rag.milvus_service import MilvusService
from app.services.fen import validate_fen
from app.services.lichess_service import LichessService
from app.services.stockfish_service import StockfishService


def _validate_fen_node(state: AgentState) -> AgentState:
    validate_fen(state["fen"])  # raises ValueError
    return state


def _fetch_theory_moves_node(state: AgentState) -> AgentState:
    service = LichessService()
    try:
        moves = service.get_theory_moves(state["fen"])
        return {**state, "theory_moves": moves}
    except RuntimeError as exc:
        return {**state, "theory_moves": [], "lichess_error": str(exc)}


def _route_after_lichess(state: AgentState) -> str:
    moves = state.get("theory_moves") or []
    if len(moves) > 0:
        return "end_with_lichess"
    return "evaluate_stockfish"


def _end_with_lichess_node(state: AgentState) -> AgentState:
    return {**state, "source": "lichess"}


def _retrieve_rag_node(state: AgentState) -> AgentState:
    """Retrieve opening context from Milvus (best-effort).

    Note: FEN alone is not ideal text for retrieval; we still connect RAG into the
    workflow to enrich responses when the knowledge base contains relevant docs.
    """

    fen = state.get("fen", "")
    if not isinstance(fen, str) or not fen.strip():
        return {**state, "rag_results": [], "rag_error": "Missing FEN"}

    # Build a simple French query (FR-first) to match our sample knowledge.
    # If we have theory moves, include top SAN/uci to give the retriever more signal.
    moves = state.get("theory_moves") or []
    top_moves = ", ".join(
        [
            (m.san or m.uci)
            for m in (moves[:5] if isinstance(moves, list) else [])
            if getattr(m, "uci", None)
        ]
    )

    query_parts = [
        "ouverture échecs plans et repères",
        f"FEN: {fen}",
    ]
    if top_moves:
        query_parts.append(f"coups théoriques: {top_moves}")

    query = " | ".join(query_parts)

    try:
        query_embedding = embed_texts([query])[0]
        service = MilvusService()
        hits = service.search(query_embedding=query_embedding, top_k=5)
        return {**state, "rag_results": hits}
    except Exception as exc:
        return {**state, "rag_results": [], "rag_error": str(exc)}


def _evaluate_stockfish_node(state: AgentState) -> AgentState:
    board: chess.Board = validate_fen(state["fen"])
    service = StockfishService()
    evaluation = service.evaluate(board)
    return {**state, "evaluation": evaluation, "source": "stockfish"}


def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("validate_fen", _validate_fen_node)
    graph.add_node("fetch_lichess", _fetch_theory_moves_node)
    graph.add_node("end_with_lichess", _end_with_lichess_node)
    graph.add_node("evaluate_stockfish", _evaluate_stockfish_node)
    graph.add_node("retrieve_rag", _retrieve_rag_node)

    graph.set_entry_point("validate_fen")
    graph.add_edge("validate_fen", "fetch_lichess")
    graph.add_conditional_edges(
        "fetch_lichess",
        _route_after_lichess,
        {
            "end_with_lichess": "end_with_lichess",
            "evaluate_stockfish": "evaluate_stockfish",
        },
    )
    # Finalize through RAG retrieval for both paths.
    graph.add_edge("evaluate_stockfish", "retrieve_rag")
    graph.add_edge("retrieve_rag", END)

    # If we ended with lichess (theory moves found), also enrich with RAG.
    graph.add_edge("end_with_lichess", "retrieve_rag")

    return graph.compile()
