import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("cPanel")

CPANEL_HOST = os.getenv("CPANEL_HOST")          # e.g. https://yourdomain.com:2083
CPANEL_USER = os.getenv("CPANEL_USER")
CPANEL_TOKEN = os.getenv("CPANEL_TOKEN")         # cPanel API token (recommended over password)


def auth_headers() -> dict:
    return {"Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}"}


async def uapi(module: str, func: str, params: dict = None) -> dict:
    url = f"{CPANEL_HOST}/execute/{module}/{func}"
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        resp = await client.get(url, headers=auth_headers(), params=params or {})
        resp.raise_for_status()
    data = resp.json()
    if data.get("status") == 0:
        errors = data.get("errors") or ["Unknown error"]
        raise RuntimeError("; ".join(errors))
    return data.get("data", data)


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
        accounts.append(f"{acc.get('email', '')} | quota: {acc.get('quota', 'unlimited')} MB | used: {acc.get('diskused', 0)} MB")
    return "\n".join(accounts)


@mcp.tool()
async def create_email_account(email: str, password: str, quota_mb: int = 250) -> str:
    """Create a new email account. email should be full address like user@domain.com."""
    user, domain = email.split("@", 1)
    data = await uapi("Email", "add_pop", {
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


@mcp.tool()
async def list_files(path: str = "/") -> str:
    """List files in a directory on the cPanel account."""
    data = await uapi("Fileman", "list_files", {"path": path, "include_mime": 0})
    if not data:
        return "No files found."
    entries = []
    for f in data:
        ftype = "DIR" if f.get("type") == "dir" else "FILE"
        entries.append(f"[{ftype}] {f.get('file', '')}")
    return "\n".join(entries)


if __name__ == "__main__":
    import uvicorn
    app = mcp.get_asgi_app()
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
