"""
Generate vCard (.vcf) files and matching QR codes for ABM event contact cards.

Each person gets:
  - contacts/<slug>.vcf   -> the vCard file, published via GitHub Pages
  - qrcodes/<slug>.png    -> a QR code pointing at that hosted .vcf URL

Scanning the QR code opens the phone's "Add Contact" screen directly
(iOS and Android both handle .vcf links this way) - no landing page,
no third-party redirect, no analytics vendor involved.

SOURCE DATA
-----------
People are read from the spreadsheet named in SOURCE_XLSX (columns:
First, Last, State, Title, Email, Phone). That file is gitignored on
purpose - it holds real contact details and must not be committed.

USAGE
-----
1. Put the current spreadsheet next to this script.
2. Run: python3 generate.py
3. Commit and push contacts/ and qrcodes/, then let GitHub Pages redeploy.
4. QR codes in qrcodes/ are ready to print.

UPDATING SOMEONE'S INFO LATER
-----------------------------
Fix their row in the spreadsheet and rerun. The .vcf is rewritten but the
QR image does NOT change, because it still points at the same URL - so
nothing needs reprinting.
"""

import os
import re

import openpyxl
import qrcode

# --- Configuration -----------------------------------------------------

GITHUB_USERNAME = "icaos"             # GitHub account hosting this repo
REPO_NAME = "abm-contact-cards"       # GitHub repo name

SOURCE_XLSX = "NameTag_Data_1.xlsx"
SOURCE_SHEET = "Submissions"

CONTACTS_DIR = "contacts"
QRCODES_DIR = "qrcodes"

# --- Helpers -------------------------------------------------------------


def clean(value) -> str:
    """Normalize a spreadsheet cell to a trimmed string ('' when empty)."""
    return "" if value is None else str(value).strip()


