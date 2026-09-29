from __future__ import annotations

from typing import Any
from app.schemas.vision import BoundingBox


def polygon_to_bbox(
    polygon: list[list[float]] | list[tuple[float, float]],
    image_width: int,
    image_height: int,
) -> BoundingBox:
    """
    Converts 4-point polygon or quadrilateral to normalized BoundingBox [0.0 - 1.0]
    and absolute pixel coordinates with strict boundary clamping.
    """
    xs = [float(p[0]) for p in polygon]
    ys = [float(p[1]) for p in polygon]

    abs_min_x = max(0.0, min(xs))
    abs_min_y = max(0.0, min(ys))
    abs_max_x = min(float(image_width), max(xs))
    abs_max_y = min(float(image_height), max(ys))

    # Normalized [0.0 - 1.0]
    norm_min_x = round(abs_min_x / max(1, image_width), 5)
    norm_min_y = round(abs_min_y / max(1, image_height), 5)
    norm_max_x = round(abs_max_x / max(1, image_width), 5)
    norm_max_y = round(abs_max_y / max(1, image_height), 5)

    min_x = min(norm_min_x, norm_max_x)
    min_y = min(norm_min_y, norm_max_y)
    max_x = max(norm_min_x, norm_max_x)
    max_y = max(norm_min_y, norm_max_y)
    width = round(max(0.0, max_x - min_x), 5)
    height = round(max(0.0, max_y - min_y), 5)

    return BoundingBox(
        x=min_x,
        y=min_y,
        width=width,
        height=height,
        x_min=min_x,
        y_min=min_y,
        x_max=max_x,
        y_max=max_y,
        x_abs_min=round(abs_min_x, 2),
        y_abs_min=round(abs_min_y, 2),
        x_abs_max=round(abs_max_x, 2),
        y_abs_max=round(abs_max_y, 2),
    )


def sort_reading_order(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Deterministic top-to-bottom, left-to-right reading order sorting.
    Groups regions into spatial horizontal lines based on line height overlap,
    then sorts left-to-right within each line.
    """
    if not regions:
        return []

    # Calculate median height to establish line grouping threshold
    heights = [
        max(0.001, float(r["bbox"].y_max - r["bbox"].y_min))
        for r in regions
        if "bbox" in r and r["bbox"]
    ]
    median_h = sorted(heights)[len(heights) // 2] if heights else 0.03
    line_threshold = median_h * 0.6

    # Sort initially by y_min
    sorted_by_y = sorted(
        regions,
        key=lambda r: (r["bbox"].y_min if "bbox" in r and r["bbox"] else 0.0),
    )

    lines: list[list[dict[str, Any]]] = []
    current_line: list[dict[str, Any]] = []
    current_y: float | None = None

    for r in sorted_by_y:
        y_top = r["bbox"].y_min if "bbox" in r and r["bbox"] else 0.0
        if current_y is None:
            current_line = [r]
            current_y = y_top
        elif abs(y_top - current_y) <= line_threshold:
            current_line.append(r)
        else:
            lines.append(current_line)
            current_line = [r]
            current_y = y_top

    if current_line:
        lines.append(current_line)

    # Sort each line left-to-right by x_min
    ordered_regions: list[dict[str, Any]] = []
    order_idx = 1
    for line in lines:
        sorted_line = sorted(
            line,
            key=lambda r: (r["bbox"].x_min if "bbox" in r and r["bbox"] else 0.0),
        )
        for item in sorted_line:
            item["reading_order"] = order_idx
            ordered_regions.append(item)
            order_idx += 1

    return ordered_regions
