# cPanel MCP Server — Team Setup Guide

Connect Claude to your cPanel website so you can manage files, upload images, and edit content directly from Claude Desktop or Claude Code.

---

## Prerequisites

- Mac (or any computer with Python 3.8+)
- Access to the cPanel account credentials (ask Nikki)
- Claude Desktop installed

---

## Step 1 — Clone the Repo

Open Terminal and run:

```bash
git clone https://github.com/NikkiZucaro/cpanel-mcp.git
cd cpanel-mcp
```

---

## Step 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 3 — Add Your cPanel Credentials

Create a file called `.env` inside the `cpanel-mcp` folder with the following:

```
CPANEL_HOST=https://yourdomain.com:2083
CPANEL_USER=your_cpanel_username
CPANEL_TOKEN=your_cpanel_api_token
```

> **Ask Nikki for the correct values.** Never share or commit this file — it's already in `.gitignore`.

---

## Step 4 — Start the Server

In your `cpanel-mcp` folder, double-click **"Start cPanel MCP Server.command"**

You should see:
```
Starting cPanel MCP Server...
INFO: Uvicorn running on http://0.0.0.0:8000
```

> **Keep this window open** while using Claude. Closing it stops the server.

---

## Step 5 — Connect to Claude Desktop

Add the following to your Claude Desktop config file.

**Config file location:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

Open it and add the `mcpServers` block:

```json
{
  "mcpServers": {
    "cpanel": {
      "url": "http://localhost:8000/sse",
      "transport": "sse"
    }
  }
}
```

Then **quit and reopen Claude Desktop**.

---

## Step 6 — Connect to Claude Code (optional)

If you use Claude Code in the terminal, run:

```bash
claude mcp remove cpanel
claude mcp add --transport sse cpanel http://localhost:8000/sse
```

Then restart Claude Code.

---

## What You Can Do

Once connected, you can ask Claude things like:

- *"List the files in my content folder"*
- *"Read the file homepage.html"*
- *"Update the text in about.html to say..."*
- *"Upload this image to /images/banner.jpg"*
- *"Create a new page called services.html"*

All file operations are restricted to `/public_html/content/` for safety.

---

## Troubleshooting

**Server won't start**
- Make sure Python is installed: `python --version`
- Make sure dependencies are installed: `pip install -r requirements.txt`
- Check that your `.env` file exists and has the correct credentials

**Claude can't connect**
- Make sure the server is running (you should see Uvicorn running on port 8000)
- Check the URL in your config is exactly `http://localhost:8000/sse`
- Restart Claude Desktop after making config changes

**Check if the server is running**
```bash
lsof -i :8000
```

---

## Stopping the Server

Close the Terminal window that's running the server, or press `Ctrl+C` inside it.
