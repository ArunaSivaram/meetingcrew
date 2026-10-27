"""Build the StdioServerParameters CrewAI needs to launch the GitHub MCP server."""

import os

from mcp import StdioServerParameters


def get_github_server_params() -> StdioServerParameters:
    """Return parameters that tell MCP how to start the GitHub MCP server over stdio.

    Default: run the official container image via Docker.
    If GITHUB_MCP_BINARY is set in .env, use that local binary instead (faster,
    no Docker needed — useful while learning).
    """
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    binary = os.environ.get("GITHUB_MCP_BINARY")

    env = {
        "GITHUB_PERSONAL_ACCESS_TOKEN": token,
        "GITHUB_TOOLSETS": "issues,users,repos",
        "PATH": os.environ.get("PATH", ""),
    }

    if binary:
        return StdioServerParameters(
            command=binary,
            args=["stdio"],
            env=env,
        )

    return StdioServerParameters(
        command="docker",
        args=[
            "run",
            "-i",
            "--rm",
            "-e",
            "GITHUB_PERSONAL_ACCESS_TOKEN",
            "-e",
            "GITHUB_TOOLSETS",
            "ghcr.io/github/github-mcp-server",
        ],
        env=env,
    )
