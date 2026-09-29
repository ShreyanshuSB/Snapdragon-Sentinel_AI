from __future__ import annotations

import re
from typing import Any


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 60,
    min_chunk_size: int = 40,
) -> list[dict[str, Any]]:
    """
    Splits text into chunks preserving sentence and paragraph boundaries.
    Ensures words are never cut mid-token.

    Args:
        text: Raw text content to chunk.
        chunk_size: Target maximum characters per chunk (default 500, ~100 tokens).
        overlap: Character overlap between contiguous chunks to preserve context (default 60).
        min_chunk_size: Minimum characters required to emit a chunk (discards tiny whitespace residues).

    Returns:
        List of chunk dicts: {"chunk_index": int, "text": str, "start_char": int, "end_char": int}
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    if len(clean_text) <= chunk_size:
        return [
            {
                "chunk_index": 0,
                "text": clean_text,
                "start_char": 0,
                "end_char": len(clean_text),
            }
        ]

    # Split into paragraphs and sentences using regex
    # Matches paragraph breaks (\n\n+) or sentence endings (.!?) followed by space/newline
    sentence_end_pattern = re.compile(r'(?<=[.!?\n])\s+')
    raw_sentences = sentence_end_pattern.split(clean_text)

    # Filter empty sentences while tracking their start positions in original text
    sentences: list[str] = [s.strip() for s in raw_sentences if s.strip()]
    if not sentences:
        return []

    chunks: list[dict[str, Any]] = []
    current_chunk_sentences: list[str] = []
    current_length = 0
    chunk_index = 0
    last_end = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # If a single sentence exceeds chunk_size, split by word boundaries
        if sentence_len > chunk_size:
            # First flush any pending sentences
            if current_chunk_sentences:
                chunk_str = " ".join(current_chunk_sentences)
                start_pos = clean_text.find(chunk_str, last_end)
                if start_pos == -1:
                    start_pos = last_end
                end_pos = start_pos + len(chunk_str)
                chunks.append({
                    "chunk_index": chunk_index,
                    "text": chunk_str,
                    "start_char": start_pos,
                    "end_char": end_pos,
                })
                chunk_index += 1
                last_end = max(0, end_pos - overlap)
                current_chunk_sentences = []
                current_length = 0

            # Split oversized sentence by words
            words = sentence.split()
            word_chunk: list[str] = []
            word_len = 0
            for w in words:
                if word_len + len(w) + 1 > chunk_size and word_chunk:
                    sub_str = " ".join(word_chunk)
                    start_pos = clean_text.find(sub_str, last_end)
                    if start_pos == -1:
                        start_pos = last_end
                    end_pos = start_pos + len(sub_str)
                    chunks.append({
                        "chunk_index": chunk_index,
                        "text": sub_str,
                        "start_char": start_pos,
                        "end_char": end_pos,
                    })
                    chunk_index += 1
                    last_end = max(0, end_pos - overlap)
                    word_chunk = [w]
                    word_len = len(w)
                else:
                    word_chunk.append(w)
                    word_len += len(w) + 1

            if word_chunk:
                current_chunk_sentences = word_chunk
                current_length = word_len
            continue

        if current_length + sentence_len + 1 > chunk_size and current_chunk_sentences:
            chunk_str = " ".join(current_chunk_sentences)
            start_pos = clean_text.find(chunk_str, last_end)
            if start_pos == -1:
                start_pos = last_end
            end_pos = start_pos + len(chunk_str)

            chunks.append({
                "chunk_index": chunk_index,
                "text": chunk_str,
                "start_char": start_pos,
                "end_char": end_pos,
            })
            chunk_index += 1
            last_end = max(0, end_pos - overlap)

            # Keep trailing sentence if within overlap budget for continuity
            overlap_sentences: list[str] = []
            overlap_len = 0
            for s in reversed(current_chunk_sentences):
                if overlap_len + len(s) + 1 <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s) + 1
                else:
                    break

            current_chunk_sentences = overlap_sentences + [sentence]
            current_length = sum(len(s) for s in current_chunk_sentences) + len(current_chunk_sentences) - 1
        else:
            current_chunk_sentences.append(sentence)
            current_length += sentence_len + 1

    if current_chunk_sentences:
        chunk_str = " ".join(current_chunk_sentences)
        if len(chunk_str) >= min_chunk_size or not chunks:
            start_pos = clean_text.find(chunk_str, last_end)
            if start_pos == -1:
                start_pos = last_end
            end_pos = start_pos + len(chunk_str)
            chunks.append({
                "chunk_index": chunk_index,
                "text": chunk_str,
                "start_char": start_pos,
                "end_char": end_pos,
            })

    return chunks
