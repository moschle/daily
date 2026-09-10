"""Claude Messages API mit Modell-Fallback.

claude-sonnet-4-20250514 liefert seit Sommer 2026 HTTP 400.
Aktuell: claude-sonnet-5, danach ältere Aliasse.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

MODELS = [m.strip() for m in os.environ.get("JURABRIEF_MODELL", "").split(",") if m.strip()] or [
    "claude-sonnet-5",
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "claude-sonnet-4-20250514",
]
API = "https://api.anthropic.com/v1/messages"
VERSION = "2023-06-01"


def complete(prompt: str, max_tokens: int = 3000) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY nicht gesetzt")

    last_err = None
    for model in MODELS:
        payload = json.dumps({
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            API,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": VERSION,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            text = next((b["text"] for b in data.get("content", [])
                         if b.get("type") == "text" and b.get("text")), None)
            if text is None:
                raise ValueError("Antwort ohne Textblock")
            if model != MODELS[0]:
                print(f"Claude: Fallback-Modell {model}", file=sys.stderr)
            return text
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:800]
            last_err = f"HTTP {e.code} {model}: {body}"
            print(f"Claude {model} abgelehnt: {last_err}", file=sys.stderr)
            if e.code in (401, 403):
                break
        except Exception as e:
            last_err = f"{model}: {e}"
            print(f"Claude {last_err}", file=sys.stderr)
    raise RuntimeError(last_err or "Claude API ohne Antwort")
