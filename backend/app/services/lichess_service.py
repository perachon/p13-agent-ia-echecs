from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class TheoryMove:
    uci: str
    san: str | None
    games: int
    white: int | None = None
    draws: int | None = None
    black: int | None = None


class LichessService:
    def __init__(self) -> None:
        self._timeout = httpx.Timeout(settings.http_timeout_seconds)

    def get_theory_moves(self, fen: str) -> list[TheoryMove]:
        """Return theory moves from Lichess opening explorer.

        Uses https://explorer.lichess.org/{db}?fen=...
        """
        url = f"{settings.lichess_explorer_base_url.rstrip('/')}/{settings.lichess_explorer_db}"

        headers: dict[str, str] = {}
        if settings.lichess_token:
            headers["Authorization"] = f"Bearer {settings.lichess_token}"

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(url, params={"fen": fen}, headers=headers)
                resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RuntimeError("Lichess request timed out") from exc
        except httpx.HTTPStatusError as exc:
            # common: 400 invalid fen, 429 rate limit
            status = exc.response.status_code
            if status == 401:
                raise RuntimeError(
                    "Lichess authorization required (set LICHESS_TOKEN)"
                ) from exc
            raise RuntimeError(f"Lichess request failed: {status}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError("Lichess request failed") from exc

        data: dict[str, Any] = resp.json()
        moves: list[TheoryMove] = []
        for m in data.get("moves", []) or []:
            uci = m.get("uci")
            if not uci:
                continue
            white = m.get("white")
            draws = m.get("draws")
            black = m.get("black")
            games = 0
            for v in (white, draws, black):
                if isinstance(v, int):
                    games += v

            moves.append(
                TheoryMove(
                    uci=uci,
                    san=m.get("san"),
                    games=games,
                    white=white if isinstance(white, int) else None,
                    draws=draws if isinstance(draws, int) else None,
                    black=black if isinstance(black, int) else None,
                )
            )

        # Most relevant first
        moves.sort(key=lambda x: x.games, reverse=True)
        return moves
