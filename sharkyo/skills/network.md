# Network Diagnostics

Use this skill when the user wants to check connectivity, ping a host, test a port, check IP, inspect network interfaces, or diagnose network issues.

## Execution Strategy

Pick the right tool for the job. Don't run multiple checks at once — run the most relevant one first, then follow up based on what the user needs.

### Check public IP

```bash
curl -s https://ipinfo.io/ip
```

### Check local IP and interfaces

```bash
ip addr show | grep -E 'inet |^[0-9]'
```

### Ping a host (limited count)

```bash
ping -c 4 <HOST>
```

### Check if a TCP port is open

```bash
nc -zv <HOST> <PORT> 2>&1
```

### Trace route to a host

```bash
traceroute <HOST>
```

### Check DNS resolution

```bash
nslookup <HOST>
# or
dig <HOST> +short
```

### Test HTTP response from a URL

```bash
curl -o /dev/null -sw "HTTP %{http_code} | %{time_total}s | %{size_download} bytes\n" <URL>
```

### Check all listening ports

```bash
ss -tlnp
```

### Check current connections

```bash
ss -tp
```

### Parameters

- Replace `<HOST>` with the hostname or IP (e.g. `google.com`, `192.168.1.1`).
- Replace `<PORT>` with the port number.
- Use `review_output: true` for diagnostics commands so the model can interpret results.
- For `ping` and `traceroute`, always use `-c 4` or similar to avoid infinite output.

### Example

- **User**: "cek apakah port 443 di api.example.com terbuka"
- **Tool Call**:
  ```json
  {
    "name": "CMD",
    "arguments": {
      "command": "nc -zv api.example.com 443 2>&1",
      "review_output": true
    }
  }
  ```
