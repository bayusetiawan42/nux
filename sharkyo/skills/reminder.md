# Linux Desktop Reminder & Timer

Use this skill when the user asks to be reminded, alerted, or set a timer for a specific duration or task.

## Execution Strategy

On Linux desktop environments, reminders can be triggered via standard desktop notifications using `notify-send` combined with a backgrounded `sleep`.

### Command Structure

Always run the command asynchronously in the background so it never blocks the terminal:

```bash
(sleep <SECONDS> && notify-send -u normal "Sharkyo Reminder" "<MESSAGE>") >/dev/null 2>&1 &
```

### Important Parameters:
- **Delay in Seconds**:
  - Convert the user's requested time to seconds:
    - 30 seconds $\rightarrow$ `30`
    - 5 minutes $\rightarrow$ `300`
    - 15 minutes $\rightarrow$ `900`
    - 1 hour $\rightarrow$ `3600`
- **Tool Parameters**:
  - When invoking `CMD`, set `review_output: false` because this is an asynchronous background process and there is no output to wait for.
- **Confirmation Reply**:
  - After scheduling the command, inform the user casually that the reminder has been set for that duration.

### Example:
- **User Prompt**: "ingatkan aku 10 menit lagi buat minum air"
- **Tool Call**:
  ```json
  {
    "name": "CMD",
    "arguments": {
      "command": "(sleep 600 && notify-send -u normal \"Sharkyo Reminder\" \"Waktunya minum air!\") >/dev/null 2>&1 &",
      "review_output": false
    }
  }
  ```
- **Assistant Response**: "Siap! Pengingat buat minum air sudah diset untuk 10 menit ke depan."
