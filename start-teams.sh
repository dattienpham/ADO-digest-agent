#!/bin/sh
exec fastmcp run teams_mcp_server.py --transport streamable-http --host 0.0.0.0 --port "$PORT"
