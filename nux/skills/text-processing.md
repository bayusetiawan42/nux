# Text Processing: grep, sed, awk

Use this skill when the user wants to search file contents, find patterns, replace text, extract columns/fields, or transform text output from commands.

## Execution Strategy

Pick the right tool: `grep` for searching/filtering, `sed` for find-replace or line editing, `awk` for column extraction and structured text.

## grep -- Search and Filter

### Search for pattern in file

```bash
grep -n "<PATTERN>" <FILE>
```

### Search recursively in directory

```bash
grep -rn "<PATTERN>" <DIR>
```

### Case-insensitive search

```bash
grep -in "<PATTERN>" <FILE>
```

### Show only matching filenames

```bash
grep -rl "<PATTERN>" <DIR>
```

### Exclude pattern (inverse match)

```bash
grep -v "<PATTERN>" <FILE>
```

### Search with context (N lines before/after)

```bash
grep -n -C 3 "<PATTERN>" <FILE>
```

### Count matches

```bash
grep -c "<PATTERN>" <FILE>
```

## sed -- Find and Replace

### Replace first occurrence per line

```bash
sed 's/<OLD>/<NEW>/' <FILE>
```

### Replace all occurrences (global)

```bash
sed 's/<OLD>/<NEW>/g' <FILE>
```

### Edit file in-place

```bash
sed -i 's/<OLD>/<NEW>/g' <FILE>
```

### Delete lines matching pattern

```bash
sed -i '/<PATTERN>/d' <FILE>
```

### Print specific line range

```bash
sed -n '10,20p' <FILE>
```

## awk -- Column Extraction and Structured Text

### Print specific column (space-delimited)

```bash
awk '{print $<N>}' <FILE>
```

### Print multiple columns

```bash
awk '{print $1, $3}' <FILE>
```

### Filter rows by column value

```bash
awk '$<N> == "<VALUE>"' <FILE>
```

### Sum a numeric column

```bash
awk '{sum += $<N>} END {print sum}' <FILE>
```

### CSV: print specific column (comma-delimited)

```bash
awk -F',' '{print $<N>}' <FILE>
```

## Parameters

- Replace `<PATTERN>`, `<FILE>`, `<DIR>`, `<OLD>`, `<NEW>`, `<N>` as needed.
- For `sed -i` (in-place): always use `review_output: true` so the model can verify the change worked.
- For grep/awk reads: use `review_output: true` if the output needs interpretation.
- When replacing across many files: run a dry-run with `grep -rl` first to show what would be affected.

## Example

- **User**: "replace all 'localhost' with '0.0.0.0' in config/settings.py"
- **Tool Call**:
  ```json
  {
    "name": "CMD",
    "arguments": {
      "command": "grep -n 'localhost' config/settings.py && sed -i 's/localhost/0.0.0.0/g' config/settings.py && echo 'Done' && grep -n '0.0.0.0' config/settings.py",
      "review_output": true
    }
  }
  ```
