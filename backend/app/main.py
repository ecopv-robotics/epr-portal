from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, apply_compatible_schema_updates, engine
from app.modules.application.router import router as application_router
from app.modules.admin.router import router as admin_router
from app.modules.company.router import router as company_router
from app.modules.material.router import router as material_router
from app.modules.product.router import router as product_router
from app.modules.store.router import router as store_router
from app.modules.template.router import router as template_router
from app.modules.user.router import router as user_router
from app.seed import seed_demo_user, seed_service_catalog


@asynccontextmanager
async def lifespan(_: FastAPI):
    apply_compatible_schema_updates()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_user(db)
        seed_service_catalog(db)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(user_router, prefix=settings.api_prefix)
app.include_router(application_router, prefix=settings.api_prefix)
app.include_router(template_router, prefix=settings.api_prefix)
app.include_router(company_router, prefix=settings.api_prefix)
app.include_router(store_router, prefix=settings.api_prefix)
app.include_router(product_router, prefix=settings.api_prefix)
app.include_router(material_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.mount("/files", StaticFiles(directory=settings.storage_path, check_dir=False), name="files")


@app.get("/health")
def health():
    return {"status": "ok"}
