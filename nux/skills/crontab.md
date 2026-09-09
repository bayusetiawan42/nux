# Cron Jobs and Scheduled Tasks

Use this skill when the user wants to schedule a recurring task, add a cron job, list existing crons, or remove a scheduled task.

## Execution Strategy

Use `crontab` for user-level cron jobs. Never touch `/etc/crontab` unless the user explicitly asks for a system cron.

### View current crontab

```bash
crontab -l 2>/dev/null || echo "No crontab set"
```

### Add a new cron job (preserving existing ones)

```bash
(crontab -l 2>/dev/null; echo "<CRON_SCHEDULE> <COMMAND>") | crontab -
```

### Remove a specific cron job (by matching pattern)

```bash
crontab -l 2>/dev/null | grep -v '<PATTERN>' | crontab -
```

### Clear all cron jobs

```bash
crontab -r
```

## Cron Schedule Reference

| Expression | Meaning |
|------------|---------|
| `* * * * *` | Every minute |
| `0 * * * *` | Every hour |
| `0 9 * * *` | Every day at 9:00 AM |
| `0 9 * * 1` | Every Monday at 9:00 AM |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `*/15 * * * *` | Every 15 minutes |
| `0 0 1 * *` | First of every month at midnight |
| `@reboot` | Once at system startup |
| `@hourly` | Every hour (same as `0 * * * *`) |
| `@daily` | Every day at midnight |

## Parameters

- Always redirect cron output to avoid silent failures: append `>> /tmp/<JOBNAME>.log 2>&1` to cron commands.
- Use `review_output: true` after add/remove to confirm the crontab looks correct.
- If the command uses paths, use absolute paths inside cron (cron runs with a minimal PATH).
- Ask for clarification via QUESTIONARY if the schedule is ambiguous.

## Example

- **User**: "run /home/bayu/scripts/backup.sh every day at 2 AM"
- **Tool Call**:
  ```json
  {
    "name": "CMD",
    "arguments": {
      "command": "(crontab -l 2>/dev/null; echo '0 2 * * * /home/bayu/scripts/backup.sh >> /tmp/backup.log 2>&1') | crontab - && crontab -l",
      "review_output": true
    }
  }
  ```
