# TODO

## --adjust flag (Interactive Auto-Adjustment)

The `--adjust` flag performs interactive auto-adjustment of configuration based on model capabilities and tier.

### Workflow
1. List available models via Groq API (`client.models.list()`)
2. Score models based on:
   - Free tier vs pay tier
   - Context window size
   - Max completion tokens
   - Tool calling support
   - Reasoning capabilities
3. Interactive prompt for user to select a model
4. Auto-adjust config settings based on selected model:
   - `model` — model ID
   - `max_history` — adjust to match context window
   - `max_completion_tokens` — adjust to match model's max completion tokens
   - `reasoning_effort` — enable if model supports reasoning
   - `service_tier` — suggest tier based on free/pay
   - `temperature` — default or custom

### Implementation
- Location: `sharkyo/core/adjust.py` (new module)
- CLI: `sharkyo --adjust` or `sharkyo command adjust`
- Output: update `~/.sharkyorc` automatically
- Display summary of changes before applying

### Example Output
```
Detected 8 available models:
  [1] llama-3.3-70b-versatile    (free, 128k ctx, 32k out, reasoning)
  [2] llama-3.1-8b-instant       (free, 131k ctx, 8k out)
  [3] openai/gpt-oss-20b         (free, 20k ctx, 8k out)
  ...

Select model [1]: 1

Applied settings:
  model               = llama-3.3-70b-versatile
  max_history          = 24 (was 12)
  max_completion_tokens = 4096 (was 512)
  reasoning_effort     = default (was null)
  service_tier         = on_demand (was null)
```