def escape(value: str) -> str:
    """
    Escape a value for vCard 3.0.

    Real job titles contain commas ("Director, Field Operations") and the
    occasional semicolon. Unescaped, those characters are read as field
    separators and the contact imports with mangled or missing data, so this
    is not cosmetic.
    """
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def slugify(text: str) -> str:
    """Lowercase, hyphen-separated, safe for both a filename and a URL."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load_people(path: str, sheet: str) -> list:
    """
    Read the spreadsheet into a list of person dicts.

    Rows with no name are skipped: a card with no one on it is not useful,
    and the blank trailing rows spreadsheets accumulate would otherwise
    become empty .vcf files.
    """
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = workbook[sheet].iter_rows(values_only=True)

    header = [clean(h) for h in next(rows)]
    index = {name: position for position, name in enumerate(header) if name}

    people = []
    for row_number, row in enumerate(rows, start=2):
        def field(name):
            position = index.get(name)
            return clean(row[position]) if position is not None else ""

        first, last = field("First"), field("Last")
        if not first and not last:
            continue

        state, title = field("State"), field("Title")

        # The State column is free text and holds three different things:
        # a US state for delegates, an organization acronym for ex-officio
        # members (APA, NCSL, ICJ...), and - for ICAOS staff - their job
        # title, with "ICAOS Staff" sitting in the Title column instead.
        # For those rows the two columns are effectively swapped, so they
        # are put back the right way round here: the employer becomes the
        # company and the specific role becomes the title. Left alone,
        # those contacts would show "Education Manager" as their company.
        if title == "ICAOS Staff":
            org, title = "ICAOS", state
        else:
            org = state

        people.append({
            "row": row_number,
            "first": first,
            "last": last,
            "full_name": f"{first} {last}".strip(),
            "org": org,
            "title": title,
            "email": field("Email"),
            "phone": field("Phone"),
        })

    return people


def merge_duplicates(people: list) -> list:
    """
    Collapse rows that describe the same person into one card.

    The source sheet has one row per ROLE, not per person, so someone who
    holds two roles (Commissioner and Official Designee, say) appears twice
    with the same name, email and phone. Left alone that produces two badges
    and two QR codes for one human. Rows are matched on name + email and
    merged, with the roles joined into a single TITLE so nothing is lost.

    Fields other than title take the first non-empty value in the group, so
    a role row that omitted a phone number still inherits it.
    """
    merged = {}
    for person in people:
        key = (person["full_name"].lower(), person["email"].lower())
        existing = merged.get(key)

        if existing is None:
            person["titles"] = [person["title"]] if person["title"] else []
            merged[key] = person
            continue

        if person["title"] and person["title"] not in existing["titles"]:
            existing["titles"].append(person["title"])
        for field in ("org", "phone", "email"):
            if not existing[field]:
                existing[field] = person[field]

    people = list(merged.values())
    for person in people:
        person["title"] = ", ".join(person["titles"])
    return people


def assign_slugs(people: list) -> None:
    """
    Give each person a unique slug, in place.

    Two different people can share a name, and in this data two do. The
    slug is a filename and a public URL, so a collision would mean one
    person's card silently overwriting the other's. Duplicates therefore
    get a numeric suffix, assigned in spreadsheet order so that reruns
    produce the same slug for the same person and previously printed QR
    codes keep working.
    """
    seen = {}
    for person in people:
        base = slugify(person["full_name"])
        seen[base] = seen.get(base, 0) + 1
        person["slug"] = base if seen[base] == 1 else f"{base}-{seen[base]}"


def build_vcard(person: dict) -> str:
    """
    Build a vCard 3.0 record.

    Optional fields are omitted rather than written empty: a TEL line with
    no number shows up as a blank phone entry on the saved contact.
    """
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{escape(person['last'])};{escape(person['first'])};;;",
        f"FN:{escape(person['full_name'])}",
    ]

    # ORG (Company) carries the state, or the organization for ex-officio
    # members. It replaces an earlier ADR line that held nothing but a state,
    # which phones rendered as a mostly-empty address block.
    if person["org"]:
        lines.append(f"ORG:{escape(person['org'])}")
    if person["title"]:
        lines.append(f"TITLE:{escape(person['title'])}")
    if person["phone"]:
        lines.append(f"TEL;TYPE=CELL:{escape(person['phone'])}")
    if person["email"]:
        lines.append(f"EMAIL:{escape(person['email'])}")

    lines.append("END:VCARD")
    return "\n".join(lines) + "\n"


# --- Generation ----------------------------------------------------------


def main():
    if not os.path.exists(SOURCE_XLSX):
        raise SystemExit(
            f"Source spreadsheet {SOURCE_XLSX!r} not found.\n"
            "It is gitignored (it holds real contact data), so it does not\n"
            "arrive with a fresh clone - copy it in before running."
        )

    os.makedirs(CONTACTS_DIR, exist_ok=True)
    os.makedirs(QRCODES_DIR, exist_ok=True)

    people = load_people(SOURCE_XLSX, SOURCE_SHEET)
    people = merge_duplicates(people)
    assign_slugs(people)

    print(f"Generating {len(people)} contact card(s) from {SOURCE_XLSX}...\n")

    skipped = []
    for person in people:
        vcf_path = os.path.join(CONTACTS_DIR, f"{person['slug']}.vcf")
        with open(vcf_path, "w") as handle:
            handle.write(build_vcard(person))

        url = (
            f"https://{GITHUB_USERNAME}.github.io/"
            f"{REPO_NAME}/{CONTACTS_DIR}/{person['slug']}.vcf"
        )

        qrcode.make(url).save(os.path.join(QRCODES_DIR, f"{person['slug']}.png"))

        missing = [f for f in ("title", "email", "phone") if not person[f]]
        if missing:
            skipped.append((person["row"], person["full_name"], missing))

    print(f"Done. {len(people)} card(s) written to "
          f"{CONTACTS_DIR}/ and {QRCODES_DIR}/")

    # Surface incomplete rows rather than letting a card go to print with a
    # missing phone number that nobody noticed.
    if skipped:
        print(f"\n{len(skipped)} card(s) generated with missing fields:")
        for row_number, name, missing in skipped:
            print(f"  row {row_number:<4} {name:<28} missing: {', '.join(missing)}")


if __name__ == "__main__":
    main()
