from fastapi import FastAPI

app = FastAPI(title="FFE Chess Agent API", version="0.1.0")


@app.get("/api/v1/healthcheck")
def healthcheck() -> dict:
    return {"status": "ok"}
