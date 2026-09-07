# 🦈 Sharkyo

**Shark, yo. Operate the system.**

Sharkyo is a minimalist terminal AI agent that operates your local machine — fast. No planning phases, no bloated context loading, no fluff. You say what you need, it runs it.

```
~/Projects $ sharkyo summarize git log this week
```
Done in 3 seconds.

---

## Why Sharkyo

Most CLI agents are built for complex coding tasks — they load your repo, plan ahead, reason in steps. That overhead makes sense for what they do.

Sharkyo doesn't do that. It's built for **local OS operations**: run a command, get the result, move on. The architecture is deliberately flat: one prompt → one LLM call → one tool → done.

For tasks where the command is obvious and you just need it executed and presented well, that's where Sharkyo wins.

---

## Install

```bash
git clone https://github.com/bayusetiawan42/sharkyo.git
cd sharkyo
pip install .
```

Set your API key:

```bash
sharkyo --add-key gsk_XXXX
```

Run:

```bash
sharkyo
```

---

## Tools

Sharkyo has four tools. That's it.

| Tool | What it does |
|---|---|
| `CMD` | Runs a shell command on your machine. Output streams live; always asks for confirmation first. |
| `KNOWLEDGE` | Stores and recalls persistent facts about you across sessions. |
| `SKILL` | Looks up internal guides for tasks that need specific execution steps. |
| `QUESTIONARY` | Asks you interactive questions when a request needs clarification before acting. |

No web search. No file indexing. No repo crawling. If you need the web, `CMD` with `curl` works fine.

---

## Usage examples

```bash
sharkyo compress all videos in this folder
sharkyo find files larger than 100MB and append to note.txt
sharkyo summarize git log from this week
sharkyo setup a new python project
sharkyo clean up old logs and cache
sharkyo run tests and show me what failed
```

For ambiguous requests, Sharkyo will ask you what it needs via interactive prompt before running anything.

---

## Memory

Sharkyo remembers things between sessions via the `KNOWLEDGE` tool. It stores facts like your preferred project directory, tools you use, or anything it notices you repeat. Next session, it already knows.

You can also tell it directly:

```
sharkyo ingat bahwa project ku ada di ~/dev dan aku pakai pnpm
```

---

## Config

Sharkyo reads `~/.sharkyorc` on startup. All fields are optional.

```
# ~/.sharkyorc

model        = openai/gpt-oss-120b
max_history  = 12
max_tokens   = 512
temperature  = 0.7
cmd_out_chars = 3000
cmd_timeout   = 0
```

Supports `key = value`, `key: value`, or `set key value` syntax. Lines starting with `#` are ignored.

---

## Safety

Every shell command is shown to you before it runs. You confirm or cancel. Sharkyo never executes anything silently.

```
  ! Wants to run: rm -rf ./dist

  ? Run it?
   > Yes
     No
```
