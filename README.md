# ABM Contact Cards

Static, privacy-friendly "scan to save contact" QR codes for event badges,
signage, and slides.

No third-party QR/analytics vendor is involved. Each QR code encodes a link
to a plain `.vcf` (vCard) file hosted on GitHub Pages. Scanning it opens the
phone's native "Add Contact" screen directly — nothing is logged, tracked,
or sold.

## How it works

- `contacts/<slug>.vcf` — one vCard file per rep, hosted via GitHub Pages
- `qrcodes/<slug>.png` — a QR code image pointing at that hosted `.vcf` URL
- `generate.py` — regenerates both from the `reps` list in the script

## Setup

1. **Clone this repo** (or create a new GitHub repo and copy these files in).

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Edit `generate.py`:**
   - Set `GITHUB_USERNAME` and `REPO_NAME` at the top to match your repo.
   - Edit the `reps` list with real rep details (name, title, state, phone,
     email, website).

4. **Run the generator:**
   ```bash
   python3 generate.py
   ```
   This writes/updates files in `contacts/` and `qrcodes/`.

5. **Commit and push:**
   ```bash
   git add contacts/ qrcodes/
   git commit -m "Update contact cards"
   git push
   ```

6. **Enable GitHub Pages** (one-time setup):
   - Go to the repo's **Settings → Pages**
   - Under "Build and deployment", set **Source** to "Deploy from a branch"
   - Set **Branch** to `main` (or your default branch) and folder to `/ (root)`
   - Save. GitHub will publish the site at:
     `https://<GITHUB_USERNAME>.github.io/<REPO_NAME>/`
   - It can take a minute or two to go live the first time.

7. **Print or embed the QR codes** from `qrcodes/` on badges, table signage,
   or slides.

## Updating a rep's info after printing

If a phone number, email, or title is wrong:

1. Edit that rep's entry in the `reps` list in `generate.py`.
2. Rerun `python3 generate.py` — this rewrites their `.vcf` file.
   (The QR code image itself does not change, since it just points to the
   same URL.)
3. Commit and push the updated `contacts/<slug>.vcf` file.
4. Done — no reprinting needed. The already-printed QR code now serves the
   corrected info within a minute or two of GitHub Pages redeploying.

## Adding a new rep

Add a new entry to the `reps` list in `generate.py` with a unique `slug`,
then rerun the script, commit, and push. A new QR code will appear in
`qrcodes/`.

## Privacy notes

- No QR/analytics vendor sits in the middle of a scan — the `.vcf` file is
  served directly from GitHub Pages.
- GitHub Pages is a static file host; it does not run scan analytics or sell
  data. Standard GitHub access/traffic logs apply, same as any GitHub-hosted
  site.
- There is no scan-count or location analytics with this approach. If you
  need that later, that's a deliberate trade-off — see the discussion in
  chat about dynamic QR vendors and their data-sharing practices before
  adding one back in.
