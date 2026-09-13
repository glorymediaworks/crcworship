# Local bilingual Bible data

This folder keeps the Bible data separate from the worship-song library so it
can be versioned, validated, and updated independently.

## Folder layout

- `data/english.json` — World English Bible Updated (WEBU)
- `data/tamil.json` — Biblica Open Indian Tamil Contemporary Version (OTCV)
- `data/bible-config.json` — translation names, files, and canonical book order
- `data/validation-report.json` — conversion counts and reference differences
- `data/copyright-english.html` — source-supplied English attribution/licence page
- `data/copyright-tamil.html` — source-supplied Tamil attribution/licence page
- `tools/convert_usfm.py` — repeatable USFM-to-JSON converter

## JSON format

Each translation is a UTF-8 JSON object keyed by a standard Bible reference:

```json
{
  "GEN.1.1": "Verse text",
  "JHN.3.16": "Verse text"
}
```

This flat format makes lookup fast in the browser. The presentation UI can load
the same key from both files and display English and Tamil together.

## Rebuild the files

From the project folder, run:

```powershell
python bible\tools\convert_usfm.py `
  --english "D:\Projects\Sowmi\Question Paper\engwebu_usfm.zip" `
  --tamil "D:\Projects\Sowmi\Question Paper\tamtcv_usfm.zip" `
  --output bible\data
```

The converter includes only the 66 canonical books, removes USFM formatting,
notes, cross-references, and Strong's metadata, and regenerates the validation
report. Keep the original archives outside this repository; the generated JSON,
source notices, converter, and validation report are the tracked project files.

## Current validation

- English: 66 books, 31,098 verse references
- Tamil: 66 books, 31,102 verse references
- Matching references: 31,093
- Empty verses: none

The small reference-count difference is expected because the translations place
some textual variants and Psalm or Romans verse numbers differently. See
`data/validation-report.json` for the exact references. The UI should gracefully
show the available translation if one side of a selected reference is absent.

## Attribution

Before publishing or distributing the Bible text, review and retain the notices
in both copyright HTML files. They were copied directly from the downloaded
translation packages.
