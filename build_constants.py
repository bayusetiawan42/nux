# build_constants.py
# Code generation script: embeds .txt files into _generated_constants.py
# Run this script before packaging, or hook it into setup via build_meta.
# This eliminates runtime File I/O for static text constants.

import pathlib
import textwrap

_SKILLS_DIR = pathlib.Path("sharkyo/skills")
_OUT_FILE = pathlib.Path("sharkyo/_generated_constants.py")

_EMBED_FILES = {
    "SYSTEM_PROMPT": _SKILLS_DIR / "system_prompt.txt",
}

def build() -> None:
    lines = [
        "# AUTO-GENERATED — do not edit by hand.",
        "# Re-run build_constants.py to regenerate.",
        "# Source: sharkyo/skills/system_prompt.txt",
        "",
    ]

    for var_name, file_path in _EMBED_FILES.items():
        content = file_path.read_text(encoding="utf-8").rstrip()
        # Use repr() so any special chars are safely escaped
        lines.append(f"{var_name}: str = {repr(content)}")
        lines.append("")

    _OUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {_OUT_FILE}")

if __name__ == "__main__":
    build()
