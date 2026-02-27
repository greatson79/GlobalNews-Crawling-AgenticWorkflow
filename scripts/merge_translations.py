#!/usr/bin/env python3
"""Merge translated chunks back into a single document.

Reads the manifest from split_for_translation.py, finds translated chunks,
concatenates in order, and writes the final merged file.

Usage:
    python3 scripts/merge_translations.py \
        --manifest .tmp/translate-chunks/manifest.json \
        --output research/site-reconnaissance.ko.md \
        --project-dir .

JSON result to stdout.
"""

import argparse
import json
import os
import sys


def merge_chunks(manifest_path, output_path):
    """Merge translated chunks into final document.

    For each chunk in the manifest, looks for the translated version:
    - chunk-00.ko.md (preferred)
    - chunk-00-translated.md (fallback)

    Returns result dict.
    """
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    chunks = manifest.get("chunks", [])
    if not chunks:
        return {"valid": False, "error": "No chunks in manifest"}

    # Single-chunk strategy: translation should be at the output path already
    if manifest.get("strategy") == "single":
        return {
            "valid": True,
            "strategy": "single",
            "message": "Single chunk — no merge needed",
        }

    merged_parts = []
    missing = []
    chunk_dir = manifest.get("output_dir", os.path.dirname(manifest_path))

    for chunk in chunks:
        chunk_id = chunk["id"]
        chunk_file = chunk["file"]
        base = os.path.splitext(chunk_file)[0]

        # Try multiple naming conventions for translated chunks
        candidates = [
            f"{base}.ko.md",
            f"{base}-translated.md",
            f"{base}-ko.md",
            os.path.join(chunk_dir, f"chunk-{chunk_id:02d}.ko.md"),
            os.path.join(chunk_dir, f"chunk-{chunk_id:02d}-translated.md"),
        ]

        found = None
        for candidate in candidates:
            if os.path.exists(candidate):
                found = candidate
                break

        if found:
            with open(found, "r", encoding="utf-8") as f:
                content = f.read()
            merged_parts.append(content.rstrip())
        else:
            missing.append(f"chunk-{chunk_id:02d}")

    if missing:
        return {
            "valid": False,
            "error": f"Missing translated chunks: {missing}",
            "found": len(chunks) - len(missing),
            "total": len(chunks),
        }

    # Merge with double newline separator
    merged_content = "\n\n".join(merged_parts) + "\n"

    # Write output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(merged_content)

    output_size = os.path.getsize(output_path)
    output_lines = merged_content.count("\n") + 1

    return {
        "valid": True,
        "strategy": "multi",
        "chunks_merged": len(chunks),
        "output_path": output_path,
        "output_size_bytes": output_size,
        "output_lines": output_lines,
    }


def main():
    parser = argparse.ArgumentParser(description="Merge translated chunks")
    parser.add_argument("--manifest", required=True, help="Manifest JSON path")
    parser.add_argument("--output", required=True, help="Output merged file path")
    parser.add_argument("--project-dir", default=".", help="Project root")
    args = parser.parse_args()

    manifest_path = (args.manifest if os.path.isabs(args.manifest)
                     else os.path.join(args.project_dir, args.manifest))
    output_path = (args.output if os.path.isabs(args.output)
                   else os.path.join(args.project_dir, args.output))

    result = merge_chunks(manifest_path, output_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
