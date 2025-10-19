#!/usr/bin/env python
"""
Run Atlas API server

Usage:
    python scripts/run_api.py [--host HOST] [--port PORT] [--reload]
"""

import argparse
import sys
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="Run Atlas API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])
    
    args = parser.parse_args()
    
    print(f"Starting Atlas API server on {args.host}:{args.port}")
    print(f"API docs available at http://{args.host}:{args.port}/docs")
    print(f"Health check at http://{args.host}:{args.port}/health")
    print()
    
    try:
        uvicorn.run(
            "atlas.api.app:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level
        )
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)

if __name__ == "__main__":
    main()
