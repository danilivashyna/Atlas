# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Atlas FastAPI Application

REST API for semantic space operations with encode, decode, and explain endpoints.
"""

import json
import logging
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager
from importlib.metadata import version as pkg_version
from typing import Any, Dict, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from atlas import SemanticSpace
from atlas.dimensions import DimensionMapper, SemanticDimension
from atlas.hierarchical import (
    DecodeHierarchicalRequest,
    DecodeHierarchicalResponse,
    EncodeHierarchicalRequest,
    EncodeHierarchicalResponse,
    HierarchicalDecoder,
    HierarchicalEncoder,
    ManipulateHierarchicalRequest,
    ManipulateHierarchicalResponse,
)

from .models import (
    DecodeRequest,
    DecodeResponse,
    DimensionExplanation,
    DimensionReasoning,
    EncodeRequest,
    EncodeResponse,
    ErrorResponse,
    ExplainRequest,
    ExplainResponse,
    HealthResponse,
    MetricsResponse,
    SummarizeRequest,
    SummarizeResponse,
)

# Configure logging (no raw text logging per security policy)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _ensure_str(v: Optional[str] | Dict[str, Any] | None) -> str:
    """Convert value to str, handling None and dict gracefully."""
    if v is None:
        return ""
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


# Feature flags

SUMMARY_MODE = os.getenv("ATLAS_SUMMARY_MODE", "proportional").lower()
# Memory feature flag: on|off
MEMORY_MODE = os.getenv("ATLAS_MEMORY_MODE", "on").lower()
# Memory backend: inproc | sqlite
MEMORY_BACKEND = os.getenv("ATLAS_MEMORY_BACKEND", "inproc").lower()
# Router feature flag: on|off
ROUTER_MODE = os.getenv("ATLAS_ROUTER_MODE", "on").lower()
# Router scoring parameters
ROUTER_ALPHA = float(os.getenv("ATLAS_ROUTER_ALPHA", "0.7"))
ROUTER_BETA = float(os.getenv("ATLAS_ROUTER_BETA", "0.15"))
ROUTER_GAMMA = float(os.getenv("ATLAS_ROUTER_GAMMA", "0.1"))
ROUTER_DELTA = float(os.getenv("ATLAS_ROUTER_DELTA", "0.05"))  # v0.5: path-aware prior
ROUTER_TAU = float(os.getenv("ATLAS_ROUTER_TAU", "0.5"))
ROUTER_DECAY = float(os.getenv("ATLAS_ROUTER_DECAY", "0.85"))  # v0.5: inherited weight decay
# Beam loop parameters (v0.6)
ROUTER_BEAM = int(os.getenv("ATLAS_ROUTER_BEAM", "5"))
ROUTER_DEPTH = int(os.getenv("ATLAS_ROUTER_DEPTH", "2"))
ROUTER_CONF = float(os.getenv("ATLAS_ROUTER_CONF", "0.85"))
ROUTER_K_MULT = float(os.getenv("ATLAS_ROUTER_K_MULT", "3.0"))

# ANN index (v0.5)
ANN_BACKEND = os.getenv("ATLAS_ANN_BACKEND", "inproc")  # inproc | faiss | off
ANN_INDEX_PATH = os.getenv("ATLAS_ANN_INDEX_PATH", "/tmp/atlas_nodes.faiss")

# Get package version
try:
    APP_VERSION = pkg_version("atlas")
except Exception:
    APP_VERSION = "0.2.0a1"

# Global state
semantic_space = None
hierarchical_encoder = None
hierarchical_decoder = None
metrics = {"requests_total": 0, "requests_by_endpoint": {}, "latencies": {}, "errors_total": 0}

# Autoscaling state (v0.7)
autoscale_beam = ROUTER_BEAM
autoscale_depth = ROUTER_DEPTH
autoscale_tau = ROUTER_TAU
autoscale_recent_conf = []  # last 10 confidence values
autoscale_timer = None


def autoscale_controller():
    """Background autoscaling task."""
    from atlas.metrics.mensum import metrics_ns

    global autoscale_beam  # Only autoscale_beam is actually modified

    try:
        # Check if enabled
        if os.getenv("ATLAS_AUTOSCALE", "on").lower() == "off":
            return

        # Get recent confidence (mock for now, in real would query mensum)
        # For simplicity, assume some logic
        if autoscale_recent_conf:
            avg_conf = sum(autoscale_recent_conf) / len(autoscale_recent_conf)
            if avg_conf > 0.9 and autoscale_beam > 3:
                old_beam = autoscale_beam
                autoscale_beam -= 1
                metrics_ns().inc_counter(
                    "autoscale_changes_total", labels={"param": "beam", "direction": "down"}
                )
                logger.info(
                    "autoscale: beam %d→%d (conf=%.3f)", old_beam, autoscale_beam, avg_conf
                )
            elif avg_conf < 0.8 and autoscale_beam < 12:
                old_beam = autoscale_beam
                autoscale_beam += 1
                metrics_ns().inc_counter(
                    "autoscale_changes_total", labels={"param": "beam", "direction": "up"}
                )
                logger.info(
                    "autoscale: beam %d→%d (conf=%.3f)", old_beam, autoscale_beam, avg_conf
                )

        # Clear recent conf for next period
        autoscale_recent_conf.clear()

    except Exception as e:
        logger.error("Autoscale error: %s", e)
    finally:
        # Schedule next
        period = int(os.getenv("ATLAS_AUTOSCALE_PERIOD_S", "30"))
        autoscale_timer = threading.Timer(period, autoscale_controller)
        autoscale_timer.start()


@asynccontextmanager
async def lifespan(_app: FastAPI):  # Renamed to avoid shadowing outer 'app'
    """Lifecycle manager for startup/shutdown"""
    global semantic_space, hierarchical_encoder, hierarchical_decoder

    # Startup
    logger.info("Initializing Atlas Semantic Space...")
    try:
        semantic_space = SemanticSpace()
        hierarchical_encoder = HierarchicalEncoder()
        hierarchical_decoder = HierarchicalDecoder()
        logger.info("Atlas Semantic Space initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize Semantic Space: %s", e)
        raise

    # Start autoscaling controller
    if os.getenv("ATLAS_AUTOSCALE", "on").lower() != "off":
        autoscale_controller()
        logger.info("Autoscaling controller started")

    # Attempt to register optional memory routes at startup. This is done here
    # (not only at import time) so that TestClient and other runtimes pick up
    # the routes even if the module import happened earlier.
    try:
        import atlas.api.memory_routes  # noqa: F401,E501
    except Exception:
        # Memory package optional - ignore if missing or broken during tests
        logger.debug("Optional memory routes not available at startup")

    yield

    # Shutdown
    if autoscale_timer:
        autoscale_timer.cancel()
        logger.info("Autoscaling controller stopped")
    logger.info("Shutting down Atlas API...")


# Create FastAPI app
log_level = os.getenv("ATLAS_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
logger.info("Atlas API initializing... (log_level=%s)", log_level)

app = FastAPI(
    title="Atlas Semantic Space API",
    description="5D semantic space interface for encoding, decoding, and explaining text",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---- Optional feature sets -------------------------------------------------
# Memory routes (write, query, flush, load, stats)
try:
    from atlas.api import memory_routes as _mr

    app.include_router(_mr.router)  # tags=["Memory"] set in router
    logger.info("Memory routes registered")
except Exception as e:
    logger.warning("Memory routes not registered: %s", e)

# Router routes (route, activate)
try:
    from atlas.api import router_routes as _rr

    app.include_router(_rr.router)  # tags=["Router"] set in router
    logger.info("Router routes registered")
except Exception as e:
    logger.warning("Router routes not registered: %s", e)

# Router batch + index routes (v0.5)
try:
    from atlas.api import router_batch_routes as _rbr

    app.include_router(_rbr.router)  # tags=["Router"] set in router
    logger.info("Router batch routes registered")
except Exception as e:
    logger.warning("Router batch routes not registered: %s", e)

# Reticulum routes (content links, v0.5)
try:
    from atlas.api import reticulum_routes as _reticulum

    app.include_router(_reticulum.router)  # tags=["Reticulum"] set in router
    logger.info("Reticulum routes registered")
except Exception as e:
    logger.warning("Reticulum routes not registered: %s", e)

# Homeostasis routes (E4.7 control plane)
try:
    from atlas.api.homeostasis_routes import create_homeostasis_router
    from atlas.api.homeostasis_stubs import create_homeostasis_stubs

    # Initialize stub dependencies in app.state
    stubs = create_homeostasis_stubs()
    app.state.policy_engine = stubs["policy_engine"]
    app.state.action_executor = stubs["action_executor"]
    app.state.audit_logger = stubs["audit_logger"]
    app.state.snapshot_manager = stubs["snapshot_manager"]

    app.include_router(create_homeostasis_router())
    logger.info("Homeostasis routes registered (using stubs)")
except Exception as e:
    logger.warning("Homeostasis routes not registered: %s", e)

# FAB integration routes (v0.1 Shadow Mode)
try:
    from atlas.api.fab_routes import create_fab_router

    app.include_router(create_fab_router())
    logger.info("FAB routes registered (v0.1 Shadow mode)")
except Exception as e:
    logger.warning("FAB routes not registered: %s", e)

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
    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
except Exception as e:
    logger.debug("Static mount skipped: %s", e)


# Middleware for request tracking
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track request metrics without logging sensitive data"""
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id

    # Log metadata only (no user data)
    logger.info("Request %s: %s %s", trace_id, request.method, request.url.path)

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

        logger.info("Request %s completed in %.2fms", trace_id, latency_ms)

        return response

    except Exception as e:
        metrics["errors_total"] += 1
        logger.error("Request %s failed: %s", trace_id, str(e))
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
    logger.error("Error %s: %s - %s", trace_id, error_type, message)

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
    """Prometheus-compatible metrics endpoint (includes v0.5 mensum metrics)"""
    # Calculate average latencies
    avg_latency = {}
    for endpoint, latencies in metrics["latencies"].items():
        if latencies:
            avg_latency[endpoint] = sum(latencies) / len(latencies)

    # Get v0.5 mensum metrics
    try:
        from atlas.metrics.mensum import metrics as get_mensum_metrics

        mensum = get_mensum_metrics().to_json()
        # Merge mensum into response
        base_response = {
            "requests_total": metrics["requests_total"],
            "requests_by_endpoint": metrics["requests_by_endpoint"],
            "avg_latency_ms": avg_latency,
            "errors_total": metrics["errors_total"],
        }
        # Include v0.5 mensum metrics
        base_response["v0_5_mensum"] = mensum
        return base_response
    except Exception:
        pass

    return MetricsResponse(
        requests_total=metrics["requests_total"],
        requests_by_endpoint=metrics["requests_by_endpoint"],
        avg_latency_ms=avg_latency,
        errors_total=metrics["errors_total"],
    )


