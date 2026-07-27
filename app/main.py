from fastapi import FastAPI

app = FastAPI(
    title="GW2 Companion",
    description="A self-hosted Guild Wars 2 companion.",
    version="0.1.0"
)

@app.get("/")
def root():
    return {
        "application": "GW2 Companion",
        "version": "0.1.0",
        "status": "Running"
    }