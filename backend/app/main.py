"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes
from app.config import settings

# Create FastAPI app
app = FastAPI(
    title="Stock Drop Forensic Analysis API",
    description="A forensic market-context and pattern-recognition API for stock analysis. Prepare, Don't Predict.",
    version="1.0.0",
    debug=settings.debug
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(routes.router, prefix="/api", tags=["analysis"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Stock Drop Forensic Analysis API",
        "version": "1.0.0",
        "philosophy": "Prepare, Don't Predict",
        "description": "This tool helps you recognize historical patterns, risk regimes, and behavioral signals. It does not predict market direction or recommend actions.",
        "endpoints": {
            "chart": "/api/chart/{ticker}?range=max&interval=1d",
            "analyze_range": "POST /api/analyze-range",
            "analyze": "POST /api/analyze",
            "regime": "/api/context/regime",
            "valuation": "/api/context/valuation",
            "crowd": "/api/context/crowd",
            "rotation": "/api/context/rotation",
            "pattern_analogs": "POST /api/pattern/analogs",
            "cache_stats": "/api/cache/stats"
        },
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "stock-drop-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