@app.get("/metrics/prom")
def metrics_prom():
    from atlas.metrics.mensum import metrics_ns

    text = metrics_ns().to_prom()
    return Response(content=text, media_type="text/plain; version=0.0.4")


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
        logger.info("Encoding text (trace_id=%s, length=%d)", trace_id, len(request.text))

        vector = semantic_space.encode(request.text)

        return EncodeResponse(vector=vector.tolist(), norm=True, trace_id=trace_id)

    except Exception as e:
        logger.error("Encode failed (trace_id=%s): %s", trace_id, e)
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
        logger.info("Decoding vector (trace_id=%s)", trace_id)

        # Clip vector to valid range
        vector = np.clip(request.vector, -1.0, 1.0)

        # Decode with reasoning
        result = semantic_space.decode(vector, with_reasoning=True)

        if isinstance(result, str):
            # Simple decode without reasoning
            return DecodeResponse(text=result, reasoning=[], explainable=False, trace_id=trace_id)

        # Parse reasoning
        text = result.get("text", "")
        reasoning_text = result.get("reasoning", "")

        # Extract dimension contributions
        dimensions_reasoning = []
        for i, dim in enumerate(SemanticDimension):
            dim_value = abs(vector[i])
            if dim_value > 0.1:  # Only include significant dimensions
                info = DimensionMapper.get_dimension_info(dim)
                dimensions_reasoning.append(
                    DimensionReasoning(
                        dim=i,
                        weight=float(dim_value),
                        label=info.name,
                        evidence=[],  # TODO: Extract from reasoning text
                    )
                )

        # Sort by weight and take top_k
        dimensions_reasoning.sort(key=lambda x: x.weight, reverse=True)
        dimensions_reasoning = dimensions_reasoning[: request.top_k]

        return DecodeResponse(
            text=text, reasoning=dimensions_reasoning, explainable=True, trace_id=trace_id
        )

    except Exception as e:
        logger.error("Decode failed (trace_id=%s): %s", trace_id, e)

        # Graceful degradation: return text without reasoning
        try:
            text = semantic_space.decode(np.array(request.vector))
            return DecodeResponse(text=text, reasoning=[], explainable=False, trace_id=trace_id)
        except Exception:
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
        logger.info("Explaining text (trace_id=%s, length=%d)", trace_id, len(request.text))

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
        logger.error("Explain failed (trace_id=%s): %s", trace_id, e)
        raise


