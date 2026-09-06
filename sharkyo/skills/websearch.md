# Web Search & Auto Page Reading

Use this skill when the user asks for current information, facts, news, or to inspect a specific website.

## Behavior

The `WEBSEARCH` tool is a 2-in-1 tool that automatically fetches clean page content in a single call to save tokens and turns:

1. **Direct URL**: If `query` starts with `http://` or `https://`, it directly fetches that page, strips HTML/scripts with BeautifulSoup, and returns clean text.
2. **Search Keywords**: If `query` contains keywords, it searches DuckDuckGo and **automatically fetches the top result's full page content** as clean readable text.

## Tool Invocation

```json
{
  "name": "WEBSEARCH",
  "arguments": {
    "query": "concise keywords or https://example.com"
  }
}
```

## Rules

- **NEVER use CMD with curl, wget, or python requests** to fetch web pages. Always use `WEBSEARCH`.
- Keep keyword queries specific and concise for better top-result relevance (e.g. "profil Suwito DPRD Banyuwangi" instead of general words).
- If the user provides a link directly, pass that link as `query` to `WEBSEARCH`.
- Do not hallucinate or guess — base your response strictly on the retrieved page content.
