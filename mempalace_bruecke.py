"""Schlanke MemPalace-Brücke für Bonsai.

mcpo auf Port 8765 legt alle 29 MemPalace-Werkzeuge offen. Bei 16k Kontext
frisst das zu viel Prompt. Dieser Proxy reicht nur die durch, die im
täglichen Gebrauch zählen, und leitet die Aufrufe unverändert weiter.

Start: ~/Projects/daily/_bruecke_start.sh
"""

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

UPSTREAM = "http://127.0.0.1:8765"

ERLAUBT = [
    "/mempalace_search",
    "/mempalace_get_drawer",
    "/mempalace_add_drawer",
    "/mempalace_update_drawer",
    "/mempalace_list_wings",
    "/mempalace_kg_query",
]

app = FastAPI(
    title="MemPalace",
    description="Gemeinsames Gedaechtnis. Suchen, lesen, ablegen.",
    version="1.0.0",
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)


@app.get("/openapi.json")
async def spec():
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{UPSTREAM}/openapi.json")
        d = r.json()
    d["paths"] = {k: v for k, v in d.get("paths", {}).items() if k in ERLAUBT}
    d["info"] = {
        "title": "MemPalace",
        "description": (
            "Das gemeinsame Gedaechtnis von Moritz. Hier stehen Arbeitsstaende, "
            "Entscheidungen und Kontext aus allen Projekten. Vor einer Aufgabe "
            "zuerst suchen, nach einer Aufgabe das Ergebnis ablegen."
        ),
        "version": "1.0.0",
    }
    return JSONResponse(d)


@app.post("{pfad:path}")
async def weiterleiten(pfad: str, request: Request):
    if pfad not in ERLAUBT:
        return JSONResponse({"error": f"Werkzeug {pfad} ist hier nicht freigegeben"}, status_code=404)
    koerper = await request.body()
    async with httpx.AsyncClient(timeout=300) as c:
        r = await c.post(
            f"{UPSTREAM}{pfad}",
            content=koerper,
            headers={"content-type": "application/json"},
        )
    try:
        return JSONResponse(r.json(), status_code=r.status_code)
    except Exception:
        return JSONResponse({"raw": r.text}, status_code=r.status_code)
