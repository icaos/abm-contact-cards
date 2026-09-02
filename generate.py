"""
Generate vCard (.vcf) files and matching QR codes for ABM event contact cards.

Each rep gets:
  - contacts/<slug>.vcf   -> the vCard file, hosted via GitHub Pages
  - qrcodes/<slug>.png    -> a QR code pointing at that hosted .vcf URL

Scanning the QR code opens the phone's "Add Contact" screen directly
(iOS and Android both handle .vcf links this way) — no landing page,
no third-party redirect, no analytics vendor involved.

USAGE
-----
1. Fill in GITHUB_USERNAME and REPO_NAME below to match your repo.
2. Edit the `reps` list with real rep details.
3. Run: python3 generate.py
4. Commit and push. Enable GitHub Pages (Settings -> Pages -> deploy
   from main branch, root folder).
5. QR codes in qrcodes/ are ready to print/use immediately.

UPDATING A REP'S INFO LATER
----------------------------
Edit their entry in `reps`, rerun this script, commit + push the
updated contacts/<slug>.vcf file. The QR code image does NOT change,
so nothing needs to be reprinted.
"""

import os

import qrcode

# --- Configuration -----------------------------------------------------

GITHUB_USERNAME = "icaos"             # GitHub account hosting this repo
REPO_NAME = "abm-contact-cards"       # <-- set this to your repo name

CONTACTS_DIR = "contacts"
QRCODES_DIR = "qrcodes"

# --- Rep data ------------------------------------------------------------
# Add/edit one dict per rep. `slug` is used for filenames/URLs, so keep it
# lowercase with hyphens (no spaces).

reps = [
    {
        "slug": "jane-doe",
        "full_name": "Jane Doe",
        "title": "Account Executive",
        "state": "CO",
        "phone": "+1-555-010-0001",
        "email": "jane.doe@example.com",
        "website": "https://example.com",
    },
    {
        "slug": "john-smith",
        "full_name": "John Smith",
        "title": "Sales Director",
        "state": "TX",
        "phone": "+1-555-010-0002",
        "email": "john.smith@example.com",
        "website": "https://example.com",
    },
    {
        "slug": "alex-rivera",
        "full_name": "Alex Rivera",
        "title": "Customer Success Manager",
        "state": "CA",
        "phone": "+1-555-010-0003",
        "email": "alex.rivera@example.com",
        "website": "https://example.com",
    },
]

# --- Generation ----------------------------------------------------------


def build_vcard(rep: dict) -> str:
    first, _, last = rep["full_name"].partition(" ")
    return (
        "BEGIN:VCARD\n"
        "VERSION:3.0\n"
        f"N:{last};{first};;;\n"
        f"FN:{rep['full_name']}\n"
        f"TITLE:{rep['title']}\n"
        f"ADR:;;;;{rep['state']};;\n"
        f"TEL;TYPE=CELL:{rep['phone']}\n"
        f"EMAIL:{rep['email']}\n"
        f"URL:{rep['website']}\n"
        "END:VCARD\n"
    )


def main():
    os.makedirs(CONTACTS_DIR, exist_ok=True)
    os.makedirs(QRCODES_DIR, exist_ok=True)

    print(f"Generating {len(reps)} contact card(s)...\n")

    for rep in reps:
        vcard_text = build_vcard(rep)

        vcf_path = os.path.join(CONTACTS_DIR, f"{rep['slug']}.vcf")
        with open(vcf_path, "w") as f:
            f.write(vcard_text)

        url = (
            f"https://{GITHUB_USERNAME}.github.io/"
            f"{REPO_NAME}/{CONTACTS_DIR}/{rep['slug']}.vcf"
        )

        qr_img = qrcode.make(url)
        qr_path = os.path.join(QRCODES_DIR, f"{rep['slug']}.png")
        qr_img.save(qr_path)

        print(f"  {rep['full_name']:<20} -> {url}")

    print(f"\nDone. Files written to {CONTACTS_DIR}/ and {QRCODES_DIR}/")

    if GITHUB_USERNAME == "GITHUB_USERNAME":
        print(
            "\nNOTE: GITHUB_USERNAME is still a placeholder. "
            "Update it at the top of this script and rerun before "
            "printing/distributing the QR codes."
        )


if __name__ == "__main__":
    main()
