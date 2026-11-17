"""BibTeX that Zotero exports, and the parser for it."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import bibtexparser
from bibtexparser.middlewares import NormalizeFieldKeys, default_parse_stack
from bibtexparser.model import DuplicateBlockKeyBlock, Entry

# BibTeX styles define month macros such as "may". bibtexparser keeps a macro
# that the source does not define as its name.
_MONTHS = {
    name[:3].lower(): name
    for name in (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
}


def _as_dict(entry: Entry) -> dict[str, str]:
    fields = {field.key: str(field.value) for field in entry.fields}
    if "month" in fields:
        fields["month"] = _MONTHS.get(fields["month"].lower(), fields["month"])
    return {"ID": entry.key, "ENTRYTYPE": entry.entry_type, **fields}


def parse_bibtex(text: str) -> list[dict[str, str]]:
    """Parse BibTeX source into a list of entries, with month macros expanded.

    Each entry is a dict of its fields, with the citation key in ``ID`` and the
    entry type in ``ENTRYTYPE``. Field names are in lower case. An entry with
    the same key as an earlier entry is kept.
    """
    library = bibtexparser.parse_string(
        text, parse_stack=[*default_parse_stack(), NormalizeFieldKeys()]
    )
    strings = "".join(f"{string.raw}\n" for string in library.strings)
    entries = []
    for block in library.blocks:
        if isinstance(block, Entry):
            entries.append(_as_dict(block))
        elif (
            isinstance(block, DuplicateBlockKeyBlock)
            and isinstance(block.ignore_error_block, Entry)
            and block.ignore_error_block.raw
        ):
            # bibtexparser does not apply the parse stack to a duplicate.
            # Parse the duplicate again, with the string definitions.
            entries.extend(parse_bibtex(strings + block.ignore_error_block.raw))
    return entries


@dataclass(frozen=True)
class BibTeX:
    """BibTeX that Zotero exports for a ``format="bibtex"`` request.

    ``text`` is the BibTeX source as Zotero sends it. Write it to a file to
    get a ``.bib`` file. ``entries`` is the parsed entries: a list of dicts
    with the citation key in ``ID``, the entry type in ``ENTRYTYPE``, and one
    key for each field. Field values are not decoded from LaTeX.
    """

    text: str

    @cached_property
    def entries(self) -> list[dict[str, str]]:
        """The parsed entries, in source order."""
        return parse_bibtex(self.text)

    @classmethod
    def join(cls, parts: list[BibTeX]) -> BibTeX:
        """Join the BibTeX from several responses, for example from pages."""
        return cls("\n\n".join(p.text.strip() for p in parts if p.text.strip()))

    def __str__(self) -> str:
        return self.text
