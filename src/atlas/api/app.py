# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Atlas FastAPI Application

REST API for semantic space operations with encode, decode, and explain endpoints.
"""

import time
import logging
import uuid
from contextlib import asynccontextmanager
from importlib.metadata import version as pkg_version

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import numpy as np

from atlas import SemanticSpace
from atlas.dimensions import DimensionMapper, SemanticDimension
from atlas.decoders import InterpretableDecoder
from atlas.hierarchical import (
    HierarchicalEncoder,
    HierarchicalDecoder,
    EncodeHierarchicalRequest,
    EncodeHierarchicalResponse,
    DecodeHierarchicalRequest,
    DecodeHierarchicalResponse,
    ManipulateHierarchicalRequest,
    ManipulateHierarchicalResponse,
)
from .models import (
    EncodeRequest,
    EncodeResponse,
    DecodeRequest,
    DecodeResponse,
    DimensionReasoning,
    ExplainRequest,
    ExplainResponse,
    DimensionExplanation,
    ErrorResponse,
    HealthResponse,
    MetricsResponse,
)

# Configure logging (no raw text logging per security policy)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get package version
try:
    APP_VERSION = pkg_version("atlas")
except Exception:
    APP_VERSION = "0.2.0a1"

# Global state
semantic_space = None
interpretable_decoder = None
hierarchical_encoder = None
hierarchical_decoder = None
metrics = {"requests_total": 0, "requests_by_endpoint": {}, "latencies": {}, "errors_total": 0}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup/shutdown"""
    global semantic_space, interpretable_decoder, hierarchical_encoder, hierarchical_decoder

    # Startup
    logger.info("Initializing Atlas Semantic Space...")
    try:
        semantic_space = SemanticSpace()
        interpretable_decoder = InterpretableDecoder()
        hierarchical_encoder = HierarchicalEncoder()
        hierarchical_decoder = HierarchicalDecoder()
        logger.info("Atlas Semantic Space initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Semantic Space: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Atlas API...")


