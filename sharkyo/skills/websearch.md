# Web Search & Page Reading

Use this skill when the user asks for information that requires searching the internet.

## Tool Workflow

Always follow this two-step pattern for web research:

### Step 1 — Search
Call `WEBSEARCH` with a concise keyword query to get a list of results (titles, URLs, snippets).

### Step 2 — Read
If the snippet is not enough to answer the user's question, call `WEBFETCH` with the most relevant URL from the search results to read the full page content as clean text.

## Tool Parameters

### WEBSEARCH
```json
{
  "name": "WEBSEARCH",
  "arguments": {
    "query": "concise keywords here",
    "max_results": 5
  }
}
```

### WEBFETCH
```json
{
  "name": "WEBFETCH",
  "arguments": {
    "url": "https://example.com/page"
  }
}
```

## Rules

- **NEVER use CMD with curl, wget, or any HTTP command to fetch web pages.** Always use `WEBFETCH` instead — it returns clean readable text, not raw HTML.
- If the first WEBFETCH result doesn't have the info, try the next URL from WEBSEARCH results.
- Do not fabricate or guess information — if nothing found after searching, say so honestly.
- For factual queries about people, places, or events: WEBSEARCH → pick best URL → WEBFETCH → answer.

## Example

**User:** "Arsenal menang nggak tadi malam?"

1. Call `WEBSEARCH(query="Arsenal match result last night")`
2. Get results with URLs
3. Call `WEBFETCH(url="<most relevant result URL>")`
4. Read clean page text and summarize the answer
