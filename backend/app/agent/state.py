from __future__ import annotations

from typing import NotRequired, TypedDict

from app.services.lichess_service import TheoryMove
from app.services.stockfish_service import Evaluation


class AgentState(TypedDict):
    fen: str

    theory_moves: NotRequired[list[TheoryMove]]
    evaluation: NotRequired[Evaluation]

    lichess_error: NotRequired[str]

    source: NotRequired[str]  # "lichess" | "stockfish"
