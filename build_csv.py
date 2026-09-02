"""
Build the offline nametag mail-merge CSV.

Produces nametag-merge.csv with the columns the badge software expects:
Counter, First Name, Last Name, State, Title, Photo File Name - where
Photo File Name is the QR image in qrcodes/ for that person.

File:          build_csv.py
Author:        ICAOS
Created:       2026-09-02
Last modified: 2026-09-02

Change history:
  2026-09-02  Initial version.

TODO:
  - None outstanding.

USAGE
-----
Run from the repo root, after generate.py:

    python3 generate.py && python3 build_csv.py

The output is gitignored (*.csv), because it holds real attendee details
and this repo is public. Hand it to whoever is printing badges together
with the qrcodes/ folder - the file names in the CSV assume both sit in
the same directory.

WHY THIS READS THE SPREADSHEET, NOT THE CARDS
---------------------------------------------
generate.py rewrites ICAOS staff rows, whose State and Title columns are
swapped in the source, into the form a phone contact should show. The
badge template wants the columns exactly as the spreadsheet has them, so
State and Title are taken raw from the spreadsheet here rather than from
the generated .vcf files.
"""

import csv
import os
import re

import openpyxl

SOURCE_XLSX = "NameTag_Data_1.xlsx"
SOURCE_SHEET = "Submissions"
QRCODES_DIR = "qrcodes"
OUTPUT = "nametag-merge.csv"

COLUMNS = ["Counter", "First Name", "Last Name", "State", "Title",
           "Photo File Name"]


def clean(value) -> str:
    return "" if value is None else str(value).strip()


def slugify(text: str) -> str:
    """Must match generate.py, so the CSV points at real image files."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load_rows() -> list:
    workbook = openpyxl.load_workbook(SOURCE_XLSX, read_only=True,
                                      data_only=True)
    rows = workbook[SOURCE_SHEET].iter_rows(values_only=True)
    header = [clean(h) for h in next(rows)]
    index = {name: pos for pos, name in enumerate(header) if name}

    people = []
    for row in rows:
        def field(name):
            pos = index.get(name)
            return clean(row[pos]) if pos is not None else ""

        first, last = field("First"), field("Last")
        if not first and not last:
            continue

        people.append({
            "first": first,
            "last": last,
            "state": field("State"),
            "title": field("Title"),
            "email": field("Email"),
        })
    return people


def merge_duplicates(people: list) -> list:
    """
    One badge per person, matching the one QR code per person.

    The sheet has a row per ROLE, so someone holding two roles appears
    twice. Printing both rows would hand them two nametags, so the rows are
    merged and their roles joined - the same rule generate.py applies, which
    keeps the CSV and the QR images in step.
    """
    merged = {}
    for person in people:
        key = (f"{person['first']} {person['last']}".lower(),
               person["email"].lower())
        existing = merged.get(key)
        if existing is None:
            merged[key] = person
            continue
        for column in ("state", "title"):
            if person[column] and person[column] not in existing[column]:
                existing[column] = f"{existing[column]}, {person[column]}".strip(", ")
    return list(merged.values())


def main():
    if not os.path.exists(SOURCE_XLSX):
        raise SystemExit(
            f"Source spreadsheet {SOURCE_XLSX!r} not found. It is gitignored "
            "(it holds real contact data), so copy it in before running."
        )

    people = merge_duplicates(load_rows())

    missing = []
    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)

        for counter, person in enumerate(people, start=1):
            slug = slugify(f"{person['first']} {person['last']}")
            image = f"{slug}.png"
            if not os.path.exists(os.path.join(QRCODES_DIR, image)):
                missing.append(image)

            writer.writerow([counter, person["first"], person["last"],
                             person["state"], person["title"], image])

    print(f"Wrote {OUTPUT} - {len(people)} row(s)")

    # A CSV naming an image that does not exist prints a badge with no QR
    # code on it, and nothing about the CSV would show that in advance.
    if missing:
        print(f"\nWARNING: {len(missing)} row(s) name a missing image:")
        for name in missing:
            print(f"  {name}")
    else:
        print(f"Every row points at a real image in {QRCODES_DIR}/.")


if __name__ == "__main__":
    main()
