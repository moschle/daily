#!/bin/bash
# Startet beide Stufen der MemPalace-Anbindung:
#   8765 = mcpo, macht aus dem stdio-MCP-Server eine HTTP-Schnittstelle (alle 29 Werkzeuge)
#   8766 = schlanke Bruecke, gibt davon nur sechs an Bonsai weiter
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin"
export MEMPALACE_PATH="$HOME/.mempalace/palace"

if ! curl -s --max-time 2 -o /dev/null http://127.0.0.1:8765/openapi.json; then
  uvx --with "mcp>=1.12,<2" --python 3.12 mcpo --host 127.0.0.1 --port 8765 \
    -- /usr/bin/python3 -m mempalace.mcp_server > /tmp/mcpo.log 2>&1 &
  for i in $(seq 1 60); do curl -s --max-time 2 -o /dev/null http://127.0.0.1:8765/openapi.json && break; sleep 2; done
fi

if ! curl -s --max-time 2 -o /dev/null http://127.0.0.1:8766/openapi.json; then
  cd "$HOME/Projects/daily" || exit 1
  uv run --with fastapi --with uvicorn --with httpx \
    uvicorn mempalace_bruecke:app --host 0.0.0.0 --port 8766 > /tmp/bruecke.log 2>&1 &
  for i in $(seq 1 40); do curl -s --max-time 2 -o /dev/null http://127.0.0.1:8766/openapi.json && break; sleep 2; done
fi

echo -n "mcpo 8765: "; curl -s --max-time 3 http://127.0.0.1:8765/openapi.json | /usr/bin/python3 -c "import sys,json;print(len(json.load(sys.stdin)['paths']),'Werkzeuge')" 2>/dev/null || echo "keine Antwort"
echo -n "Bruecke 8766: "; curl -s --max-time 3 http://127.0.0.1:8766/openapi.json | /usr/bin/python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d['paths']),'Werkzeuge:',list(d['paths']))" 2>/dev/null || tail -3 /tmp/bruecke.log
