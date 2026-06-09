#!/bin/sh
exec fastmcp run mcp_server.py --transport streamable-http --host 0.0.0.0 --port "$PORT"
