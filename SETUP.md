# ZettaQuant V-SLM MCP — Setup

## 1. Install `uv`

```bash
brew install uv                                        # macOS
curl -LsSf https://astral.sh/uv/install.sh | sh        # macOS / Linux
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows
```

Run `which uvx` and note the full path (e.g. `/opt/homebrew/bin/uvx`) — you'll need it below.

## 2. Get your ZettaQuant API key

Ask your ZettaQuant contact. Test:

```bash
curl -H "x-api-key: YOUR_KEY" https://api.zettaquant.ai/v1/usage/me
```

## 3. Add to your host

Replace `YOUR_KEY` and the `uvx` path with your values.

**Cursor** — `~/.cursor/mcp.json`
**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) · `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "zettaquant-vslm": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["zettaquant-vslm-mcp"],
      "env": { "ZQ_API_KEY": "YOUR_KEY" }
    }
  }
}
```

**Claude Code (CLI)**

```bash
claude mcp add zettaquant-vslm /opt/homebrew/bin/uvx zettaquant-vslm-mcp \
  --env ZQ_API_KEY=YOUR_KEY
```

**Zed** — `~/.config/zed/settings.json`

```json
{
  "context_servers": {
    "zettaquant-vslm": {
      "command": {
        "path": "/opt/homebrew/bin/uvx",
        "args": ["zettaquant-vslm-mcp"],
        "env": { "ZQ_API_KEY": "YOUR_KEY" }
      }
    }
  }
}
```

Restart the host.

## 4. Test

Paste in your host's chat:

> Filter these sentences for rate cut expectations:
> - FOMC signaled openness to rate cuts if inflation continues to soften.
> - The cafeteria menu was updated last week.
> - A 25bp cut in September remains the base case for most participants.

The host should call `vslm_predict` and return only the two rate-cut sentences.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Server shows red / "connection failed" | Wrong `command` path. Use the output of `which uvx`. |
| Crashes on startup / `No module named 'mcp.server.fastmcp'` | Stale cached build. Refresh with `uvx --refresh zettaquant-vslm-mcp` (needs ≥ 0.1.1). |
| `ZettaQuant auth failed (401)` | Wrong / expired key. Retest with the curl above. |
| `ZettaQuant plan not active (402)` | Your ZettaQuant plan is inactive — contact ZettaQuant. |
| `ZettaQuant access denied (403)` | Your key lacks the `vslm` scope — contact ZettaQuant. |
| `ZettaQuant quota exceeded (429)` | Hit your per-period cap; the reset time is in the error message. |

PyPI: https://pypi.org/project/zettaquant-vslm-mcp/
