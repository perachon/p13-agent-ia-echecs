import chess


def validate_fen(fen: str) -> chess.Board:
    """Parse and validate a FEN string.

    Raises:
        ValueError: If the FEN is invalid.
    """
    try:
        board = chess.Board(fen)
    except Exception as exc:  # pragma: no cover
        raise ValueError("Invalid FEN") from exc

    if board.is_variant_end():
        # Still a valid board; keep it allowed.
        return board

    return board
