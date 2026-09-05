# zettaquant-vslm-mcp

**MCP server that exposes ZettaQuant V-SLM to any MCP-aware LLM host.**

Add three lines to your Claude Desktop / Cursor / Zed / Windsurf config and your model can filter noisy context (earnings-call transcripts, news articles, long reports, log lines) using ZettaQuant's topic-conditioned relevancy classifier — typically cutting token spend before the language model even sees the input.

---

## What it exposes

One tool, over stdio, via the [Model Context Protocol](https://modelcontextprotocol.io):

| Tool | Purpose |
|---|---|
| `vslm_predict(sentences, query)` | Filter `sentences` to only those relevant to `query`. Returns `relevant_sentences` plus stats. Uses the broad-domain V-SLM `general_context_agent` under the hood. |

The LLM decides when to call it on its own — no code you have to write in the host.

---

## Install & configure

You need a ZettaQuant API key with the `vslm` scope. Get one at [zettaquant.ai](https://zettaquant.ai) (or ask your account contact).

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "zettaquant-vslm": {
      "command": "uvx",
      "args": ["zettaquant-vslm-mcp"],
      "env": {
        "ZQ_API_KEY": "<your api key>"
      }
    }
  }
}
```

Restart Claude Desktop. The tools appear under the "Tools" menu.

### Cursor

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "zettaquant-vslm": {
      "command": "uvx",
      "args": ["zettaquant-vslm-mcp"],
      "env": { "ZQ_API_KEY": "<your api key>" }
    }
  }
}
```

Restart Cursor.

### Zed

In `~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "zettaquant-vslm": {
      "command": {
        "path": "uvx",
        "args": ["zettaquant-vslm-mcp"],
        "env": { "ZQ_API_KEY": "<your api key>" }
      }
    }
  }
}
```

### Windsurf / other MCP hosts

Any host that supports the standard `mcpServers` config shape works — use the same `command` + `args` + `env` block as above.

---

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `ZQ_API_KEY` | Yes | — | Your ZettaQuant API key. Must have the `vslm` scope. |
| `ZQ_BASE_URL` | | `https://api.zettaquant.ai` | Override for staging or a private gateway. |

---

## Usage examples in the LLM

Once installed, just ask naturally. Some prompts that will trigger `vslm_predict`:

- *"Here are 40 sentences from Apple's Q3 earnings call. Pull out the ones about AI capex plans."*
- *"Filter these log lines down to anything related to lateral movement."*
- *"I pasted a 10-K risk section. Only show me sentences about supply-chain exposure."*

The model calls `vslm_predict` under the hood, gets back the relevant sentences, and works from those — cheaper and more precise than reading the full input.

---

## Development

```bash
uv venv
uv pip install -e .
export ZQ_API_KEY="..."
python -m zettaquant_vslm_mcp
```

The server speaks JSON-RPC on stdin/stdout. To poke it manually, use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
npx @modelcontextprotocol/inspector uvx zettaquant-vslm-mcp
```

---

## Troubleshooting

- **"ZQ_API_KEY is not set"** in the host logs → the `env` block in your MCP config didn't propagate. Confirm the config file path and restart the host.
- **401 in tool output** → key is valid but wrong. Try it directly: `curl -H "x-api-key: $ZQ_API_KEY" https://api.zettaquant.ai/v1/usage/me`.
- **`ZettaQuant access denied (403)`** → your key doesn't have the `vslm` scope. Contact ZettaQuant.
- **`ZettaQuant quota exceeded (429)`** → you hit your per-period cap; the error message includes the reset time.

---

## License

MIT.
