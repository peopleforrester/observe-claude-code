# ABOUTME: FastMCP stdio server for the demo — a benign read tool and a sensitive deploy tool.
# ABOUTME: The deploy tool is the "don't touch prod" boundary denied by permission policy on stage.
from fastmcp import FastMCP

mcp = FastMCP("prod-api")


@mcp.tool
def get_status(service: str) -> dict:
    """Return the current status of a service. Read-only and safe to run."""
    return {
        "service": service,
        "status": "healthy",
        "version": "1.4.2",
        "environment": "production",
    }


@mcp.tool
def deploy(service: str, version: str) -> dict:
    """Deploy a service version to PRODUCTION. Sensitive, irreversible write action."""
    return {
        "service": service,
        "deployed_version": version,
        "environment": "production",
        "result": "deployment triggered",
    }


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
