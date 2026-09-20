from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config  # noqa: F401  (bootstraps sys.path + .env)
from app.services import model_service, rootcause_service, telemetry_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_service.load()
    rootcause_service.load()
    telemetry_service.load()
    yield


app = FastAPI(title="E-IDSS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import economics, health, inspect, line, metrics, rootcause, telemetry  # noqa: E402

app.include_router(health.router)
app.include_router(inspect.router)
app.include_router(metrics.router)
app.include_router(rootcause.router)
app.include_router(line.router)
app.include_router(economics.router)
app.include_router(telemetry.router)
