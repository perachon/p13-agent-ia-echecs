import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';

import {
  AgentResponse,
  ApiService,
  VectorSearchResponse,
  YouTubeSearchResponse,
} from './services/api.service';
import { ChessboardComponent } from './components/chessboard/chessboard.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, ChessboardComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent {
  fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

  agent: AgentResponse | null = null;
  agentError: string | null = null;
  agentLoading = false;

  searchQuery = 'défense sicilienne';
  topK = 3;
  youtubeMaxResults = 3;

  vector: VectorSearchResponse | null = null;
  youtube: YouTubeSearchResponse | null = null;
  searchError: string | null = null;
  searchLoading = false;

  constructor(public readonly api: ApiService) {}

  setStartPosition(): void {
    this.fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  }

  onFenChange(newFen: string): void {
    this.fen = newFen;
  }

  recommend(): void {
    this.agentLoading = true;
    this.agentError = null;
    this.agent = null;

    this.api.agent(this.fen).subscribe({
      next: (data) => {
        this.agent = data;
        this.agentLoading = false;
      },
      error: (err) => {
        this.agentError = err?.error?.detail ?? 'Agent request failed';
        this.agentLoading = false;
      },
    });
  }

  runSearch(): void {
    const q = this.searchQuery.trim();
    if (!q) return;

    this.searchLoading = true;
    this.searchError = null;
    this.vector = null;
    this.youtube = null;

    forkJoin({
      vector: this.api.vectorSearch(q, this.topK),
      youtube: this.api.youtubeSearch(q, this.youtubeMaxResults),
    }).subscribe({
      next: ({ vector, youtube }) => {
        this.vector = vector;
        this.youtube = youtube;
        this.searchLoading = false;
      },
      error: (err) => {
        this.searchError = err?.error?.detail ?? 'Search failed';
        this.searchLoading = false;
      },
    });
  }
}