# Create FastAPI app
app = FastAPI(
    title="Atlas Semantic Space API",
    description="5D semantic space interface for encoding, decoding, and explaining text",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware (configure appropriately for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (favicon, etc.)
try:
    import os

    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
except Exception as e:
    pass  # Static files optional


# Middleware for request tracking
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track request metrics without logging sensitive data"""
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id

    # Log metadata only (no user data)
    logger.info(f"Request {trace_id}: {request.method} {request.url.path}")

    start_time = time.time()

    try:
        response = await call_next(request)
        latency_ms = (time.time() - start_time) * 1000

        # Update metrics
        metrics["requests_total"] += 1
        endpoint = request.url.path
        metrics["requests_by_endpoint"][endpoint] = (
            metrics["requests_by_endpoint"].get(endpoint, 0) + 1
        )

        if endpoint not in metrics["latencies"]:
            metrics["latencies"][endpoint] = []
        metrics["latencies"][endpoint].append(latency_ms)

        logger.info(f"Request {trace_id} completed in {latency_ms:.2f}ms")

        return response

    except Exception as e:
        metrics["errors_total"] += 1
        logger.error(f"Request {trace_id} failed: {str(e)}")
        raise


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all exceptions with proper error responses"""
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    # Determine error type
    error_type = type(exc).__name__
    message = str(exc)

    # Log error (but not user data)
    logger.error(f"Error {trace_id}: {error_type} - {message}")

    # Create error response
    error_response = ErrorResponse(
        error_type=error_type,
        message=message,
        trace_id=trace_id,
        debug_info={"endpoint": request.url.path, "method": request.method},
    )

    # Determine HTTP status code
    if isinstance(exc, ValueError):
        status_code = 400
    elif isinstance(exc, HTTPException):
        status_code = exc.status_code
    else:
        status_code = 500

    return JSONResponse(status_code=status_code, content=error_response.model_dump())


# Health check endpoints
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(
        status="ok" if semantic_space is not None else "not_ready",
        version=APP_VERSION,
        model_loaded=semantic_space is not None,
    )


@app.get("/ready", response_model=HealthResponse, tags=["Health"])
async def readiness_check():
    """Readiness probe - checks if model is loaded"""
    if semantic_space is None:
        raise HTTPException(status_code=503, detail="Semantic space not initialized")

    return HealthResponse(status="ready", version=APP_VERSION, model_loaded=True)


@app.get("/metrics", response_model=MetricsResponse, tags=["Health"])
async def get_metrics():
    """Prometheus-compatible metrics endpoint"""
    # Calculate average latencies
    avg_latency = {}
    for endpoint, latencies in metrics["latencies"].items():
        if latencies:
            avg_latency[endpoint] = sum(latencies) / len(latencies)

    return MetricsResponse(
        requests_total=metrics["requests_total"],
        requests_by_endpoint=metrics["requests_by_endpoint"],
        avg_latency_ms=avg_latency,
        errors_total=metrics["errors_total"],
    )


# Main API endpoints
@app.post("/encode", response_model=EncodeResponse, tags=["Semantic Operations"])
async def encode_text(request: EncodeRequest, req: Request) -> EncodeResponse:
    """
    Encode text into 5D semantic space.

    This endpoint converts input text into a 5-dimensional vector representation
    where each dimension captures a distinct semantic property.

    **Security**: Raw text is not logged, only metadata.
    """
    trace_id = getattr(req.state, "trace_id", str(uuid.uuid4()))

    try:
        # Encode (we don't log the text)
        logger.info(f"Encoding text (trace_id={trace_id}, length={len(request.text)})")

        vector = semantic_space.encode(request.text)

        return EncodeResponse(vector=vector.tolist(), norm=True, trace_id=trace_id)

    except Exception as e:
        logger.error(f"Encode failed (trace_id={trace_id}): {e}")
        raise


@app.post("/decode", response_model=DecodeResponse, tags=["Semantic Operations"])
async def decode_vector(request: DecodeRequest, req: Request) -> DecodeResponse:
    """
    Decode 5D vector back to text with optional reasoning.

    This endpoint reconstructs text from a semantic vector and provides
    explanations for which dimensions contributed to the result.

    **Graceful Degradation**: If reasoning fails, returns text with explainable=false.
    """
    trace_id = getattr(req.state, "trace_id", str(uuid.uuid4()))

    try:
        logger.info(f"Decoding vector (trace_id={trace_id})")

        # Clip vector to valid range
        vector = np.clip(request.vector, -1.0, 1.0)

        # Use InterpretableDecoder for decoding with reasoning
        result = interpretable_decoder.decode(vector.tolist(), top_k=request.top_k)

        # Convert InterpretableDecoder output to API format
        dimensions_reasoning = []
        for item in result["reasoning"]:
            dim_idx = item["dimension"]
            # Get dimension info for label
            dim_enum = list(SemanticDimension)[dim_idx]
            info = DimensionMapper.get_dimension_info(dim_enum)
            
            dimensions_reasoning.append(
                DimensionReasoning(
                    dim=dim_idx,
                    weight=abs(item["value"]),
                    label=info.name,
                    evidence=[item["contribution"]],  # Use contribution as evidence
                )
            )

        return DecodeResponse(
            text=result["text"],
            reasoning=dimensions_reasoning,
            explainable=result["explainable"],
            trace_id=trace_id,
        )

    except ValueError as e:
        # Handle validation errors (e.g., inf/nan values)
        logger.error(f"Decode validation failed (trace_id={trace_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Decode failed (trace_id={trace_id}): {e}")

        # Graceful degradation: return text without reasoning
        try:
            text = semantic_space.decode(np.array(request.vector))
            return DecodeResponse(text=text, reasoning=[], explainable=False, trace_id=trace_id)
        except:
            raise HTTPException(status_code=500, detail="Decode failed completely")


@app.post("/explain", response_model=ExplainResponse, tags=["Semantic Operations"])
async def explain_text(request: ExplainRequest, req: Request) -> ExplainResponse:
    """
    Explain how text is represented in semantic space.

    This endpoint encodes text and provides detailed explanations for each
    dimension's contribution to the representation.
    """
    trace_id = getattr(req.state, "trace_id", str(uuid.uuid4()))

    try:
        logger.info(f"Explaining text (trace_id={trace_id}, length={len(request.text)})")

        # Encode
        vector = semantic_space.encode(request.text)

        # Generate per-dimension explanations
        dims_explanations = []
        for i, dim in enumerate(SemanticDimension):
            info = DimensionMapper.get_dimension_info(dim)
            score = float(vector[i])

            # Get interpretation
            interpretation = DimensionMapper.interpret_value(dim, score)

            dims_explanations.append(
                DimensionExplanation(
                    i=i,
                    label=f"{info.name} ({interpretation})",
                    score=score,
                    examples=[],  # TODO: Add example words for this dimension
                )
            )

        return ExplainResponse(vector=vector.tolist(), dims=dims_explanations, trace_id=trace_id)

    except Exception as e:
        logger.error(f"Explain failed (trace_id={trace_id}): {e}")
        raise


# Hierarchical API endpoints
@app.post("/encode_h", response_model=EncodeHierarchicalResponse, tags=["Hierarchical Operations"])
async def encode_hierarchical(
    request: EncodeHierarchicalRequest, req: Request
) -> EncodeHierarchicalResponse:
    """
    Encode text into hierarchical 5D semantic tree.

    This endpoint converts input text into a hierarchical tree structure
    where each node has a 5D vector and can have up to 5 children.

    **Parameters:**
    - max_depth: Controls tree depth (0 = root only, 1 = root + children, etc.)
    - expand_threshold: Router confidence threshold for expanding children (0.0-1.0)

    **Security**: Raw text is not logged, only metadata.
    """
    trace_id = getattr(req.state, "trace_id", str(uuid.uuid4()))

    try:
        logger.info(f"Encoding hierarchical (trace_id={trace_id}, max_depth={request.max_depth})")

        tree = hierarchical_encoder.encode_hierarchical(
            request.text, max_depth=request.max_depth, expand_threshold=request.expand_threshold
        )

        return EncodeHierarchicalResponse(
            tree=tree, norm=True, max_depth=request.max_depth, trace_id=trace_id
        )

    except Exception as e:
        logger.error(f"Hierarchical encode failed (trace_id={trace_id}): {e}")
        raise


@app.post("/decode_h", response_model=DecodeHierarchicalResponse, tags=["Hierarchical Operations"])
async def decode_hierarchical(
    request: DecodeHierarchicalRequest, req: Request
) -> DecodeHierarchicalResponse:
    """
    Decode hierarchical tree back to text with path-wise reasoning.

    This endpoint reconstructs text from a hierarchical tree and provides
    explanations for which paths contributed to the result.

    **Path Format**: Paths like 'dim2/dim2.4' indicate root dimension 2, child dimension 4.

    **Graceful Degradation**: If reasoning fails, returns text with explainable=false.
    """
    trace_id = getattr(req.state, "trace_id", str(uuid.uuid4()))

    try:
        logger.info(f"Decoding hierarchical (trace_id={trace_id})")

        result = hierarchical_decoder.decode_hierarchical(
            request.tree, top_k=request.top_k, with_reasoning=True
        )

        return DecodeHierarchicalResponse(
            text=result["text"],
            reasoning=result.get("reasoning", []),
            explainable=bool(result.get("reasoning")),
            trace_id=trace_id,
        )

    except Exception as e:
        logger.error(f"Hierarchical decode failed (trace_id={trace_id}): {e}")

        # Graceful degradation
        try:
            result = hierarchical_decoder.decode_hierarchical(
                request.tree, top_k=request.top_k, with_reasoning=False
            )
            return DecodeHierarchicalResponse(
                text=result["text"], reasoning=[], explainable=False, trace_id=trace_id
            )
        except:
            raise HTTPException(status_code=500, detail="Hierarchical decode failed completely")


@app.post(
    "/manipulate_h", response_model=ManipulateHierarchicalResponse, tags=["Hierarchical Operations"]
)
async def manipulate_hierarchical(
    request: ManipulateHierarchicalRequest, req: Request
) -> ManipulateHierarchicalResponse:
    """
    Manipulate specific paths in hierarchical tree and see how meaning changes.

    This allows surgical edits to specific branches of the semantic tree,
    enabling fine-grained control over meaning.

    **Example edits:**
    ```json
    [
        {"path": "dim2/dim2.4", "value": [0.9, 0.1, -0.2, 0.0, 0.0]},
        {"path": "dim3", "value": [-0.5, 0.3, 0.8, 0.1, -0.2]}
    ]
    ```
    """
    trace_id = getattr(req.state, "trace_id", str(uuid.uuid4()))

    try:
        logger.info(f"Manipulating hierarchical (trace_id={trace_id}, edits={len(request.edits)})")

        # Encode original
        original_tree = hierarchical_encoder.encode_hierarchical(request.text, max_depth=2)
        original_decoded = hierarchical_decoder.decode_hierarchical(original_tree, top_k=3)

        # Apply edits
        modified_tree = original_tree
        for edit in request.edits:
            modified_tree = hierarchical_decoder.manipulate_path(
                modified_tree, edit.path, edit.value
            )

        # Decode modified
        modified_decoded = hierarchical_decoder.decode_hierarchical(modified_tree, top_k=3)

        return ManipulateHierarchicalResponse(
            original={
                "text": request.text,
                "tree": original_tree.model_dump(),
                "decoded": original_decoded,
            },
            modified={
                "tree": modified_tree.model_dump(),
                "decoded": modified_decoded,
                "edits_applied": [e.model_dump() for e in request.edits],
            },
            trace_id=trace_id,
        )

    except Exception as e:
        logger.error(f"Hierarchical manipulation failed (trace_id={trace_id}): {e}")
        raise


# Favicon endpoint
@app.get("/favicon.ico", tags=["Static"])
async def favicon():
    """Serve favicon"""
    try:
        import os

        static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "static")
        favicon_path = os.path.join(static_dir, "favicon.ico")
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path, media_type="image/x-icon")
    except Exception:
        pass
    # Fallback to 404
    raise HTTPException(status_code=404, detail="Favicon not found")


