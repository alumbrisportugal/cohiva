#!/usr/bin/env python3
"""Check PWA translation keys, string values and interpolation variables.

Run: python3 alumbris/check_pwa_i18n.py
No third-party dependencies required.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1] / "pwa" / "src" / "i18n"
BASE = ROOT / "en-US" / "index.ts"
TARGET = ROOT / "pt-PT" / "index.ts"
# The catalog follows a nested object literal with literal string values.
KEY = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]*):\s*(?:\{|'|\"|$)")
PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z_0-9]*\}")


def read_catalog(path: pathlib.Path) -> tuple[set[str], dict[str, set[str]]]:
    content = path.read_text(encoding="utf-8")
    stack: list[str] = []
    keys: set[str] = set()
    interpolations: dict[str, set[str]] = {}
    # This is a lightweight structural sanity check, NOT a TS parser.
    # A complete syntax/type check is performed by the upstream Yarn build.
    for line in content.splitlines():
        stripped = line.strip()
        match = KEY.match(line)
        if match:
            key = match.group(1)
            is_object = stripped.endswith("{")
            path_key = ".".join(stack + [key])
            if is_object:
                stack.append(key)
            else:
                keys.add(path_key)
                interpolations[path_key] = set(PLACEHOLDER.findall(stripped))
        if stripped in ("},", "}") and stack:
            stack.pop()
    return keys, interpolations


def main() -> int:
    original_keys, original_vars = read_catalog(BASE)
    translated_keys, translated_vars = read_catalog(TARGET)
    missing = sorted(original_keys - translated_keys)
    extra = sorted(translated_keys - original_keys)
    different = sorted(
        key for key in original_keys & translated_keys
        if original_vars[key] != translated_vars[key]
    )
    print(f"en-US keys: {len(original_keys)}; pt-PT keys: {len(translated_keys)}")
    for title, values in (("Missing keys", missing), ("Extra keys", extra), ("Mismatched interpolation", different)):
        if values:
            print(f"{title}: " + ", ".join(values))
    if missing or extra or different:
        return 1
    print("PWA pt-PT structural check passed. Run yarn check/build for syntax and runtime validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
