from __future__ import annotations

from dataclasses import dataclass

import chess
import chess.engine

from app.core.config import settings


@dataclass(frozen=True)
class Evaluation:
    type: str  # "cp" | "mate"
    value: int


class StockfishService:
    def evaluate(self, board: chess.Board) -> Evaluation:
        """Evaluate a position using Stockfish.

        Returns centipawns (cp) from the side-to-move perspective when possible,
        otherwise a mate score.
        """
        limit = chess.engine.Limit(depth=settings.stockfish_depth)

        try:
            with chess.engine.SimpleEngine.popen_uci(settings.stockfish_path) as engine:
                info = engine.analyse(board, limit)
        except FileNotFoundError as exc:
            raise RuntimeError("Stockfish binary not found") from exc
        except chess.engine.EngineTerminatedError as exc:
            raise RuntimeError("Stockfish terminated unexpectedly") from exc
        except chess.engine.EngineError as exc:
            raise RuntimeError("Stockfish engine error") from exc

        score = info["score"].pov(board.turn)
        mate = score.mate()
        if mate is not None:
            return Evaluation(type="mate", value=int(mate))

        cp = score.score(mate_score=100000)
        return Evaluation(type="cp", value=int(cp if cp is not None else 0))
