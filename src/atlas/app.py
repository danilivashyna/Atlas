"""
Atlas β — FastAPI Application

Main application entry point with ConfigLoader integration.
Binds together: Pydantic schemas (E1.1) + FastAPI routes (E1.2) + FAB router (E1.3).

Version: 0.2.0-beta
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from atlas.api.routes import get_router
from atlas.api.schemas import ErrorResponse
from atlas.configs import ConfigLoader
from atlas.router.fab import create_fab_router


# ============================================================================
# Application Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Startup:
        - Load configs via ConfigLoader
        - Initialize FAB router
        - Load indices (HNSW/FAISS) from MANIFEST
        - Validate MANIFEST checksums
    
    Shutdown:
        - Clear config cache
        - Release resources
    
    Notes:
        - Read-only ConfigLoader (no runtime mutation)
        - FAB router is stateless (no cleanup needed)
        - Indices stored in app.state for route access
    """
    # Startup
    print("🚀 Atlas β starting...")
    
    # Load configs (cached for app lifetime)
    routes_config = ConfigLoader.get_api_routes()
    print(f"✅ Loaded {len(routes_config)} API route configs")
    
    index_configs = ConfigLoader.get_all_index_configs()
    print(f"✅ Loaded {len(index_configs)} index configs")
    
    metrics_config = ConfigLoader.get_metrics_config()
    print(f"✅ Loaded metrics config")
    
    # Initialize FAB router (stateless, no shared state)
    # RRF k parameter should come from routes.yaml in production
    fab_router = create_fab_router(rrf_k=60)
    app.state.fab_router = fab_router
    print(f"✅ Initialized FAB router (rrf_k=60)")
    
    # Load indices from MANIFEST
    app.state.indices_loaded = False
    app.state.indices = {}
    
    try:
        from pathlib import Path
        from atlas.indices import (
            HNSWIndexBuilder,
            FAISSIndexBuilder,
            load_manifest,
            verify_manifest_integrity,
        )
        
        # Check for MANIFEST
        manifest_path = Path("MANIFEST.v0_2.json")
        if not manifest_path.exists():
            print("⚠️  MANIFEST.v0_2.json not found (indices not loaded)")
            print("   To build indices: python scripts/build_indices.py")
        else:
            # Load and validate MANIFEST
            manifest = load_manifest(manifest_path)
            print(f"✅ Loaded MANIFEST: {manifest['version']}, api={manifest['api_version']}")
            
            # Verify integrity
            is_valid = verify_manifest_integrity(manifest)
            print(f"✅ MANIFEST integrity verified: {is_valid}")
            
            # Load indices
            for idx_entry in manifest["indices"]:
                level = idx_entry["level"]
                file_path = Path(idx_entry["file"])
                index_type = idx_entry["index_type"]
                
                if not file_path.exists():
                    print(f"⚠️  Index file not found: {file_path}")
                    continue
                
                # Load HNSW or FAISS index
                if index_type == "HNSW":
                    # HNSW for sentence/paragraph
                    config = index_configs.get(level)
                    builder = HNSWIndexBuilder(level=level, config=config)
                    builder.load(file_path)
                    app.state.indices[level] = builder
                    print(f"✅ Loaded {level} HNSW index: {idx_entry['num_vectors']} vectors")
                    
                elif index_type == "FAISS":
                    # FAISS for document level only
                    config = index_configs.get("document")
                    builder = FAISSIndexBuilder(config=config)
                    builder.load(file_path)
                    app.state.indices[level] = builder
                    print(f"✅ Loaded {level} FAISS index: {idx_entry['num_vectors']} vectors")
            
            # Mark as loaded if all 3 levels present
            if len(app.state.indices) == 3:
                app.state.indices_loaded = True
                print(f"✅ All indices loaded ({len(app.state.indices)} levels)")
            else:
                print(f"⚠️  Only {len(app.state.indices)}/3 indices loaded")
                
    except Exception as e:
        print(f"❌ Failed to load indices: {e}")
        print("   App will start but /search will return 501")
    
    print("✅ Atlas β ready\n")
    
    yield
    
    # Shutdown
    print("\n🛑 Atlas β shutting down...")
    ConfigLoader.clear_cache()
    app.state.indices.clear()
    print("✅ Cleared config cache and indices")


# ============================================================================
# Application Factory
# ============================================================================

def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        FastAPI app with all routes, middleware, and error handlers
    
    Configuration sources:
        - CORS: configs/api/routes.yaml (cors section)
        - Logging: configs/api/routes.yaml (logging section)
        - Timeouts: configs/api/routes.yaml (default_timeout_ms)
    """
    # Create app with lifespan
    app = FastAPI(
        title="Atlas β — Memory Engine API",
        description="Hierarchical semantic memory with multi-level search (5D + token/sent/para/doc)",
        version="0.2.0-beta",
        lifespan=lifespan,
    )
    
    # Load CORS config from routes.yaml
    routes_config = ConfigLoader.get_api_routes()
    cors_config = routes_config.get("cors", {})
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.get("allow_origins", ["*"]),
        allow_methods=cors_config.get("allow_methods", ["GET", "POST", "OPTIONS"]),
        allow_headers=cors_config.get("allow_headers", ["Content-Type", "Authorization", "X-Trace-ID"]),
        max_age=cors_config.get("max_age", 3600),
    )
    
    # Include API router
    router = get_router()
    app.include_router(router)
    
    # Register error handlers
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Convert any exception to ErrorResponse schema."""
        from datetime import datetime
        
        error_response = ErrorResponse(
            error="INTERNAL_ERROR",
            message=str(exc) if str(exc) else "An unexpected error occurred",
            details={"exception_type": type(exc).__name__},
            trace_id=request.headers.get("X-Trace-ID"),
            timestamp=datetime.utcnow()
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump()
        )
    
    return app


# ============================================================================
# Application Instance
# ============================================================================

# Create app instance (used by uvicorn)
app = create_app()


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Load logging config from routes.yaml
    routes_config = ConfigLoader.get_api_routes()
    logging_config = routes_config.get("logging", {})
    log_level = logging_config.get("level", "INFO").lower()
    
    print(f"🚀 Starting Atlas β API server...")
    print(f"📝 Log level: {log_level}")
    print(f"🔗 Docs: http://localhost:8000/docs")
    print(f"🔗 Health: http://localhost:8000/api/v1/health\n")
    
    uvicorn.run(
        "atlas.app:app",
        host="0.0.0.0",
        port=8000,
        log_level=log_level,
        reload=True,  # Development mode
    )
