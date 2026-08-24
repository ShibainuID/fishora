from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.contracts import ImageValidationError
from apps.main_api.api.buyers import router as buyers_router
from apps.main_api.api.fish import knowledge_router, router as fish_router
from apps.main_api.api.lots import router as lots_router
from apps.main_api.config import DEFAULT_CORS_ALLOW_ORIGINS, MainSettings, parse_origins
from apps.main_api.db.lot_repository import SqlLandingPointRepository, SqlLotRepository
from apps.main_api.db.preference_repository import SqlPreferenceRepository
from apps.main_api.db.repositories import SqlKnowledgeRepository
from apps.main_api.db.session import session_factory
from apps.main_api.db.sql_repositories import SqlPredictionRepository, SqlSpeciesRepository
from apps.main_api.errors import (
    BidOutbid,
    CvUnavailable,
    InvalidGeneratedKnowledge,
    InvalidLot,
    LotClosed,
    LotNotAllocatable,
    LotNotFound,
    OpenCodeUnavailable,
    PredictionNotFound,
    PredictionNotVerified,
    UnsupportedCvLabel,
    UnsupportedSpecies,
)
from apps.main_api.ports import AppDependencies
from apps.main_api.services.cv_client import HttpCVClient
from apps.main_api.services.embeddings import LocalE5Embedder
from apps.main_api.services.generation import KnowledgeGenerator, OpenCodeGoClient
from apps.main_api.services.image_store import FilesystemImageStore
from apps.main_api.services.retrieval import VerifiedRetriever


def create_main_app(settings: MainSettings | None = None, deps: AppDependencies | None = None) -> FastAPI:
    """Main API factory.

    Tests inject every external port through `deps`; the production factory
    leaves them None and wires the SQLAlchemy repositories, HTTP CV client,
    and filesystem image store lazily in the lifespan, so importing this
    module never connects to Postgres or any network service. Settings and
    production ports are instantiated only when actually missing: a complete
    fake bundle (all five ports injected) never constructs MainSettings, never
    reads environment variables, and never creates a DB session factory.
    """
    deps = deps or AppDependencies()
    app = FastAPI(lifespan=_lifespan)
    app.state.settings = settings  # may be None when all ports are injected
    app.state.deps = deps
    _register_cors(app, settings)
    _register_error_handlers(app)
    app.include_router(fish_router)
    app.include_router(knowledge_router)
    app.include_router(lots_router)
    app.include_router(buyers_router)
    return app


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _ensure_production_deps(app)
    yield


def _ensure_production_deps(app: FastAPI) -> None:
    """Fill any un-injected port with the production implementation (idempotent).

    The five concrete ports are the completeness criterion: when cv_client,
    species_repo, prediction_repo, image_store, and embedder are all injected,
    nothing is missing. A session factory is only a means to build the SQL
    repos, not an end port, so a complete fake bundle never constructs
    MainSettings, a DB session factory, a network client, or an embedder —
    even when the lifespan runs. The production embedder is constructed
    without loading weights: LocalE5Embedder stays lazy until first embed.
    """
    deps = app.state.deps
    complete = (
        deps.cv_client is not None
        and deps.species_repo is not None
        and deps.prediction_repo is not None
        and deps.image_store is not None
        and deps.embedder is not None
    )
    if complete:
        return
    settings = app.state.settings or MainSettings()
    # Stored so routes read configured values, not the class defaults.
    app.state.settings = settings
    if deps.session_factory is None:
        deps.session_factory = session_factory(settings)
    if deps.cv_client is None:
        deps.cv_client = HttpCVClient(settings.cv_service_url, settings.cv_timeout_seconds)
    if deps.species_repo is None:
        deps.species_repo = SqlSpeciesRepository(deps.session_factory)
    if deps.prediction_repo is None:
        deps.prediction_repo = SqlPredictionRepository(deps.session_factory)
    if deps.image_store is None:
        deps.image_store = FilesystemImageStore(settings.image_storage_dir)
    if deps.embedder is None:
        deps.embedder = LocalE5Embedder(
            settings.embedding_model_name,
            device=settings.embedding_device,
        )
    if deps.knowledge_repo is None:
        deps.knowledge_repo = SqlKnowledgeRepository(deps.session_factory)
    if deps.lot_repo is None:
        deps.lot_repo = SqlLotRepository(deps.session_factory)
    if deps.landing_point_repo is None:
        deps.landing_point_repo = SqlLandingPointRepository(deps.session_factory)
    if deps.preference_repo is None:
        deps.preference_repo = SqlPreferenceRepository(deps.session_factory)
    if deps.retriever is None:
        deps.retriever = VerifiedRetriever(deps.knowledge_repo, deps.embedder)
    if deps.generator is None:
        # Lazy: a blank OPENCODE_GO_API_KEY must not break startup.
        deps.generator = KnowledgeGenerator(lambda: OpenCodeGoClient(settings))


