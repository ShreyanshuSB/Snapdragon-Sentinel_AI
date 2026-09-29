from __future__ import annotations

from typing import Any


class ContextItem:
    """Represents a single evidence or context block with priority and source ID."""

    def __init__(
        self,
        source_id: str,
        source_type: str,
        title: str,
        text: str,
        priority: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.source_id = source_id
        self.source_type = source_type
        self.title = title
        self.text = text
        self.priority = priority  # 1 = highest, 8 = lowest
        self.metadata = metadata or {}

    @property
    def estimated_tokens(self) -> int:
        # Conservative token estimation: ~4 chars per token + 10 tokens formatting overhead
        return (len(self.text) + len(self.source_id) + len(self.title)) // 4 + 10


class ContextBudgetManager:
    """
    Manages context window budgets for reasoning models (e.g. Qwen3-VL 4096 tokens).
    Deduplicates evidence, prioritizes critical items, and truncates gracefully.
    """

    def __init__(
        self,
        max_tokens: int = 4096,
        reserve_for_output: int = 512,
        max_input_tokens: int | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self.reserve_for_output = reserve_for_output
        self.max_input_tokens = max_input_tokens if max_input_tokens is not None else max(512, max_tokens - reserve_for_output)


    def prune_and_fit(
        self,
        items: list[ContextItem],
        system_prompt: str = "",
        user_question: str = "",
    ) -> tuple[list[ContextItem], int, list[str]]:
        """
        Sorts items by priority, fits them into max_input_tokens, and drops lowest priority if exceeded.
        Returns: (kept_items, total_estimated_tokens, dropped_source_ids)
        """
        base_tokens = (len(system_prompt) + len(user_question)) // 4 + 20
        available_budget = self.max_input_tokens - base_tokens

        # Deduplicate items by source_id
        seen_ids: set[str] = set()
        deduped_items: list[ContextItem] = []
        for item in items:
            if item.source_id in seen_ids:
                continue
            seen_ids.add(item.source_id)
            deduped_items.append(item)

        # Sort primarily by priority (ascending: 1 is top priority, 8 is lowest)
        sorted_items = sorted(deduped_items, key=lambda x: x.priority)

        kept: list[ContextItem] = []
        dropped_ids: list[str] = []
        accumulated_tokens = base_tokens

        for item in sorted_items:
            item_tokens = item.estimated_tokens
            if accumulated_tokens + item_tokens <= self.max_input_tokens:
                kept.append(item)
                accumulated_tokens += item_tokens
            else:
                dropped_ids.append(item.source_id)

        return kept, accumulated_tokens, dropped_ids
