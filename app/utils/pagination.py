from typing import Any, List, Tuple

from app.config import PAGE_SIZE


def paginate(items: List[Any], page: int, page_size: int = PAGE_SIZE) -> Tuple[List[Any], int, bool, bool]:
    """
    Paginate a list of items.

    Returns:
        (page_items, total_pages, has_prev, has_next)
    """
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))

    start = page * page_size
    end = start + page_size
    page_items = items[start:end]

    has_prev = page > 0
    has_next = page < total_pages - 1

    return page_items, total_pages, has_prev, has_next
