"""
zettaquant-vslm-mcp - MCP server for ZettaQuant V-SLM.

Exposes one tool over stdio to any MCP-aware host (Claude Desktop, Cursor,
Zed, Windsurf, ChatGPT dev mode):

  - vslm_predict   Filter sentences to only those relevant to a topic.
                   Always uses the general_context_agent, broad-domain,
                   works across financial text, transcripts, news, reports,
                   and beyond.

Usage
-----
The host spawns this package as a subprocess (via `uvx zettaquant-vslm-mcp`
or `python -m zettaquant_vslm_mcp`) and speaks JSON-RPC over stdin/stdout.
Configure it in the host's MCP config with the user's ZettaQuant API key:

    {
      "mcpServers": {
        "zettaquant-vslm": {
          "command": "uvx",
          "args": ["zettaquant-vslm-mcp"],
          "env": { "ZQ_API_KEY": "<your api key>" }
        }
      }
    }
"""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# Base URL is overridable so we can point at staging / a private gateway.
ZQ_BASE_URL = os.environ.get("ZQ_BASE_URL", "https://api.zettaquant.ai").rstrip("/")
ZQ_API_KEY = os.environ.get("ZQ_API_KEY", "")

# The only ZQ "agent" this MCP server exposes.
VSLM_AGENT = "general_context_agent"

if not ZQ_API_KEY:
    print(
        "zettaquant-vslm-mcp: ZQ_API_KEY environment variable is not set.\n"
        "  Set it in your MCP host config, e.g. Claude Desktop's\n"
        "  claude_desktop_config.json under mcpServers.<name>.env.ZQ_API_KEY.",
        file=sys.stderr,
    )

_HTTP_TIMEOUT_S = 120.0

mcp = FastMCP("zettaquant-vslm")


def _require_key() -> None:
    """Raise if ZQ_API_KEY is missing so the host surfaces a clear tool error."""
    if not ZQ_API_KEY:
        raise RuntimeError(
            "ZQ_API_KEY is not set. Add it to the MCP host config under "
            "mcpServers.<name>.env.ZQ_API_KEY, then restart the host."
        )


def _headers() -> dict[str, str]:
    return {"x-api-key": ZQ_API_KEY, "content-type": "application/json"}


def _friendly_http_error(exc: httpx.HTTPStatusError) -> RuntimeError:
    """Turn common ZettaQuant HTTP errors into readable messages for the LLM."""
    status = exc.response.status_code
    try:
        body = exc.response.json()
    except Exception:
        body = {"raw": exc.response.text[:500]}

    if status == 401:
        msg = "ZettaQuant auth failed (401). Check ZQ_API_KEY in your MCP host config."
    elif status == 402:
        msg = f"ZettaQuant plan not active (402). {body.get('message', '')}"
    elif status == 403:
        msg = f"ZettaQuant access denied (403). {body.get('message', body)}"
    elif status == 429:
        msg = (
            f"ZettaQuant quota exceeded (429). "
            f"{body.get('message', '')}; quota resets at {body.get('resets_at', 'next period')}."
        )
    elif status in (502, 503):
        msg = f"ZettaQuant upstream temporarily unavailable ({status}); retry later."
    else:
        msg = f"ZettaQuant returned HTTP {status}: {body}"
    return RuntimeError(msg)


@mcp.tool()
async def vslm_predict(
    sentences: list[str],
    query: str,
) -> dict[str, Any]:
    """Filter a list of sentences to only those relevant to `query`.

    Use this BEFORE feeding noisy context (earnings-call transcripts, news
    articles, long reports, log lines) to an LLM; it typically cuts token
    spend without losing important context. Chain it with your own language model.

    Args:
        sentences: raw input sentences; ~2000 per call is comfortable.
        query: natural-language description of the topic to filter for
            (e.g. "AI capex plans", "rate cuts", "supply chain risk").

    Returns:
        dict with:
          relevant_sentences: sentences that passed the filter, original order.
          total_sentences, relevant_count: counts to compute savings.
          topic_used: the topic string the model actually filtered against.
          topic_source: "zettaquant" (server-derived) or "caller" (you supplied).
          model_id: which V-SLM head handled the request.
    """
    _require_key()
    if not sentences:
        return {
            "agent": VSLM_AGENT,
            "model_id": None,
            "topic_used": query,
            "topic_source": "caller",
            "relevant_sentences": [],
            "total_sentences": 0,
            "relevant_count": 0,
        }
    payload = {"agent": VSLM_AGENT, "sentences": sentences, "query": query}
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_S) as client:
        try:
            r = await client.post(
                f"{ZQ_BASE_URL}/v1/vslm/predict",
                headers=_headers(),
                json=payload,
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise _friendly_http_error(e) from None
        return r.json()


def main() -> None:
    """Console-script entrypoint. Runs stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
