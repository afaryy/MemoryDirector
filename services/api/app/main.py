from fastapi import FastAPI

app = FastAPI(title="Memory Director API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
