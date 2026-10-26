from fastapi import FastAPI

from app.routes import router as designs_router


app = FastAPI(title="Design Registry API", version="1.0.0")
app.include_router(designs_router)