@app.post("/summarize", response_model=SummarizeResponse, tags=["Semantic Operations"])
async def summarize_text(request: SummarizeRequest, req: Request) -> SummarizeResponse:
    """
    Length-controlled summarization with 5D semantic ratio preservation.

    This endpoint performs proportional summarization that maintains the semantic
    distribution of the source text while compressing or expanding to a target length.

    **Algorithm:**
    1. Encode source text to 5D vector and normalize to probability distribution
    2. Collect evidence (text pieces) for each dimension with weights
    3. Calculate token quotas per dimension: t_i = round(L' * p_i)
    4. Greedily fill content from each dimension, avoiding repeats
    5. Verify KL divergence D_KL(p||p') ≤ ε and adjust if needed

    **Modes:**
    - `compress`: Reduce text to target_tokens while preserving semantics
    - `expand`: Expand text to target_tokens by elaborating on key points

    **Feature Flag:**
    Controlled by `ATLAS_SUMMARY_MODE` environment variable:
    - `proportional` (default): Use KL-controlled proportional algorithm
    - `off`: Endpoint returns 503 Service Unavailable

    **Graceful Degradation:**
    If evidence extraction fails, falls back to simple truncation/expansion.
    """
    trace_id = getattr(req.state, "trace_id", str(uuid.uuid4()))

    # Check feature flag
    if SUMMARY_MODE == "off":
        raise HTTPException(
            status_code=503, detail="Summarization feature is disabled (ATLAS_SUMMARY_MODE=off)"
        )

    try:
        logger.info(
            "Summarizing text (trace_id=%s, length=%d, target=%d, mode=%s)",
            trace_id,
            len(request.text),
            request.target_tokens,
            request.mode,
        )

        # Import summarize function
        from atlas.summarize import summarize

        # Perform summarization
        result = summarize(
            text=request.text,
            target_tokens=request.target_tokens,
            mode=request.mode,
            epsilon=request.epsilon,
            preserve_order=request.preserve_order,
            encoder=semantic_space.encoder if semantic_space else None,
            use_memory=request.use_memory,
            memory_top_k=int(request.memory_top_k),
            memory_weight=float(request.memory_weight),
        )

        # Build response
        return SummarizeResponse(
            summary=result["summary"],
            length=result["length"],
            ratio_target=result["ratio_target"],
            ratio_actual=result["ratio_actual"],
            kl_div=result["kl_div"],
            trace_id=trace_id,
        )

    except Exception as e:
        logger.error("Summarize failed (trace_id=%s): %s", trace_id, e)
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


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

    if hierarchical_encoder is None:
        raise HTTPException(status_code=500, detail="Hierarchical encoder not initialized")

    try:
        logger.info(
            "Encoding hierarchical (trace_id=%s, max_depth=%d)", trace_id, request.max_depth
        )

        tree = hierarchical_encoder.encode_hierarchical(
            request.text, max_depth=request.max_depth, expand_threshold=request.expand_threshold
        )

        return EncodeHierarchicalResponse(
            tree=tree, norm=True, max_depth=request.max_depth, trace_id=trace_id
        )

    except Exception as e:
        logger.error("Hierarchical encode failed (trace_id=%s): %s", trace_id, e)
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

    if hierarchical_decoder is None:
        raise HTTPException(status_code=500, detail="Hierarchical decoder not initialized")

    try:
        logger.info("Decoding hierarchical (trace_id=%s)", trace_id)

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
        logger.error("Hierarchical decode failed (trace_id=%s): %s", trace_id, e)

        # Graceful degradation
        try:
            result = hierarchical_decoder.decode_hierarchical(
                request.tree, top_k=request.top_k, with_reasoning=False
            )
            return DecodeHierarchicalResponse(
                text=result["text"], reasoning=[], explainable=False, trace_id=trace_id
            )
        except Exception:
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

    if hierarchical_encoder is None or hierarchical_decoder is None:
        raise HTTPException(
            status_code=500, detail="Hierarchical encoder/decoder not initialized"
        )

    try:
        logger.info(
            "Manipulating hierarchical (trace_id=%s, edits=%d)", trace_id, len(request.edits)
        )

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
        logger.error("Hierarchical manipulation failed (trace_id=%s): %s", trace_id, e)
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
            "summarize": "POST /summarize - Length-controlled summarization with semantic preservation",
            "memory": "POST /memory/* - Memory backend (write/query/flush/load) + GET /memory/stats",
            "router": {
                "route": "POST /router/route - Route text to hierarchical nodes",
                "activate": "POST /router/activate - Soft-activate children of a node",
                "route_batch": "POST /router/route_batch - Batch routing queries (v0.5)",
                "index_rebuild": "POST /router/index/rebuild - Rebuild ANN index (v0.5)",
                "index_update": "POST /router/index/update - Incremental ANN updates (v0.5.1)",
            },
            "reticulum": {
                "link": "POST /reticulum/link - Link content to a node (v0.5)",
                "query": "POST /reticulum/query - Query linked content by path (v0.5)",
                "link_version": "POST /reticulum/link_version - Versioned content links (v0.5.3)",
                "resolve": "POST /reticulum/resolve - Resolve latest links by content_id (v0.5.3)",
                "recent": "POST /reticulum/recent - Recency-weighted content queries (v0.5.3)",
            },
            "encode_h": "POST /encode_h - Encode text to hierarchical tree",
            "decode_h": "POST /decode_h - Decode tree to text with path reasoning",
            "manipulate_h": "POST /manipulate_h - Manipulate tree paths",
            "health": "GET /health - Health check",
            "ready": "GET /ready - Readiness check",
            "metrics": "GET /metrics - Prometheus metrics + v0.5 metrics (mensum)",
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