# Root endpoint
@app.get("/", tags=["Info"])
async def root():
    """API information endpoint"""
    return {
        "name": "Atlas Semantic Space API",
        "version": APP_VERSION,
        "description": "5D semantic space for interpretable text representations",
        "endpoints": {
            "encode": "POST /encode - Encode text to 5D vector",
            "decode": "POST /decode - Decode vector to text with reasoning",
            "explain": "POST /explain - Explain text's semantic representation",
            "encode_h": "POST /encode_h - Encode text to hierarchical tree (NEW)",
            "decode_h": "POST /decode_h - Decode tree to text with path reasoning (NEW)",
            "manipulate_h": "POST /manipulate_h - Manipulate tree paths (NEW)",
            "health": "GET /health - Health check",
            "ready": "GET /ready - Readiness check",
            "metrics": "GET /metrics - Prometheus metrics",
            "docs": "GET /docs - Interactive API documentation",
        },
        "hierarchical": {
            "description": "Hierarchical semantic space (matryoshka 5D)",
            "schema_version": "atlas-hier-2",
            "features": [
                "Multi-level semantic decomposition",
                "Path-wise reasoning and explanations",
                "Lazy expansion with router confidence",
                "Surgical manipulation of semantic branches",
            ],
        },
        "repository": "https://github.com/danilivashyna/Atlas",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
