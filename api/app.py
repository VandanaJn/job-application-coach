from fastapi import FastAPI
from api.routes.user import router as user_router
from api.routes.jobs import router as jobs_router
from api.routes.sessions import router as sessions_router

app = FastAPI(title="Job Application Coach API")
app.include_router(user_router)
app.include_router(jobs_router)
app.include_router(sessions_router)
