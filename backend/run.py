from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    # Cloud hosts (Railway/Render) inject PORT; local uses BACKEND_PORT
    port = int(os.getenv("PORT") or os.getenv("BACKEND_PORT", "8000"))
    reload = os.getenv("APP_ENV", "development") == "development"

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,  # auto-restart when you save a file (dev only)
    )


if __name__ == "__main__":
    main()
