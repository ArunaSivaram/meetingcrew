"""Connect to the GitHub MCP server and print every tool it exposes."""

import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

from crewai_tools import MCPServerAdapter  # noqa: E402

from meetings.mcp_client import get_github_server_params  # noqa: E402


def main() -> None:
    params = get_github_server_params()
    with MCPServerAdapter(params) as tools:
        for tool in tools:
            description = (tool.description or "").strip().splitlines()
            first_line = description[0] if description else ""
            print(f"{tool.name}: {first_line}")


if __name__ == "__main__":
    main()
