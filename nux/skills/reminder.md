# Desktop Reminder and Timer

Use this skill when the user asks to be reminded, alerted, or set a timer for a specific duration or task.

## Execution Strategy

On Linux desktop environments, reminders are triggered via standard desktop notifications using `notify-send` combined with a backgrounded `sleep`.

### Command Structure

Always run the command asynchronously in the background so it never blocks the terminal:

```bash
(sleep <SECONDS> && notify-send -u normal "Sharkyo Reminder" "<MESSAGE>") >/dev/null 2>&1 &
```

### Time Conversion

Convert the user's requested time to seconds:

| Input | Seconds |
|-------|---------|
| 30 seconds | `30` |
| 5 minutes | `300` |
| 15 minutes | `900` |
| 1 hour | `3600` |

### Parameters

- Set `review_output: false` because this is an asynchronous background process with no output to wait for.
- After scheduling, inform the user that the reminder has been set.

## Example

- **User**: "remind me in 10 minutes to drink water"
- **Tool Call**:
  ```json
  {
    "name": "CMD",
    "arguments": {
      "command": "(sleep 600 && notify-send -u normal \"Sharkyo Reminder\" \"Time to drink water!\") >/dev/null 2>&1 &",
      "review_output": false
    }
  }
  ```
- **Assistant Response**: "Done! Reminder to drink water is set for 10 minutes from now."
