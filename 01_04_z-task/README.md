# 01_04_z-task

Python agent application with dynamic MCP tool discovery and a native vision tool for image-based documents.

## What it does

1. Loads MCP server configuration from `mcp.json`
2. Connects to the configured server over stdio
3. Downloads the live MCP tool list for the agent automatically
4. Adds native tools, including `understand_image` for image analysis
5. Runs an autonomous Responses API loop until the task is complete

## Requirements

1. Create `.env` in the repo root based on `env.example`
2. Set one AI key: `OPENAI_API_KEY` or `OPENROUTER_API_KEY`
3. If you use OpenRouter, optionally set `AI_PROVIDER=openrouter`
4. Install Python dependencies from the repo root:

```bash
pip install -r requirements.txt
```

## Run

From the repo root:

```bash
python 01_04_z-task/app.py
```

With a custom query:

```bash
python 01_04_z-task/app.py --query "Read the task materials and prepare the final shipment decision."
```

With a different MCP server from `mcp.json`:

```bash
python 01_04_z-task/app.py --server files
```

## Native tool

`understand_image`

- accepts a path relative to `01_04_z-task`
- reads local image files
- sends them to the model as image input
- works well for scans, screenshots, tables, forms and other document images

## Notes

- MCP tools are not hardcoded. The agent pulls them from the connected server at startup.
- The default prompt is task-oriented, but you can replace it with `--query` at runtime.
