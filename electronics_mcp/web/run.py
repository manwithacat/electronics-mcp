"""Web UI entry point for ElectronicsMCP."""

import uvicorn

from electronics_mcp.web.app import app  # noqa: F401


def main():
    uvicorn.run(
        "electronics_mcp.web.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
