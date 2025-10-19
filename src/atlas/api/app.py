"""
Atlas FastAPI Application

REST API for semantic space operations with encode, decode, and explain endpoints.
"""

import time
import logging
import uuid
from typing import Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np

from atlas import SemanticSpace
from atlas.dimensions import DimensionMapper, SemanticDimension
from .models import (
    EncodeRequest, EncodeResponse,
    DecodeRequest, DecodeResponse, DimensionReasoning,
    ExplainRequest, ExplainResponse, DimensionExplanation,
    ErrorResponse, HealthResponse, MetricsResponse
)

# Configure logging (no raw text logging per security policy)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
semantic_space = None
metrics = {
    "requests_total": 0,
    "requests_by_endpoint": {},
    "latencies": {},
    "errors_total": 0
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup/shutdown"""
    global semantic_space
    
    # Startup
    logger.info("Initializing Atlas Semantic Space...")
    try:
        semantic_space = SemanticSpace()
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
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware (configure appropriately for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        metrics["requests_by_endpoint"][endpoint] = metrics["requests_by_endpoint"].get(endpoint, 0) + 1
        
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
        debug_info={
            "endpoint": request.url.path,
            "method": request.method
        }
    )
    
    # Determine HTTP status code
    if isinstance(exc, ValueError):
        status_code = 400
    elif isinstance(exc, HTTPException):
        status_code = exc.status_code
    else:
        status_code = 500
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump()
    )


# Health check endpoints
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(
        status="ok" if semantic_space is not None else "not_ready",
        version="0.1.0",
        model_loaded=semantic_space is not None
    )


@app.get("/ready", response_model=HealthResponse, tags=["Health"])
async def readiness_check():
    """Readiness probe - checks if model is loaded"""
    if semantic_space is None:
        raise HTTPException(status_code=503, detail="Semantic space not initialized")
    
    return HealthResponse(
        status="ready",
        version="0.1.0",
        model_loaded=True
    )


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
        errors_total=metrics["errors_total"]
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
        
        return EncodeResponse(
            vector=vector.tolist(),
            norm=True,
            trace_id=trace_id
        )
    
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
        
        # Decode with reasoning
        result = semantic_space.decode(vector, with_reasoning=True)
        
        if isinstance(result, str):
            # Simple decode without reasoning
            return DecodeResponse(
                text=result,
                reasoning=[],
                explainable=False,
                trace_id=trace_id
            )
        
        # Parse reasoning
        text = result.get('text', '')
        reasoning_text = result.get('reasoning', '')
        
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
                        evidence=[]  # TODO: Extract from reasoning text
                    )
                )
        
        # Sort by weight and take top_k
        dimensions_reasoning.sort(key=lambda x: x.weight, reverse=True)
        dimensions_reasoning = dimensions_reasoning[:request.top_k]
        
        return DecodeResponse(
            text=text,
            reasoning=dimensions_reasoning,
            explainable=True,
            trace_id=trace_id
        )
    
    except Exception as e:
        logger.error(f"Decode failed (trace_id={trace_id}): {e}")
        
        # Graceful degradation: return text without reasoning
        try:
            text = semantic_space.decode(np.array(request.vector))
            return DecodeResponse(
                text=text,
                reasoning=[],
                explainable=False,
                trace_id=trace_id
            )
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
                    examples=[]  # TODO: Add example words for this dimension
                )
            )
        
        return ExplainResponse(
            vector=vector.tolist(),
            dims=dims_explanations,
            trace_id=trace_id
        )
    
    except Exception as e:
        logger.error(f"Explain failed (trace_id={trace_id}): {e}")
        raise


# Root endpoint
@app.get("/", tags=["Info"])
async def root():
    """API information endpoint"""
    return {
        "name": "Atlas Semantic Space API",
        "version": "0.1.0",
        "description": "5D semantic space for interpretable text representations",
        "endpoints": {
            "encode": "POST /encode - Encode text to 5D vector",
            "decode": "POST /decode - Decode vector to text with reasoning",
            "explain": "POST /explain - Explain text's semantic representation",
            "health": "GET /health - Health check",
            "ready": "GET /ready - Readiness check",
            "metrics": "GET /metrics - Prometheus metrics",
            "docs": "GET /docs - Interactive API documentation",
        },
        "repository": "https://github.com/danilivashyna/Atlas"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
