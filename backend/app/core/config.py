from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    http_timeout_seconds: float = 8.0

    # Lichess opening explorer (public)
    lichess_explorer_base_url: str = "https://explorer.lichess.org"
    lichess_explorer_db: str = "lichess"  # lichess | masters | player
    lichess_token: str | None = None

    # Stockfish
    stockfish_path: str = "/usr/games/stockfish"
    stockfish_depth: int = 14

    # Milvus
    milvus_host: str = "milvus"
    milvus_port: int = 19530
    milvus_collection: str = "openings"

    # Embeddings
    # Default chosen for lightweight CPU embeddings (no PyTorch/CUDA in Docker)
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"

    # YouTube Data API v3 (Step 4)
    youtube_api_key: str | None = None
    youtube_region_code: str = "FR"
    youtube_relevance_language: str = "fr"

    # CORS (for Angular dev server)
    cors_allow_origins: str = "http://localhost:4200,http://127.0.0.1:4200"

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


settings = Settings()
