#!/usr/bin/env python3
"""Run the CrewSasToSparkSql FastAPI server."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "crewsastosparksql.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (disable in production)
        log_level="info"
    )
