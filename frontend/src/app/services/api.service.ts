import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export type TheoryMove = {
  uci: string;
  san?: string | null;
  games: number;
  white?: number | null;
  draws?: number | null;
  black?: number | null;
};

export type Evaluation = { type: 'cp' | 'mate'; value: number };

export type AgentResponse = {
  fen: string;
  source?: 'lichess' | 'stockfish' | string;
  lichess_error?: string;
  moves?: TheoryMove[];
  evaluation?: Evaluation;
};

export type VectorHit = { score: number; source: string; title: string; text: string };
export type VectorSearchResponse = { query: string; top_k: number; results: VectorHit[] };

export type YouTubeVideo = {
  video_id: string;
  title: string;
  channel_title?: string | null;
  published_at?: string | null;
  url: string;
  thumbnail_url?: string | null;
};
export type YouTubeSearchResponse = { query: string; max_results: number; results: YouTubeVideo[] };

@Injectable({ providedIn: 'root' })
export class ApiService {
  // In dev, FastAPI runs on :8000.
  readonly baseUrl = 'http://localhost:8000';

  constructor(private readonly http: HttpClient) {}

  agent(fen: string): Observable<AgentResponse> {
    const encodedFen = encodeURIComponent(fen);
    return this.http.get<AgentResponse>(`${this.baseUrl}/api/v1/agent/${encodedFen}`);
  }

  vectorSearch(query: string, topK: number): Observable<VectorSearchResponse> {
    const params = new URLSearchParams({ q: query, top_k: String(topK) });
    return this.http.get<VectorSearchResponse>(`${this.baseUrl}/vector-search?${params.toString()}`);
  }

  youtubeSearch(query: string, maxResults: number): Observable<YouTubeSearchResponse> {
    const params = new URLSearchParams({ q: query, max_results: String(maxResults) });
    return this.http.get<YouTubeSearchResponse>(`${this.baseUrl}/api/v1/youtube/search?${params.toString()}`);
  }
}