def _register_cors(app: FastAPI, settings: MainSettings | None) -> None:
    """Allow the frontend's origin to reach this API from a browser."""
    origins = (
        settings.cors_origins
        if settings is not None
        else parse_origins(DEFAULT_CORS_ALLOW_ORIGINS)
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["content-type", "authorization"],
    )


def _register_error_handlers(app: FastAPI) -> None:
    # Fixed generic details only: never echo an internal CV URL, credentials, or headers.
    @app.exception_handler(ImageValidationError)
    async def _image_validation(request: Request, exc: ImageValidationError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(CvUnavailable)
    async def _cv_unavailable(request: Request, exc: CvUnavailable):
        return JSONResponse(status_code=503, content={"detail": "fish identification service is temporarily unavailable"})

    @app.exception_handler(PredictionNotFound)
    async def _prediction_not_found(request: Request, exc: PredictionNotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(UnsupportedSpecies)
    async def _unsupported_species(request: Request, exc: UnsupportedSpecies):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(UnsupportedCvLabel)
    async def _unsupported_cv_label(request: Request, exc: UnsupportedCvLabel):
        return JSONResponse(status_code=502, content={"detail": "cv returned an unsupported species label"})

    @app.exception_handler(PredictionNotVerified)
    async def _prediction_not_verified(request: Request, exc: PredictionNotVerified):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(OpenCodeUnavailable)
    async def _opencode_unavailable(request: Request, exc: OpenCodeUnavailable):
        # Generic detail plus chunk ids only, never credentials or internal URLs.
        return JSONResponse(status_code=502, content={
            "detail": "knowledge generation is temporarily unavailable",
            "retrieved_chunk_ids": exc.retrieved_chunk_ids,
        })

    @app.exception_handler(InvalidGeneratedKnowledge)
    async def _invalid_generated_knowledge(request: Request, exc: InvalidGeneratedKnowledge):
        return JSONResponse(status_code=502, content={
            "detail": "generated knowledge failed validation",
            "retrieved_chunk_ids": exc.retrieved_chunk_ids,
        })

    @app.exception_handler(InvalidLot)
    async def _invalid_lot(request: Request, exc: InvalidLot):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(LotNotFound)
    async def _lot_not_found(request: Request, exc: LotNotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(LotClosed)
    async def _lot_closed(request: Request, exc: LotClosed):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(BidOutbid)
    async def _bid_outbid(request: Request, exc: BidOutbid):
        return JSONResponse(status_code=409, content={
            "detail": "bid must exceed current highest",
            "current_highest_per_kg": str(exc.current_highest_per_kg),
        })

    @app.exception_handler(LotNotAllocatable)
    async def _lot_not_allocatable(request: Request, exc: LotNotAllocatable):
        return JSONResponse(status_code=409, content={"detail": str(exc)})


_app: FastAPI | None = None


def __getattr__(name: str):
    # Lazy module-level app: importing never needs env vars or a database.
    if name == "app":
        global _app
        if _app is None:
            _app = create_main_app()
        return _app
    raise AttributeError(name)
