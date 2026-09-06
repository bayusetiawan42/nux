# System Information

Use this skill when the user asks about system specs, hardware info, OS version, CPU, RAM, uptime, or any machine/environment details.

## Execution Strategy

Combine relevant commands into a single shell call to minimize round-trips. Use `review_output: true` so the model can present the info clearly.

### Full system overview

```bash
echo "=== OS ===" && cat /etc/os-release | grep PRETTY_NAME && \
echo "=== Kernel ===" && uname -r && \
echo "=== CPU ===" && grep 'model name' /proc/cpuinfo | head -1 && nproc && \
echo "=== RAM ===" && free -h && \
echo "=== Disk ===" && df -h --total | tail -1 && \
echo "=== Uptime ===" && uptime -p
```

### CPU details

```bash
lscpu | grep -E 'Model name|Socket|Thread|Core|MHz|Cache'
```

### RAM details

```bash
free -h && echo "" && cat /proc/meminfo | grep -E 'MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree'
```

### GPU info

```bash
lspci | grep -i vga && nvidia-smi 2>/dev/null || echo "no nvidia-smi"
```

### Storage devices

```bash
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE
```

### Temperature sensors

```bash
sensors 2>/dev/null || cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | awk '{print $1/1000 "°C"}'
```

### Parameters

- Always use `review_output: true` — the model should summarize and present this info conversationally, not just dump it.
- Combine commands with `&&` and `echo "=== SECTION ==="` headers for readable output.

### Example

- **User**: "specs mesin ini apa aja"
- **Tool Call**:
  ```json
  {
    "name": "CMD",
    "arguments": {
      "command": "echo '=== OS ===' && cat /etc/os-release | grep PRETTY_NAME && echo '=== CPU ===' && grep 'model name' /proc/cpuinfo | head -1 && nproc && echo '=== RAM ===' && free -h && echo '=== Disk ===' && df -h --total | tail -1 && echo '=== Uptime ===' && uptime -p",
      "review_output": true
    }
  }
  ```
