from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.routers.plugins import router as plugins_router
from src.plugins.loader import plugin_loader
from src.version import IOTTA_VERSION
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)


logger = logging.getLogger(__name__)

def print_banner():
    logger.info(f"""
    _       _   _        
   (_)     | | | |       
    _  ___ | |_| |_ __ _ 
   | |/ _ \\| __| __/ _` |
   | | (_) | |_| || (_| |
   |_|\\___/ \\__|\\__\\__,_|  v{IOTTA_VERSION}
""")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print_banner()
    plugin_loader.load_all()
    yield


app = FastAPI(
    title="iotta",
    description="Any device. One API.",
    version=IOTTA_VERSION,
    lifespan=lifespan,
)

app.include_router(plugins_router)

@app.get("/health")
def health():
    return {"status": "ok"}