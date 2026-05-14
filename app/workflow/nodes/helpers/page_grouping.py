from itertools import groupby

from app.workflow.state import PageText, PageOutline

_ARC_GROUP = {
    "setup": "Setup",
    "rising action": "Conflict",
    "climax": "Conflict",
    "resolution": "Resolution",
    "ending": "Resolution",
}


def _arc_group(arc_position: str) -> str:
    return _ARC_GROUP.get(arc_position.lower(), arc_position)


def group_pages_by_arc(pages: list[PageText], outlines: list[PageOutline]) -> str:
    outline_by_page = {o.page_number: o for o in outlines}

    sections = []
    for group_label, group in groupby(pages, key=lambda p: _arc_group(p.arc_position)):
        group = list(group)
        page_nums = (
            f"{group[0].page_number}-{group[-1].page_number}"
            if len(group) > 1
            else str(group[0].page_number)
        )
        outlines_str = "; ".join(
            outline_by_page[p.page_number].outline if p.page_number in outline_by_page else "N/A"
            for p in group
        )
        moods_str = "; ".join(p.mood for p in group)

        sections.append(
            f"{group_label} (Pages {page_nums})\n"
            f"Outlines: {outlines_str}\n"
            f"Moods: {moods_str}"
        )

    return "\n\n".join(sections)
