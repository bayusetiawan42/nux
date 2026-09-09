# tools/file.py
# File read, write, and edit tools.

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import questionary

from nux.tools import register_tool
from nux.tools.result import ToolResult
from nux.ui.display import (
    QUESTIONARY_STYLE_SPEC,
    console,
    is_interactive,
    print_info,
    print_success,
    show_diff,
    show_file_preview,
)

if TYPE_CHECKING:
    from nux.server.daemon import Session

FILE_READ_SCHEMA = {
    "type": "function",
    "function": {
        "name": "FILE_READ",
        "description": (
            "Read the contents of a file and return it with line numbers. "
            "Supports offset and limit for reading specific sections. "
            "Use this to inspect files before editing them."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file.",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed). Default: 1.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to return. Default: unspecified, auto-adjusted by system.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
}

FILE_WRITE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "FILE_WRITE",
        "description": (
            "Write content to a file. Creates parent directories if needed. "
            "If the file already exists, shows a diff and asks for confirmation. "
            "For new files, shows a preview and asks for confirmation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file.",
                },
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
}

FILE_EDIT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "FILE_EDIT",
        "description": (
            "Edit a file by replacing exact text with new text. "
            "Shows a colored diff of the changes and asks for confirmation before applying. "
            "Use FILE_READ first to see the file contents, then use this to make precise edits."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file.",
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact text to find and replace. Must match exactly including whitespace and indentation.",
                },
                "new_string": {
                    "type": "string",
                    "description": "The replacement text. Use empty string to delete the old_string.",
                },
            },
            "required": ["path", "old_string", "new_string"],
            "additionalProperties": False,
        },
    },
}

SCHEMAS = {
    "FILE_READ": FILE_READ_SCHEMA,
    "FILE_WRITE": FILE_WRITE_SCHEMA,
    "FILE_EDIT": FILE_EDIT_SCHEMA,
}

_CONFIRM_STYLE = questionary.Style(QUESTIONARY_STYLE_SPEC)


def _resolve_path(path: str, cwd: str | None = None) -> str:
    if os.path.isabs(path):
        return path
    base = cwd or os.getcwd()
    return os.path.normpath(os.path.join(base, path))


def _confirm(message: str) -> bool:
    if not is_interactive():
        console.print(
            "  [dim](warning: terminal is not interactive, applying without confirmation)[/dim]"
        )
        return True
    answer = questionary.select(
        message,
        choices=["Yes", "No"],
        style=_CONFIRM_STYLE,
    ).ask()
    return answer == "Yes"


@dataclass
class FileReadArgs:
    path: str
    offset: int = 1
    limit: int = 2000

    @classmethod
    def from_dict(cls, args: dict) -> FileReadArgs:
        return cls(
            path=args.get("path", ""),
            offset=max(1, args.get("offset") or 1),
            limit=max(1, args.get("limit") or 2000),
        )


@dataclass
class FileWriteArgs:
    path: str
    content: str

    @classmethod
    def from_dict(cls, args: dict) -> FileWriteArgs:
        return cls(
            path=args.get("path") or "",
            content=args.get("content") or "",
        )


@dataclass
class FileEditArgs:
    path: str
    old_string: str
    new_string: str

    @classmethod
    def from_dict(cls, args: dict) -> FileEditArgs:
        return cls(
            path=args.get("path") or "",
            old_string=args.get("old_string") or "",
            new_string=args.get("new_string") or "",
        )


@register_tool("FILE_READ")
def execute_read(args: dict, session: Session) -> ToolResult:
    parsed = FileReadArgs.from_dict(args)

    if not parsed.limit:
        parsed.limit = session.max_textlen_tokens

    if not parsed.path:
        return ToolResult(output="Error: 'path' is required.", should_continue=True)

    resolved = _resolve_path(parsed.path, session.packet.cwd)

    if not os.path.isfile(resolved):
        return ToolResult(
            output=f"Error: File not found: {resolved}",
            should_continue=True,
        )

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except OSError as e:
        return ToolResult(
            output=f"Error reading file: {e}",
            should_continue=True,
        )

    total = len(all_lines)
    start = parsed.offset - 1
    end = min(start + parsed.limit, total)
    selected = all_lines[start:end]

    numbered = []
    for i, line in enumerate(selected, start=start + 1):
        stripped = line.rstrip("\n")
        numbered.append(f"{i}: {stripped}")

    header = f"File: {resolved} ({total} lines)"
    if start > 0 or end < total:
        header += f" [showing lines {start + 1}-{end}]"

    output = header + "\n" + "\n".join(numbered)
    print_info(f"Read {resolved} [limit:]")
    return ToolResult(output=output, should_continue=True)


@register_tool("FILE_WRITE")
def execute_write(args: dict, session: Session) -> ToolResult:
    parsed = FileWriteArgs.from_dict(args)

    if not parsed.path:
        return ToolResult(output="Error: 'path' is required.", should_continue=True)

    resolved = _resolve_path(parsed.path, session.packet.cwd)
    exists = os.path.isfile(resolved)

    if session.no_confirm:
        pass
    elif exists:
        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                old_content = f.read()
        except OSError as e:
            return ToolResult(output=f"Error reading existing file: {e}", should_continue=True)

        show_diff(old_content, parsed.content, resolved)
        if not _confirm("Write changes?"):
            print_info("Cancelled.")
            return ToolResult(output="File write cancelled by user.", should_continue=True)
    else:
        show_file_preview(parsed.content, resolved)
        if not _confirm("Create this file?"):
            print_info("Cancelled.")
            return ToolResult(output="File write cancelled by user.", should_continue=True)

    try:
        parent = os.path.dirname(resolved)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(parsed.content)
    except OSError as e:
        return ToolResult(output=f"Error writing file: {e}", should_continue=True)

    action = "Updated" if exists else "Created"
    print_success(f"{action}: {resolved}")
    return ToolResult(
        output=f"{action} {resolved} ({len(parsed.content)} chars)",
        should_continue=True,
    )


@register_tool("FILE_EDIT")
def execute_edit(args: dict, session: Session) -> ToolResult:
    parsed = FileEditArgs.from_dict(args)

    if not parsed.path:
        return ToolResult(output="Error: 'path' is required.", should_continue=True)
    if not parsed.old_string:
        return ToolResult(output="Error: 'old_string' is required.", should_continue=True)

    resolved = _resolve_path(parsed.path, session.packet.cwd)

    if not os.path.isfile(resolved):
        return ToolResult(
            output=f"Error: File not found: {resolved}",
            should_continue=True,
        )

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError as e:
        return ToolResult(output=f"Error reading file: {e}", should_continue=True)

    count = content.count(parsed.old_string)
    if count == 0:
        return ToolResult(
            output=(
                f"Error: old_string not found in {resolved}. "
                "Use FILE_READ to see the exact file contents."
            ),
            should_continue=True,
        )
    if count > 1:
        return ToolResult(
            output=(
                f"Error: old_string found {count} times in {resolved}. "
                "Provide more context to make the match unique."
            ),
            should_continue=True,
        )

    new_content = content.replace(parsed.old_string, parsed.new_string, 1)

    if session.no_confirm:
        pass
    else:
        show_diff(content, new_content, resolved)
        if not _confirm("Apply changes?"):
            print_info("Cancelled.")
            return ToolResult(output="File edit cancelled by user.", should_continue=True)

    try:
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(new_content)
    except OSError as e:
        return ToolResult(output=f"Error writing file: {e}", should_continue=True)

    print_success(f"Edited: {resolved}")
    return ToolResult(
        output=f"Edited {resolved} successfully.",
        should_continue=True,
    )
