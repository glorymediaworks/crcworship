#!/usr/bin/env python3
"""Convert paired USFM Bible archives into browser-friendly verse JSON files."""

from __future__ import annotations

import argparse
import html
import json
import re
import zipfile
from pathlib import Path


BOOK_ORDER = [
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
    "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
    "ECC", "SNG", "ISA", "JER", "LAM", "EZK", "DAN", "HOS", "JOL", "AMO",
    "OBA", "JON", "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL", "MAT",
    "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL", "EPH", "PHP",
    "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM", "HEB", "JAS", "1PE",
    "2PE", "1JN", "2JN", "3JN", "JUD", "REV",
]
BOOK_SET = set(BOOK_ORDER)

NOTE_RE = re.compile(r"\\(?:f|fe|x)\b.*?\\(?:f|fe|x)\*", re.DOTALL)
WORD_RE = re.compile(r"\\w\s+([^|\\]*?)(?:\|[^\\]*?)?\\w\*")
FIG_RE = re.compile(r"\\fig\b.*?\\fig\*", re.DOTALL)
MILESTONE_RE = re.compile(r"\\(?:qt-s|qt-e|ts-s|ts-e)\\?[^\\]*?\\\*")
MARKER_RE = re.compile(r"\\[a-z][a-z0-9-]*(?:\s+\d+)?\*?\s*", re.IGNORECASE)


def clean_usfm_text(value: str) -> str:
    """Remove USFM formatting, notes, references, and Strong's attributes."""
    value = NOTE_RE.sub("", value)
    value = FIG_RE.sub("", value)
    value = MILESTONE_RE.sub("", value)
    # Run repeatedly because word fields may be adjacent or contain punctuation.
    previous = None
    while previous != value:
        previous = value
        value = WORD_RE.sub(lambda match: match.group(1), value)
    value = re.sub(r"\|[a-z][^\\\s]*(?:=\"[^\"]*\")?", "", value, flags=re.IGNORECASE)
    value = MARKER_RE.sub("", value)
    value = html.unescape(value)
    value = re.sub(r"\s+([,.;:!?…])", r"\1", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def parse_usfm(content: str) -> tuple[str | None, dict[str, str]]:
    book_id = None
    chapter = None
    current_key = None
    verses: dict[str, str] = {}

    for raw_line in content.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        id_match = re.match(r"^\\id\s+([1-3]?[A-Z]{2,3})\b", line, re.IGNORECASE)
        if id_match:
            book_id = id_match.group(1).upper()
            continue

        chapter_match = re.match(r"^\\c\s+(\d+)\b", line)
        if chapter_match:
            chapter = chapter_match.group(1)
            current_key = None
            continue

        verse_match = re.match(r"^\\v\s+([^\s]+)\s*(.*)$", line)
        if verse_match and book_id and chapter:
            verse_number = verse_match.group(1)
            current_key = f"{book_id}.{chapter}.{verse_number}"
            verse_text = clean_usfm_text(verse_match.group(2))
            if current_key in verses and verse_text:
                verses[current_key] = f"{verses[current_key]} {verse_text}".strip()
            else:
                verses[current_key] = verse_text
            continue

        # Paragraph/poetry continuation lines after a verse remain part of that verse.
        if current_key and re.match(r"^\\(?:p|m|q\d*|qr|qc|qm\d*|li\d*|pi\d*|nb)\b", line):
            continuation = clean_usfm_text(line)
            if continuation:
                verses[current_key] = f"{verses[current_key]} {continuation}".strip()

    return book_id, verses


def convert_archive(archive_path: Path) -> tuple[dict[str, str], dict]:
    all_verses: dict[str, str] = {}
    books_found: list[str] = []
    duplicates: list[str] = []

    with zipfile.ZipFile(archive_path) as archive:
        usfm_names = sorted(name for name in archive.namelist() if name.lower().endswith((".usfm", ".sfm")))
        for name in usfm_names:
            content = archive.read(name).decode("utf-8-sig")
            book_id, verses = parse_usfm(content)
            if book_id not in BOOK_SET:
                continue
            books_found.append(book_id)
            for key, text in verses.items():
                if key in all_verses:
                    duplicates.append(key)
                if text:
                    all_verses[key] = text

        copyright_name = next((name for name in archive.namelist() if name.lower() == "copr.htm"), None)
        copyright_html = archive.read(copyright_name).decode("utf-8-sig") if copyright_name else ""

    metadata = {
        "sourceArchive": archive_path.name,
        "books": [book for book in BOOK_ORDER if book in set(books_found)],
        "missingBooks": [book for book in BOOK_ORDER if book not in set(books_found)],
        "verseCount": len(all_verses),
        "duplicateReferences": sorted(set(duplicates)),
        "copyrightHtml": copyright_html,
    }
    return all_verses, metadata


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--english", required=True, type=Path)
    parser.add_argument("--tamil", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    english, english_meta = convert_archive(args.english)
    tamil, tamil_meta = convert_archive(args.tamil)

    write_json(args.output / "english.json", english)
    write_json(args.output / "tamil.json", tamil)
    (args.output / "copyright-english.html").write_text(english_meta.pop("copyrightHtml"), encoding="utf-8")
    (args.output / "copyright-tamil.html").write_text(tamil_meta.pop("copyrightHtml"), encoding="utf-8")

    english_refs = set(english)
    tamil_refs = set(tamil)
    report = {
        "english": english_meta,
        "tamil": tamil_meta,
        "matchingReferenceCount": len(english_refs & tamil_refs),
        "englishOnlyReferenceCount": len(english_refs - tamil_refs),
        "tamilOnlyReferenceCount": len(tamil_refs - english_refs),
        "englishOnlyReferences": sorted(english_refs - tamil_refs),
        "tamilOnlyReferences": sorted(tamil_refs - english_refs),
        "emptyEnglishVerses": sorted(key for key, value in english.items() if not value.strip()),
        "emptyTamilVerses": sorted(key for key, value in tamil.items() if not value.strip()),
    }
    write_json(args.output / "validation-report.json", report)
    write_json(args.output / "bible-config.json", {
        "schemaVersion": 1,
        "keyFormat": "BOOK.CHAPTER.VERSE",
        "bookOrder": BOOK_ORDER,
        "translations": {
            "english": {
                "name": "World English Bible Updated",
                "shortName": "WEBU",
                "language": "English",
                "file": "english.json",
                "copyrightFile": "copyright-english.html",
            },
            "tamil": {
                "name": "Biblica Open Indian Tamil Contemporary Version",
                "shortName": "OTCV",
                "language": "Tamil",
                "file": "tamil.json",
                "copyrightFile": "copyright-tamil.html",
            },
        },
    })

    print(json.dumps({
        "englishVerses": len(english),
        "tamilVerses": len(tamil),
        "matchingReferences": report["matchingReferenceCount"],
        "englishOnly": report["englishOnlyReferenceCount"],
        "tamilOnly": report["tamilOnlyReferenceCount"],
    }, indent=2))


if __name__ == "__main__":
    main()
