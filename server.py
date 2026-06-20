import asyncio
import os
from typing import Any
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP


SERVER_HOST = os.getenv("HOST")
if not SERVER_HOST:
    SERVER_HOST = "0.0.0.0" if os.getenv("RENDER") or os.getenv("PORT") else "127.0.0.1"
SERVER_PORT = int(os.getenv("PORT", "8000"))

mcp = FastMCP(
    "wiki-summary",
    host=SERVER_HOST,
    port=SERVER_PORT,
    stateless_http=True,
    json_response=True,
)

USER_AGENT = os.getenv(
    "WIKI_USER_AGENT",
    "WikiSummaryMCP/1.0 (contact: example@email.com)",
)
HEADERS = {"User-Agent": USER_AGENT, "Api-User-Agent": USER_AGENT}
SUPPORTED_LANGS = {"ko", "en"}


async def _search_titles(
    client: httpx.AsyncClient,
    query: str,
    lang: str,
    limit: int,
) -> list[str]:
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params: dict[str, Any] = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
        "utf8": 1,
    }

    response = await client.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    return [
        item["title"]
        for item in data.get("query", {}).get("search", [])
        if item.get("title")
    ]


async def _get_summary(
    client: httpx.AsyncClient,
    title: str,
    lang: str,
) -> dict[str, str] | None:
    encoded_title = quote(title, safe="")
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"

    try:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    summary = data.get("extract") or ""
    if not summary.strip():
        return None

    return {
        "title": data.get("title") or title,
        "summary": summary,
        "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
        "thumbnail": data.get("thumbnail", {}).get("source", ""),
    }


def _normalize_lang(lang: str) -> str:
    lang = (lang or "ko").lower().strip()
    return lang if lang in SUPPORTED_LANGS else "ko"


def _normalize_limit(limit: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = 10
    return max(1, min(value, 20))


def _format_markdown(query: str, results: list[dict[str, str]]) -> str:
    if not results:
        return f"# Search results for '{query}'\n\nNo results found."

    lines = [f"# Search results for '{query}' ({len(results)})", ""]
    for index, item in enumerate(results, 1):
        lines.extend(
            [
                f"## {index}. {item['title']}",
                item["summary"],
            ]
        )
        if item.get("url"):
            lines.append(f"[Read on Wikipedia]({item['url']})")
        if item.get("thumbnail"):
            lines.append(f"Thumbnail: {item['thumbnail']}")
        lines.append("")

    return "\n".join(lines).strip()


@mcp.tool()
async def wiki_search_summary(query: str, lang: str = "ko", limit: int = 10) -> str:
    """Search Wikipedia and return summaries for related pages."""
    query = (query or "").strip()
    if not query:
        return "Please provide a search query."

    lang = _normalize_lang(lang)
    limit = _normalize_limit(limit)

    async with httpx.AsyncClient(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
        try:
            titles = await _search_titles(client, query, lang, limit)
        except (httpx.HTTPError, ValueError):
            return "An error occurred while searching Wikipedia. Please try again later."

        if not titles:
            return f"# Search results for '{query}'\n\nNo results found."

        tasks = [_get_summary(client, title, lang) for title in titles]
        summaries = await asyncio.gather(*tasks)
        results = [item for item in summaries if item]

    return _format_markdown(query, results)


def _default_transport() -> str:
    if os.getenv("MCP_TRANSPORT"):
        return os.getenv("MCP_TRANSPORT", "stdio")
    if os.getenv("RENDER") or os.getenv("PORT"):
        return "streamable-http"
    return "stdio"


if __name__ == "__main__":
    transport = _default_transport()

    if transport == "streamable-http":
        mcp.run(transport="streamable-http")
    elif transport == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run()
