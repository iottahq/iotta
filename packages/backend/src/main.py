from contextlib import asynccontextmanager

from fastapi import FastAPI
from src.database import Base, engine
from src.device_manager import init_device_manager
from src.logging import get_logger, setup_logging
from src.models import credential, device
from src.plugins.loader import plugin_loader
from src.routers.credentials import router as credentials_router
from src.routers.devices import router as devices_router
from src.routers.plugins import router as plugins_router
from src.version import IOTTA_VERSION

setup_logging()

logger = get_logger("core")


def print_banner():
    logger.info(f"""
    _       _   _
   (_)     | | | |
    _  ___ | |_| |_ __ _
   | |/ _ \| __| __/ _` |
   | | (_) | |_| || (_| |
   |_|\___/ \__|\__\__,_|  v{IOTTA_VERSION}
""")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    print_banner()
    plugin_loader.load_all()
    manager = init_device_manager(app)
    await manager.mount_all()
    yield


app = FastAPI(
    title="iotta",
    description="Any device. One API.",
    version=IOTTA_VERSION,
    lifespan=lifespan,
)

app.include_router(plugins_router)
app.include_router(credentials_router)
app.include_router(devices_router)


@app.get("/health")
def health():
    return {"status": "ok"}
