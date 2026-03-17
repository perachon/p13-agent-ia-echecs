import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';

import { Chess, Square } from 'chess.js';

type CmModule = typeof import('cm-chessboard');

@Component({
  selector: 'app-chessboard',
  standalone: true,
  templateUrl: './chessboard.component.html',
  styleUrls: ['./chessboard.component.css'],
})
export class ChessboardComponent implements AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('boardHost', { static: true }) boardHost!: ElementRef<HTMLDivElement>;

  @Input({ required: true }) fen = '';
  @Output() fenChange = new EventEmitter<string>();

  private cm: CmModule | null = null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private board: any | null = null;
  private chess: Chess | null = null;
  private moveInputHandler: ((event: any) => boolean | undefined) | null = null;
  private moveInputResetPending = false;

  private toSquare(value: unknown): Square | null {
    if (typeof value !== 'string') return null;
    const v = value.trim();
    if (!/^[a-h][1-8]$/.test(v)) return null;
    return v as Square;
  }

  async ngAfterViewInit(): Promise<void> {
    await this.initBoard();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['fen'] && !changes['fen'].firstChange) {
      void this.setFenOnBoard(String(changes['fen'].currentValue ?? ''));
    }
  }

  ngOnDestroy(): void {
    try {
      this.board?.disableMoveInput();
    } catch {
      // ignore
    }

    try {
      this.board?.destroy?.();
    } catch {
      // ignore
    }
    this.board = null;
    this.chess = null;
    this.moveInputHandler = null;
  }

  private scheduleMoveInputReset(): void {
    if (this.moveInputResetPending) return;
    if (!this.board || !this.moveInputHandler) return;
    this.moveInputResetPending = true;

    // Reset on next tick to avoid interfering with the current cm-chessboard callback.
    setTimeout(() => {
      try {
        this.board?.disableMoveInput();
      } catch {
        // ignore
      }

      try {
        this.board?.enableMoveInput(this.moveInputHandler);
      } catch {
        // ignore
      }

      this.moveInputResetPending = false;
    }, 0);
  }

  private async initBoard(): Promise<void> {
    this.cm = await import('cm-chessboard');
    const cm = this.cm;
    const fen = this.fen?.trim() ? this.fen.trim() : cm.FEN.start;

    this.chess = new Chess();
    try {
      this.chess.load(fen);
    } catch {
      this.chess.load(cm.FEN.start);
    }

    this.board = new cm.Chessboard(this.boardHost.nativeElement, {
      position: this.chess.fen(),
      assetsUrl: 'assets/cm-chessboard/',
      style: {
        cssClass: 'default',
        showCoordinates: true,
      },
    });

    this.moveInputHandler = (event: any) => {
      if (!this.chess || !this.cm) return false;
      const cm = this.cm;

      if (event.type === cm.INPUT_EVENT_TYPE.moveInputStarted) {
        const from = this.toSquare(event.squareFrom);
        if (!from) return false;

        const piece = this.chess.get(from);
        if (!piece) return false;

        // Enforce side-to-move.
        if (piece.color !== this.chess.turn()) return false;

        return true;
      }

      if (event.type === cm.INPUT_EVENT_TYPE.validateMoveInput) {
        const from = this.toSquare(event.squareFrom);
        const to = this.toSquare(event.squareTo);
        if (!from || !to) return false;

        const movingPiece = this.chess.get(from);
        const isPawn = movingPiece?.type === 'p';
        const toRank = to.slice(1, 2);
        const needsPromotion = isPawn && (toRank === '1' || toRank === '8');

        // Validate without mutating game state.
        const testMove = this.chess.move(
          { from, to, promotion: needsPromotion ? 'q' : undefined } as any
        );
        if (!testMove) return false;
        this.chess.undo();
        return true;
      }

      if (event.type === cm.INPUT_EVENT_TYPE.moveInputFinished) {
        const from = this.toSquare(event.squareFrom);
        const to = this.toSquare(event.squareTo);
        const legalMove = Boolean(event.legalMove);

        if (legalMove && from && to) {
          const movingPiece = this.chess.get(from);
          const isPawn = movingPiece?.type === 'p';
          const toRank = to.slice(1, 2);
          const needsPromotion = isPawn && (toRank === '1' || toRank === '8');
          this.chess.move({ from, to, promotion: needsPromotion ? 'q' : undefined } as any);
        }

        const currentFen = this.chess.fen();
        void this.board?.setPosition(currentFen, true);
        this.fenChange.emit(currentFen);

        // Rare edge case: quick interactions can leave the internal input state stuck.
        this.scheduleMoveInputReset();
      }

      if (event.type === cm.INPUT_EVENT_TYPE.moveInputCanceled) {
        // Always restore board from chess.js state (source of truth).
        const currentFen = this.chess.fen();
        void this.board?.setPosition(currentFen, true);
        this.scheduleMoveInputReset();
      }

      return undefined;
    };

    this.board.enableMoveInput(this.moveInputHandler);

    // Emit initial canonical FEN
    this.fenChange.emit(this.chess.fen());
  }

  private async setFenOnBoard(fen: string): Promise<void> {
    if (!this.board || !this.chess) return;

    const trimmed = fen.trim();
    if (!trimmed) return;

    try {
      this.chess.load(trimmed);
      await this.board.setPosition(this.chess.fen(), true);
    } catch {
      // ignore invalid fen
    }
  }
}
