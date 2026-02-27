#!/usr/bin/env python3
"""Split a markdown document into chunks for parallel translation.

Splits on heading boundaries, never within code blocks.
Each chunk is sized to stay well under the 32K output token limit
when a translator agent processes it.

Usage:
    python3 scripts/split_for_translation.py \
        --source research/site-reconnaissance.md \
        --output-dir .tmp/translate-chunks \
        --max-lines 350 \
        --project-dir .

JSON manifest output to stdout.
"""

import argparse
import json
import os
import re
import sys


# --- Constants ---
DEFAULT_MAX_LINES = 350  # Safe limit per chunk (~15K tokens output)
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$")
CODE_FENCE_RE = re.compile(r"^```")
MIN_CHUNK_LINES = 20  # Don't create tiny trailing chunks


def _parse_sections(lines):
    """Parse markdown into sections by ## headings.

    Returns list of dicts: {heading_level, heading_text, start_line, end_line, lines}
    Code blocks are tracked to avoid splitting within them.
    """
    sections = []
    current = {"heading_level": 0, "heading_text": "(preamble)", "start_line": 0, "lines": []}
    in_code_block = False

    for i, line in enumerate(lines):
        # Track code fence boundaries
        if CODE_FENCE_RE.match(line):
            in_code_block = not in_code_block
            current["lines"].append(line)
            continue

        if in_code_block:
            current["lines"].append(line)
            continue

        # Check for heading (only split on ## level — top sections)
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) <= 2:  # Split on # and ## only
            # Save current section
            if current["lines"] or sections:  # Don't save empty preamble
                current["end_line"] = i
                sections.append(current)

            current = {
                "heading_level": len(m.group(1)),
                "heading_text": m.group(2).strip(),
                "start_line": i,
                "lines": [line],
            }
        else:
            current["lines"].append(line)

    # Save last section
    current["end_line"] = len(lines)
    sections.append(current)

    return sections


def _group_into_chunks(sections, max_lines):
    """Group sections into chunks, each under max_lines.

    Greedy algorithm: add sections to current chunk until max_lines would be exceeded.
    """
    chunks = []
    current_chunk = {"sections": [], "total_lines": 0}

    for section in sections:
        section_lines = len(section["lines"])

        # If single section exceeds max_lines, it becomes its own chunk
        if section_lines > max_lines:
            # Flush current chunk first
            if current_chunk["sections"]:
                chunks.append(current_chunk)
                current_chunk = {"sections": [], "total_lines": 0}
            chunks.append({"sections": [section], "total_lines": section_lines})
            continue

        # Would adding this section exceed the limit?
        if current_chunk["total_lines"] + section_lines > max_lines and current_chunk["sections"]:
            chunks.append(current_chunk)
            current_chunk = {"sections": [], "total_lines": 0}

        current_chunk["sections"].append(section)
        current_chunk["total_lines"] += section_lines

    # Flush remaining
    if current_chunk["sections"]:
        # Merge tiny trailing chunk with previous
        if current_chunk["total_lines"] < MIN_CHUNK_LINES and chunks:
            chunks[-1]["sections"].extend(current_chunk["sections"])
            chunks[-1]["total_lines"] += current_chunk["total_lines"]
        else:
            chunks.append(current_chunk)

    return chunks


def _detect_source_language(lines):
    """Heuristic: detect primary language of the document.

    Uses character-class density over a larger sample to avoid
    false positives from domain names or quoted foreign text.
    """
    # Use first 200 lines, stripping code blocks and URLs
    sample_lines = []
    in_code = False
    for line in lines[:200]:
        if CODE_FENCE_RE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        # Strip URLs and domain names
        cleaned = re.sub(r"https?://\S+", "", line)
        cleaned = re.sub(r"\b\w+\.\w{2,3}(?:\.\w{2,3})?\b", "", cleaned)
        sample_lines.append(cleaned)

    sample = "\n".join(sample_lines)
    total_chars = max(len(re.sub(r"\s", "", sample)), 1)

    # Count script-specific characters
    ko_count = len(re.findall(r"[\uac00-\ud7af]", sample))
    zh_count = len(re.findall(r"[\u4e00-\u9fff]", sample))
    ja_count = len(re.findall(r"[\u3040-\u309f\u30a0-\u30ff]", sample))
    ar_count = len(re.findall(r"[\u0600-\u06ff]", sample))

    # Threshold: >10% of non-whitespace chars in that script
    threshold = total_chars * 0.10
    if ko_count > threshold:
        return "ko"
    if zh_count > threshold:
        return "zh"
    if ja_count > threshold:
        return "ja"
    if ar_count > threshold:
        return "ar"
    # Latin-script languages: need higher threshold and word-boundary matching
    # Default to English for technical/mixed-language documents
    return "en"


def split_document(source_path, output_dir, max_lines=DEFAULT_MAX_LINES):
    """Split a markdown file into translation chunks.

    Returns manifest dict with chunk metadata.
    """
    with open(source_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    total_lines = len(lines)

    # Detect source language
    source_lang = _detect_source_language(lines)

    # If small enough for single agent, return as single chunk
    if total_lines <= max_lines:
        return {
            "source": source_path,
            "source_language": source_lang,
            "total_lines": total_lines,
            "strategy": "single",
            "chunks": [
                {
                    "id": 0,
                    "file": source_path,
                    "lines": total_lines,
                    "headings": [],
                    "has_code_blocks": "```" in content,
                }
            ],
        }

    # Parse and group
    sections = _parse_sections(lines)
    chunks = _group_into_chunks(sections, max_lines)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Write chunk files
    manifest_chunks = []
    for i, chunk in enumerate(chunks):
        chunk_lines = []
        headings = []
        for section in chunk["sections"]:
            chunk_lines.extend(section["lines"])
            if section["heading_text"] != "(preamble)":
                headings.append(section["heading_text"])

        chunk_content = "\n".join(chunk_lines)
        chunk_file = os.path.join(output_dir, f"chunk-{i:02d}.md")

        with open(chunk_file, "w", encoding="utf-8") as f:
            f.write(chunk_content)

        manifest_chunks.append({
            "id": i,
            "file": chunk_file,
            "lines": len(chunk_lines),
            "headings": headings,
            "has_code_blocks": "```" in chunk_content,
        })

    return {
        "source": source_path,
        "source_language": source_lang,
        "total_lines": total_lines,
        "strategy": "multi",
        "chunk_count": len(chunks),
        "output_dir": output_dir,
        "chunks": manifest_chunks,
    }


def main():
    parser = argparse.ArgumentParser(description="Split markdown for parallel translation")
    parser.add_argument("--source", required=True, help="Source markdown file")
    parser.add_argument("--output-dir", default=".tmp/translate-chunks",
                        help="Directory for chunk files")
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES,
                        help=f"Max lines per chunk (default: {DEFAULT_MAX_LINES})")
    parser.add_argument("--project-dir", default=".", help="Project root")
    args = parser.parse_args()

    source = (args.source if os.path.isabs(args.source)
              else os.path.join(args.project_dir, args.source))
    output_dir = (args.output_dir if os.path.isabs(args.output_dir)
                  else os.path.join(args.project_dir, args.output_dir))

    if not os.path.exists(source):
        print(json.dumps({"valid": False, "error": f"Source not found: {source}"}))
        sys.exit(1)

    manifest = split_document(source, output_dir, args.max_lines)
    manifest["valid"] = True

    # Write manifest file
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    manifest["manifest_path"] = manifest_path

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
