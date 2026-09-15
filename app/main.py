from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Neuro-Psychiatry Research Assistant")
app.include_router(router)
