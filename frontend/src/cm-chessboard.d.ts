declare module 'cm-chessboard' {
  export const FEN: {
    start: string;
  };

  export const INPUT_EVENT_TYPE: {
    moveInputStarted: string;
    movingOverSquare: string;
    validateMoveInput: string;
    moveInputFinished: string;
    moveInputCanceled: string;
  };

  export type MoveInputEvent = {
    type: string;
    squareFrom?: string;
    squareTo?: string;
  };

  export type ChessboardConfig = {
    position?: string;
    assetsUrl?: string;
    style?: {
      cssClass?: string;
      showCoordinates?: boolean;
    };
  };

  // cm-chessboard is a JS library; this is a minimal typing surface for our usage.
  export class Chessboard {
    constructor(element: HTMLElement, config?: ChessboardConfig);
    enableMoveInput(
      handler: (event: MoveInputEvent) => boolean | undefined,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      context?: any
    ): void;
    disableMoveInput(): void;
    setPosition(fen: string, animated?: boolean): Promise<void> | void;
    getPosition(): string;
  }
}
