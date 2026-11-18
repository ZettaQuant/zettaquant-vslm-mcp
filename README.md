# Kolmo custom decision models MCP (private beta)

Train a private classifier from your own text and label definitions, then classify new text with it from any MCP client. `kolmo-mcp` runs locally over stdio and calls the ZettaQuant API, where training and inference run.

**Access is invitation-only.** [Request access by email](mailto:contact@zettaquant.ai?subject=Kolmo%20custom%20models%20beta%20access) with your account email, organization, use case and expected volume. Once approved, create a **My models: training and inference** key at [API Keys](https://app.zettaquant.ai/keys).

## Setup

Add this to your MCP client's configuration:

```json
{
  "mcpServers": {
    "kolmo-custom-models": {
      "command": "uvx",
      "args": ["--from", "zettaquant-vslm-mcp==0.2.0b1", "kolmo-mcp"],
      "env": { "ZQ_MODEL_API_KEY": "YOUR_APPROVED_KEY" }
    }
  }
}
```

To run from a checkout instead, use `"command": "uv"` with `"args": ["run", "--directory", "/path/to/zettaquant-vslm-mcp", "kolmo-mcp"]`.

## Tools

| Tool | What it does |
|---|---|
| `kolmo_beta_access` | Setup guidance and a prefilled email link to request access. |
| `kolmo_list_models` | Ready models available to your account, with versions and labels. |
| `kolmo_train_model` | Starts training from label definitions and representative text. |
| `kolmo_model_status` | Training progress, or the version of a ready model. |
| `kolmo_cancel_training` | Cancels a training run. |
| `kolmo_classify` | Up to 128 texts; one label, score and probabilities per text. Text longer than the model's 256-token window is split and the pieces are averaged by length. |
| `kolmo_classify_documents` | Long documents; one label per chunk, with character offsets into the original text. |

## Training data

- Supply 2–24 labels, each with an `id` (lowercase, up to 32 characters), a `name` and a `description` that says when it applies. Include an `other` label if some inputs fit none of them.
- Supply at least about 150 distinct, representative text pieces covering every label. The API accepts as few as ten, but that is too few to learn from.
- Give each source document its own `document_id` and keep that document's pieces under it. The API splits long text and holds out whole documents for evaluation.
- A `ready` model can still be poor. Classify held-out examples for every label before relying on it.
- Identical training inputs reuse one idempotency key, so retrying recovers the same run. Pass a new `request_id` to train again on the same data.

## Limits

Requests are capped at 16 MiB. Each training text allows 2,000,000 characters and each `kolmo_classify` text 4,000. Document inference returns at most 128 chunks per call. Beta rate limits apply, and a 429 includes retry guidance when available.

## Access and data handling

The API checks your invitation, key scopes, account state and model ownership on every request. The adapter reads only `ZQ_MODEL_API_KEY`. Keys belong to one user and organization, so use your own. Set `ZQ_MODELS_BASE_URL` only for a trusted HTTPS ZettaQuant deployment; the default is `https://app.zettaquant.ai`.

Submitted text goes to ZettaQuant, and training also sends it to ZettaQuant's labeling providers. Your MCP host may keep tool arguments and results under its own settings. Error messages never include API responses, your key or your text.

A container image is also available: `docker build -f Dockerfile.kolmo -t kolmo-mcp .` then `docker run --rm -i -e ZQ_MODEL_API_KEY kolmo-mcp`.

---

# zettaquant-vslm-mcp (context filtering)

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
python -m zettaquant_vslm_mcp.server
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
