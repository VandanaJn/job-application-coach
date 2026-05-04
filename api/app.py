from fastapi import FastAPI
from api.routes.sessions import router as sessions_router

app = FastAPI(title="Job Application Coach API")
app.include_router(sessions_router)
