"""Parse a JATS .nxml article into per-section text records ready for chunking."""

from lxml import etree

MIN_SECTION_CHARS = 40


def _text(elem) -> str:
    return "".join(elem.itertext()).strip() if elem is not None else ""


def _clean(text: str) -> str:
    return " ".join(text.split())


def _extract_title(root) -> str:
    return _clean(_text(root.find(".//front/article-meta/title-group/article-title")))


def _extract_journal(root) -> str:
    return _clean(_text(root.find(".//front/journal-meta/journal-title-group/journal-title")))


def _extract_pub_date(root) -> str:
    for pub_date in root.findall(".//front/article-meta/pub-date"):
        year = _text(pub_date.find("year"))
        month = _text(pub_date.find("month"))
        day = _text(pub_date.find("day"))
        parts = [p for p in (year, month, day) if p]
        if parts:
            return "-".join(parts)
    return ""


def _extract_abstract(root) -> str:
    paragraphs = root.findall(".//front/article-meta/abstract//p")
    return _clean(" ".join(_text(p) for p in paragraphs))


def _extract_sections(root) -> list[tuple[str, str]]:
    """Return (heading, text) pairs, one per <sec>, using only each section's own direct paragraphs."""
    sections = []
    for sec in root.findall(".//body//sec"):
        heading = _clean(_text(sec.find("title"))) or "Body"
        paragraphs = sec.findall("p")
        text = _clean(" ".join(_text(p) for p in paragraphs))
        if len(text) >= MIN_SECTION_CHARS:
            sections.append((heading, text))
    return sections


def parse_nxml(nxml_bytes: bytes, pmcid: str) -> list[dict]:
    """Parse article XML into a list of {pmcid, title, journal, pub_date, section, text} records."""
    root = etree.fromstring(nxml_bytes)

    title = _extract_title(root)
    journal = _extract_journal(root)
    pub_date = _extract_pub_date(root)

    records = []

    abstract = _extract_abstract(root)
    if len(abstract) >= MIN_SECTION_CHARS:
        records.append(
            {
                "pmcid": pmcid,
                "title": title,
                "journal": journal,
                "pub_date": pub_date,
                "section": "Abstract",
                "text": abstract,
            }
        )

    for heading, text in _extract_sections(root):
        records.append(
            {
                "pmcid": pmcid,
                "title": title,
                "journal": journal,
                "pub_date": pub_date,
                "section": heading,
                "text": text,
            }
        )

    return records
