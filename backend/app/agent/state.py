from __future__ import annotations

from typing import NotRequired, TypedDict

from app.services.lichess_service import TheoryMove
from app.services.stockfish_service import Evaluation


class RagHit(TypedDict):
    score: float
    source: str | None
    title: str | None
    text: str | None


class AgentState(TypedDict):
    fen: str

    theory_moves: NotRequired[list[TheoryMove]]
    evaluation: NotRequired[Evaluation]

    lichess_error: NotRequired[str]

    rag_results: NotRequired[list[RagHit]]
    rag_error: NotRequired[str]

    source: NotRequired[str]  # "lichess" | "stockfish"
