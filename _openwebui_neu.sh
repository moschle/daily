#!/bin/bash
# Open WebUI mit fester Bonsai-Verbindung UND fest eingetragenem MemPalace-Werkzeugserver.
# Daten bleiben im Volume "open-webui".
D=/usr/local/bin/docker
set -e

TOOLS='[{"url":"http://host.docker.internal:8766","path":"openapi.json","auth_type":"bearer","key":"","config":{"enable":true,"access_control":null}}]'

$D rm -f open-webui >/dev/null 2>&1 || true
$D run -d --name open-webui \
  -p 3000:8080 \
  --restart always \
  -v open-webui:/app/backend/data \
  --add-host=host.docker.internal:host-gateway \
  -e OPENAI_API_BASE_URL=http://host.docker.internal:8080/v1 \
  -e OPENAI_API_KEY=local \
  -e ENABLE_OPENAI_API=true \
  -e TOOL_SERVER_CONNECTIONS="$TOOLS" \
  -e ENABLE_AUTOCOMPLETE_GENERATION=false \
  -e ENABLE_TAGS_GENERATION=false \
  -e TASK_MODEL_EXTERNAL="" \
  ghcr.io/open-webui/open-webui:main >/dev/null

for i in $(seq 1 60); do curl -s --max-time 2 -o /dev/null http://127.0.0.1:3000/ && break; sleep 2; done
sleep 6
echo "--- Werkzeugserver aus dem Container erreichbar:"
$D exec open-webui curl -s --max-time 8 http://host.docker.internal:8766/openapi.json \
  | python3 -c "import sys,json;print(len(json.load(sys.stdin)['paths']),'Werkzeuge')" 2>&1 | tail -1
echo "--- Modellserver erreichbar:"
$D exec open-webui curl -s --max-time 8 -o /dev/null -w '%{http_code}\n' http://host.docker.internal:8080/v1/models
echo "--- Open WebUI:"
curl -s --max-time 3 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/
