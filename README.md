# ABM Contact Cards

Static, vendor-free "scan to save contact" QR codes for ICAOS Annual Business
Meeting nametags, signage, and slides.

Each QR code encodes a link to a plain `.vcf` (vCard) file published via
GitHub Pages. Scanning it opens the phone's native "Add Contact" screen
directly — no landing page, no third-party redirect, and no QR vendor
sitting in the middle collecting scan analytics.

## Why this is useful after printing

The QR image encodes a *URL*, not the contact details themselves. Correcting
someone's title or phone number means editing the `.vcf` that URL points at —
the printed code keeps working and nothing needs reprinting. This has been
verified in production, not just assumed.

## Contents

| Path | What it is |
|---|---|
| `contacts/<slug>.vcf` | One vCard per attendee, served over GitHub Pages |
| `qrcodes/<slug>.png` | The QR code pointing at that vCard's URL |
| `generate.py` | Builds both, from the source spreadsheet |
| `build_sheet.py` | Builds `nametag-sheet.html`, the QR assembly page |
| `build_csv.py` | Builds `nametag-merge.csv` for badge mail-merge |
| `build_xlsx.py` | Builds `nametag-merge.xlsx`, same data with QR images embedded |

## Source data

Attendees are read from `NameTag_Data_1.xlsx` (sheet `Submissions`, columns:
First, Last, State, Title, Email, Phone).

**That spreadsheet is gitignored and must stay that way.** It holds real
contact details for 151 government officials, and this repo is public — so
`*.xlsx`, `*.csv`, and the generated merge files are all excluded. A fresh
clone will not have it; copy it in before running anything.

### Two quirks in that sheet, handled automatically

- **One row per role, not per person.** Someone holding two roles appears
  twice. Those rows are merged into one card so nobody gets two badges, with
  their roles joined into a single title.
- **ICAOS staff have State and Title swapped.** Their `State` cell holds a
  job title and `Title` reads `ICAOS Staff`. `generate.py` puts these back the
  right way round for the phone contact (`ORG:ICAOS`, title = their real
  role). `build_csv.py` and `build_xlsx.py` deliberately keep the raw
  spreadsheet layout, because the badge template expects those columns as-is.

## Setup

```bash
pip install -r requirements.txt
```

## Regenerating everything

Order matters — `build_sheet.py` reads `contacts/`, so it must run after
`generate.py`:

```bash
python3 generate.py && python3 build_sheet.py && python3 build_csv.py && python3 build_xlsx.py
```

`build_sheet.py` refuses to run if the spreadsheet is newer than the cards,
rather than quietly producing a sheet from stale data.

Then commit and push `contacts/`, `qrcodes/`, and `nametag-sheet.html`, and
let GitHub Pages redeploy. The merge files stay local — they are gitignored.

## Updating someone after badges are printed

1. Fix their row in the spreadsheet.
2. Rerun the commands above. Their `.vcf` is rewritten; the QR image is
   **not**, because the URL has not changed.
3. Commit, push, wait for Pages to redeploy.
4. Done. The already-printed code now serves the corrected details.

## Adding an attendee

Add a row to the spreadsheet and rerun. A new slug, card, and QR code appear.

## Outputs for badge production

| File | For | Notes |
|---|---|---|
| `nametag-sheet.html` | Working through placements | Grouped by role, searchable, tracks what has been placed. Published at `/nametag-sheet.html` |
| `nametag-merge.csv` | Driving the badge printer | `Photo File Name` names the QR image; ship it with the `qrcodes/` folder |
| `nametag-merge.xlsx` | Checking by eye | Same columns plus the QR image embedded, so a wrong code is visible before printing |

A `.csv` cannot contain images — it is plain text. That is why mail-merge
software uses a filename column and pulls each image from a folder at print
time. The `.xlsx` embeds pictures for human review, but most merge tools will
still read the filename column, so keep the images alongside it.

## Hosting

GitHub Pages serves this repo's root, so the cards are live at:

```
https://icaos.github.io/abm-contact-cards/contacts/<slug>.vcf
```

Pages serves `.vcf` as `text/x-vcard`, which iOS and Android both handle.

### The repo is public — and that is a deliberate, revisitable choice

Pages on a private repo requires a paid plan, so the repo was made public to
ship quickly. The consequence: the full attendee roster is clonable, and git
history survives forks, so **going private later does not retract what has
already been published**.

To move to a private repo: upgrade the account to Pro/Team **first**, then
flip the repo private. Pages keeps publishing and the URLs are unchanged, so
already-printed QR codes keep working. Flipping private on a free plan
disables Pages instead.

A self-hosted alternative (NGINX behind Traefik, serving `contacts/` with
directory listing off) was considered and set aside for time. It is the right
answer if the roster should stop being publicly enumerable.

## Privacy notes

- No QR or analytics vendor is involved in a scan. The `.vcf` is served
  directly by GitHub Pages.
- Standard GitHub traffic logs apply. There is no scan-count or location
  analytics, by design.
- Cards carry the same information as a printed business card: name, title,
  state or organization, work phone, work email. Do not add personal
  addresses or personal mobile numbers.
