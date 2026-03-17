from __future__ import annotations

import chess
from langgraph.graph import END, StateGraph

from app.agent.state import AgentState
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
    graph.add_edge("end_with_lichess", END)
    graph.add_edge("evaluate_stockfish", END)

    return graph.compile()
