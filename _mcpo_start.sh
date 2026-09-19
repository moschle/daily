#!/bin/bash
# MemPalace-Bruecke: stdio-MCP -> HTTP/OpenAPI, damit Open WebUI das Palais erreicht.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin"
pkill -f "mcpo --host 127.0.0.1 --port 8765" 2>/dev/null
sleep 1
export MEMPALACE_PATH="$HOME/.mempalace/palace"
uvx --refresh --with "mcp>=1.12,<2" --python 3.12 mcpo \
  --host 127.0.0.1 --port 8765 \
  -- /usr/bin/python3 -m mempalace.mcp_server > /tmp/mcpo.log 2>&1 &
for i in $(seq 1 60); do
  curl -s --max-time 2 -o /dev/null http://127.0.0.1:8765/openapi.json && { echo "OK"; break; }
  sleep 2
done
curl -s --max-time 3 http://127.0.0.1:8765/openapi.json | /usr/bin/python3 -c "import sys,json;d=json.load(sys.stdin);print('Tools:',len(d.get('paths',{})));print(list(d.get('paths',{}))[:8])" 2>/dev/null || tail -5 /tmp/mcpo.log
