import os
import base64
from pathlib import PurePosixPath

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("cPanel")

CPANEL_HOST = os.getenv("CPANEL_HOST")          # e.g. https://yourdomain.com:2083
CPANEL_USER = os.getenv("CPANEL_USER")
CPANEL_TOKEN = os.getenv("CPANEL_TOKEN")        # cPanel API token (recommended)


def auth_headers() -> dict:
    return {"Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}"}


async def uapi(module: str, func: str, params: dict = None) -> dict:
    """
    Call cPanel UAPI.
    Uses GET with query params, which works for most read/write operations.
    """
    url = f"{CPANEL_HOST}/execute/{module}/{func}"
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        resp = await client.get(url, headers=auth_headers(), params=params or {})
        resp.raise_for_status()
    data = resp.json()
    if data.get("status") == 0:
        errors = data.get("errors") or ["Unknown error"]
        raise RuntimeError("; ".join(errors))
    return data.get("data", data)


# ---------- PATH RESTRICTION FOR WEBSITE CONTENT ----------

CONTENT_ROOT = PurePosixPath("/public_html/content")


def safe_content_path(path: str) -> str:
    """
    Restrict all file operations to /public_html/content.
    `path` is treated as relative to that directory.
    """
    # Treat incoming path as relative (even if user passes leading /)
    rel = PurePosixPath(path.lstrip("/"))
    # Prevent .. traversal
    normalized = PurePosixPath("/")
    for part in rel.parts:
        if part in ("", ".", ".."):
            continue
        normalized /= part
    full = CONTENT_ROOT / normalized.relative_to("/")
    return str(full)


# ---------- EXISTING ADMIN TOOLS ----------

@mcp.tool()
async def list_domains() -> str:
    """List all domains on the cPanel account."""
    data = await uapi("DomainInfo", "list_domains")
    lines = []
    for d in data.get("sub_domains", []) + [{"domain": data.get("main_domain")}]:
        if d.get("domain"):
            lines.append(d["domain"])
    return "\n".join(lines) if lines else "No domains found."


@mcp.tool()
async def list_email_accounts() -> str:
    """List all email accounts on the cPanel account."""
    data = await uapi("Email", "list_pops")
    if not data:
        return "No email accounts found."
    accounts = []
    for acc in data:
        accounts.append(
            f"{acc.get('email', '')} | quota: {acc.get('quota', 'unlimited')} MB | "
            f"used: {acc.get('diskused', 0)} MB"
        )
    return "\n".join(accounts)


@mcp.tool()
async def create_email_account(email: str, password: str, quota_mb: int = 250) -> str:
    """Create a new email account. email should be full address like user@domain.com."""
    user, domain = email.split("@", 1)
    await uapi("Email", "add_pop", {
        "email": user,
        "domain": domain,
        "password": password,
        "quota": quota_mb,
    })
    return f"Email account {email} created successfully."


@mcp.tool()
async def delete_email_account(email: str) -> str:
    """Delete an email account."""
    user, domain = email.split("@", 1)
    await uapi("Email", "delete_pop", {"email": user, "domain": domain})
    return f"Email account {email} deleted."


@mcp.tool()
async def list_databases() -> str:
    """List all MySQL databases on the cPanel account."""
    data = await uapi("Mysql", "list_databases")
    if not data:
        return "No databases found."
    return "\n".join(db.get("database", "") for db in data)


@mcp.tool()
async def create_database(name: str) -> str:
    """Create a new MySQL database. Name will be prefixed with your cPanel username automatically."""
    await uapi("Mysql", "create_database", {"name": name})
    return f"Database '{name}' created."


@mcp.tool()
async def list_dns_records(domain: str) -> str:
    """List DNS zone records for a domain."""
    data = await uapi("DNS", "parse_zone", {"zone": domain})
    if not data:
        return "No DNS records found."
    records = []
    for r in data:
        records.append(f"{r.get('type','')}\t{r.get('name','')}\t{r.get('record','')}")
    return "\n".join(records)


@mcp.tool()
async def get_disk_usage() -> str:
    """Get disk usage summary for the cPanel account."""
    data = await uapi("Quota", "get_quota_info")
    return (
        f"Used: {data.get('megabytes_used', '?')} MB / "
        f"Limit: {data.get('megabyte_limit', 'unlimited')} MB"
    )


# ---------- FILE TOOLS (RESTRICTED TO /public_html/content) ----------

@mcp.tool()
async def list_files(path: str = "") -> str:
    """List files in a directory under /public_html/content."""
    full_path = safe_content_path(path)
    data = await uapi("Fileman", "list_files", {"path": full_path, "include_mime": 0})
    if not data:
        return "No files found."
    entries = []
    for f in data:
        ftype = "DIR" if f.get("type") == "dir" else "FILE"
        entries.append(f"[{ftype}] {f.get('file', '')}")
    return "\n".join(entries)


@mcp.tool()
async def read_file(path: str) -> str:
    """Read the contents of a file under /public_html/content."""
    full_path = safe_content_path(path)
    data = await uapi("Fileman", "get_file_content", {"path": full_path})
    return data.get("content", "")


@mcp.tool()
async def write_file(path: str, content: str) -> str:
    """Write or overwrite a text file under /public_html/content."""
    full_path = safe_content_path(path)
    await uapi("Fileman", "save_file_content", {
        "path": full_path,
        "content": content,
    })
    return f"File written: {full_path}"


@mcp.tool()
async def upload_file_base64(path: str, content_base64: str) -> str:
    """
    Upload a file (e.g., image) under /public_html/content from base64-encoded content.
    This uses save_file_content; for binary data we decode and store bytes as-is.
    """
    full_path = safe_content_path(path)
    raw = base64.b64decode(content_base64)
    # Represent bytes as ISO-8859-1 so they round-trip through JSON safely.
    content = raw.decode("latin-1")
    await uapi("Fileman", "save_file_content", {
        "path": full_path,
        "content": content,
    })
    return f"Uploaded file to: {full_path}"


@mcp.tool()
async def delete_file(path: str) -> str:
    """Delete a file under /public_html/content."""
    full_path = safe_content_path(path)
    await uapi("Fileman", "delete", {"path": full_path})
    return f"Deleted file: {full_path}"


@mcp.tool()
async def create_directory(path: str) -> str:
    """Create a directory under /public_html/content."""
    full_path = safe_content_path(path)
    await uapi("Fileman", "mkdir", {"path": full_path})
    return f"Created directory: {full_path}"


if __name__ == "__main__":
    mcp.run(transport="sse")
