import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.auth import get_current_user, require_auth
from src.crypto import check_secret_key_configured
from src.device_manager import init_device_manager
from src.logging import get_logger, setup_logging
from src.models.user import User
from src.plugins.loader import plugin_loader
from src.routers.auth import UserRead
from src.routers.auth import router as auth_router
from src.routers.credentials import router as credentials_router
from src.routers.devices import router as devices_router
from src.routers.groups import router as groups_router
from src.routers.plugin_editor import router as plugin_editor_router
from src.routers.plugin_registry import router as plugin_registry_router
from src.routers.plugins import router as plugins_router
from src.routers.tokens import router as tokens_router
from src.version import IOTTA_VERSION

BASE_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_INI = BASE_DIR / "alembic.ini"
ALEMBIC_DIR = BASE_DIR / "alembic"

setup_logging()
logger = get_logger("core")


def run_migrations():
    for name in ("alembic", "alembic.runtime.migration", "sqlalchemy", "root"):
        log = logging.getLogger(name)
        log.setLevel(logging.CRITICAL)
        log.propagate = False
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(str(ALEMBIC_INI))
    alembic_cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    alembic_cfg.set_section_option("logger_alembic", "level", "CRITICAL")
    alembic_cfg.set_section_option("logger_sqlalchemy", "level", "CRITICAL")
    alembic_cfg.set_section_option("logger_root", "level", "CRITICAL")
    command.upgrade(alembic_cfg, "head")
    setup_logging()


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
    check_secret_key_configured()
    logger.info("Running database migrations...")
    run_migrations()
    logger.info("Migrations complete")
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
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://0.0.0.0:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# All auth routes (setup, login, me) live in auth_router
app.include_router(auth_router)

# Protected routers
app.include_router(groups_router, dependencies=[Depends(require_auth)])
app.include_router(tokens_router, dependencies=[Depends(require_auth)])
app.include_router(plugins_router, dependencies=[Depends(require_auth)])
app.include_router(plugin_editor_router, dependencies=[Depends(require_auth)])
app.include_router(plugin_registry_router, dependencies=[Depends(require_auth)])
app.include_router(credentials_router, dependencies=[Depends(require_auth)])
app.include_router(devices_router, dependencies=[Depends(require_auth)])


@app.get("/health")
def health():
    return {"status": "ok"}
