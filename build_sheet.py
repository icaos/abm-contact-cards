"""
Build the nametag QR assembly sheet.

Produces nametag-sheet.html: every attendee's QR code grouped by role, with
the file name of each QR image, for whoever is placing the codes on printed
nametags. The page is self-contained - QR images are embedded as data URIs -
so it works from a file:// path, a shared link, or GitHub Pages.

File:          build_sheet.py
Author:        ICAOS
Created:       2026-09-02
Last modified: 2026-09-02

Change history:
  2026-09-02  Initial version.

TODO:
  - If the attendee list grows much past ~300, consider linking the QR
    images instead of embedding them, to keep the page size down.

USAGE
-----
Run after generate.py, from the repo root:

    python3 build_sheet.py

It reads contacts/ and qrcodes/, so it always reflects whatever generate.py
last produced. It needs no third-party packages.
"""

import base64
import collections
import glob
import json
import os

TEMPLATE = r'''<title>ABM Nametag QR Assembly</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  :root {
    --paper:      #F3F4F6;
    --surface:    #FFFFFF;
    --ink:        #15181D;
    --muted:      #69717E;
    --accent:     #2C5D63;
    --accent-ink: #FFFFFF;
    --rule:       #DCE0E5;
    --done:       #E8EFEA;
    --done-ink:   #2F6B45;
    --qr-ground:  #FFFFFF;

    --step--1: 0.75rem;
    --step-0:  0.9375rem;
    --step-1:  1.125rem;
    --step-2:  1.5rem;
    --step-3:  2.125rem;

    --sans: "Libre Franklin", "Helvetica Neue", Arial, sans-serif;
    --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
  }

  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --paper:      #14171B;
      --surface:    #1C2026;
      --ink:        #E9ECEF;
      --muted:      #9AA3AF;
      --accent:     #6FB3B8;
      --accent-ink: #10161A;
      --rule:       #2C323A;
      --done:       #1E2C24;
      --done-ink:   #86C9A0;
      --qr-ground:  #FFFFFF;
    }
  }

  :root[data-theme="dark"] {
    --paper:      #14171B;
    --surface:    #1C2026;
    --ink:        #E9ECEF;
    --muted:      #9AA3AF;
    --accent:     #6FB3B8;
    --accent-ink: #10161A;
    --rule:       #2C323A;
    --done:       #1E2C24;
    --done-ink:   #86C9A0;
    --qr-ground:  #FFFFFF;
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: var(--sans);
    font-size: var(--step-0);
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }

  .wrap { max-width: 1180px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }

  /* --- Masthead --- */
  .masthead { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 2rem; }
  .eyebrow {
    font-family: var(--mono);
    font-size: var(--step--1);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
  }
  h1 {
    font-size: var(--step-3);
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin: 0;
    text-wrap: balance;
  }
  .lede { color: var(--muted); max-width: 62ch; margin: 0; }

  /* --- How-to --- */
  .howto {
    border-left: 3px solid var(--accent);
    padding: 0.875rem 0 0.875rem 1rem;
    margin: 1.75rem 0 0;
    display: flex; flex-direction: column; gap: 0.35rem;
    color: var(--muted);
    font-size: var(--step--1);
  }
  .howto b { color: var(--ink); font-weight: 600; }
  .howto code {
    font-family: var(--mono);
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 3px;
    padding: 0.05em 0.35em;
    font-size: 0.95em;
    color: var(--ink);
  }

  /* --- Toolbar --- */
  .toolbar {
    position: sticky; top: 0; z-index: 10;
    background: var(--paper);
    border-bottom: 1px solid var(--rule);
    padding: 1rem 0 0.875rem;
    margin: 2rem 0 0;
    display: flex; flex-direction: column; gap: 0.875rem;
  }
  .toolrow { display: flex; flex-wrap: wrap; gap: 0.625rem; align-items: center; }

  .search {
    flex: 1 1 15rem;
    font: inherit;
    color: var(--ink);
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 5px;
    padding: 0.5rem 0.75rem;
  }
  .search::placeholder { color: var(--muted); }
  .search:focus-visible, .chip:focus-visible, .btn:focus-visible, .tile:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  .progress {
    font-family: var(--mono);
    font-size: var(--step--1);
    font-variant-numeric: tabular-nums;
    color: var(--muted);
    white-space: nowrap;
  }
  .progress b { color: var(--ink); font-weight: 500; }

  .btn {
    font: inherit;
    font-size: var(--step--1);
    color: var(--ink);
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 5px;
    padding: 0.45rem 0.8rem;
    cursor: pointer;
  }
  .btn:hover { border-color: var(--accent); color: var(--accent); }

  .chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .chip {
    font: inherit;
    font-size: var(--step--1);
    color: var(--muted);
    background: transparent;
    border: 1px solid var(--rule);
    border-radius: 999px;
    padding: 0.3rem 0.7rem;
    cursor: pointer;
    display: inline-flex; gap: 0.4rem; align-items: baseline;
  }
  .chip:hover { color: var(--ink); border-color: var(--muted); }
  .chip .n { font-family: var(--mono); font-variant-numeric: tabular-nums; opacity: 0.75; }
  .chip[aria-pressed="true"] {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--accent-ink);
  }
  .chip[aria-pressed="true"] .n { opacity: 0.85; }

  /* --- Role sections --- */
  .role { margin-top: 2.5rem; }
  .role-head {
    display: flex; align-items: baseline; gap: 0.75rem;
    border-bottom: 1px solid var(--rule);
    padding-bottom: 0.5rem; margin-bottom: 1.25rem;
  }
  .role-head h2 {
    font-size: var(--step-2); font-weight: 600; letter-spacing: -0.01em; margin: 0;
  }
  .role-head .n {
    font-family: var(--mono); font-size: var(--step--1);
    color: var(--muted); font-variant-numeric: tabular-nums;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(11.25rem, 1fr));
    gap: 0.875rem;
  }

  /* --- Badge tile --- */
  .tile {
    display: flex; flex-direction: column; gap: 0.5rem;
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 6px;
    padding: 0.875rem;
    text-align: left;
    font: inherit; color: inherit;
    cursor: pointer;
  }
  .tile:hover { border-color: var(--accent); }
  .tile[data-done="true"] { background: var(--done); border-color: var(--done-ink); }
  .tile[data-done="true"] .name { color: var(--done-ink); }

  .qr {
    width: 100%; aspect-ratio: 1; display: block;
    background: var(--qr-ground);
    border-radius: 3px;
    /* QR codes are small bitmaps; smoothing them on upscale blurs the modules
       and can defeat a scanner. Keep the edges hard. */
    image-rendering: pixelated;
  }
  .name { font-weight: 600; line-height: 1.25; text-wrap: balance; }
  .org { color: var(--muted); font-size: var(--step--1); }
  /* Shown only where the section heading does not already name the role -
     i.e. the dual-role tiles. */
  .roles {
    font-size: var(--step--1);
    font-weight: 500;
    color: var(--accent);
    line-height: 1.3;
  }
  .file {
    font-family: var(--mono); font-size: 0.6875rem;
    color: var(--muted); word-break: break-all; line-height: 1.35;
  }
  .mark {
    font-family: var(--mono); font-size: var(--step--1);
    color: var(--done-ink); font-weight: 500;
  }
  .tile[data-done="false"] .mark { visibility: hidden; }

  .empty { color: var(--muted); padding: 2rem 0; }

  @media (prefers-reduced-motion: no-preference) {
    .tile, .chip, .btn { transition: border-color 120ms ease, background 120ms ease, color 120ms ease; }
  }

  /* --- Print: the sheet the badge table actually works from --- */
  @media print {
    :root { --paper: #FFF; --surface: #FFF; --ink: #000; --muted: #444; --rule: #BBB; }
    .toolbar, .howto, .btn { display: none !important; }
    body { background: #FFF; }
    .wrap { max-width: none; padding: 0; }
    .role { break-inside: auto; margin-top: 1.5rem; }
    .role-head { break-after: avoid; }
    .grid { grid-template-columns: repeat(4, 1fr); gap: 0.5rem; }
    .tile { break-inside: avoid; border-color: #BBB; }
    /* Keep printed codes near 1in so a phone camera locks on reliably. */
    .qr { width: 1.05in; height: 1.05in; margin: 0 auto; }
  }
</style>

<div class="wrap">
  <header class="masthead">
    <div class="eyebrow">ICAOS &middot; Annual Business Meeting</div>
    <h1>Nametag QR Assembly</h1>
    <p class="lede">
      Every attendee&rsquo;s scan-to-save QR code, grouped by role. Scanning one
      opens the phone&rsquo;s Add&nbsp;Contact screen with that person&rsquo;s details
      already filled in.
    </p>
    <div class="howto">
      <div><b>To place a code:</b> find the person, then use the file named under their QR &mdash; it lives in <code>qrcodes/</code> in the repo.</div>
      <div><b>Click a tile</b> once the code is on their nametag. Progress is saved in this browser, so you can close the page and come back.</div>
      <div><b>Print</b> for a paper worksheet &mdash; codes print at about 1&nbsp;inch, the smallest size that scans reliably.</div>
    </div>
  </header>

  <div class="toolbar">
    <div class="toolrow">
      <input class="search" id="q" type="search" placeholder="Search a name, state, or file name" aria-label="Search attendees">
      <span class="progress" id="progress"></span>
      <button class="btn" id="print" type="button">Print</button>
      <button class="btn" id="reset" type="button">Clear progress</button>
    </div>
    <div class="chips" id="chips"></div>
  </div>

  <main id="out"></main>
</div>

<script>
  const DATA = __DATA__;
  const KEY = "abm-nametag-progress";

  // Progress is a convenience for one person working through a long manual
  // task, so a browser that blocks storage should degrade to "nothing saved"
  // rather than break the page.
  let done = new Set();
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) done = new Set(JSON.parse(raw));
  } catch (e) { /* storage unavailable; run without persistence */ }

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify([...done])); } catch (e) {}
  }

  let role = null;      // null = every role
  let query = "";

  const out = document.getElementById("out");
  const chips = document.getElementById("chips");
  const progress = document.getElementById("progress");

  function matches(p) {
    if (role && p.group !== role) return false;
    if (!query) return true;
    const hay = (p.name + " " + p.org + " " + p.slug + " " + p.title + " " + p.group).toLowerCase();
    return hay.includes(query);
  }

  function renderChips() {
    const all = document.createElement("button");
    all.className = "chip";
    all.type = "button";
    all.setAttribute("aria-pressed", role === null);
    all.innerHTML = 'All roles <span class="n">' + DATA.people.length + '</span>';
    all.onclick = () => { role = null; render(); };
    chips.replaceChildren(all);

    DATA.order.forEach(t => {
      const b = document.createElement("button");
      b.className = "chip";
      b.type = "button";
      b.setAttribute("aria-pressed", role === t);
      b.innerHTML = escapeHtml(t) + ' <span class="n">' + DATA.counts[t] + '</span>';
      b.onclick = () => { role = (role === t ? null : t); render(); };
      chips.append(b);
    });
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function tile(p) {
    const el = document.createElement("button");
    el.className = "tile";
    el.type = "button";
    el.dataset.done = done.has(p.slug);
    el.setAttribute("aria-pressed", done.has(p.slug));
    el.innerHTML =
      '<img class="qr" alt="QR code for ' + escapeHtml(p.name) + '" src="data:image/png;base64,' + p.qr + '">' +
      '<span class="name">' + escapeHtml(p.name) + '</span>' +
      (p.org ? '<span class="org">' + escapeHtml(p.org) + '</span>' : '') +
      (p.title !== p.group ? '<span class="roles">' + escapeHtml(p.title) + '</span>' : '') +
      '<span class="file">' + escapeHtml(p.slug) + '.png</span>' +
      '<span class="mark">&check; placed</span>';
    el.onclick = () => {
      done.has(p.slug) ? done.delete(p.slug) : done.add(p.slug);
      el.dataset.done = done.has(p.slug);
      el.setAttribute("aria-pressed", done.has(p.slug));
      save();
      updateProgress();
    };
    return el;
  }

  function updateProgress() {
    progress.innerHTML = '<b>' + done.size + '</b> of ' + DATA.people.length + ' placed';
  }

  function render() {
    renderChips();
    const shown = DATA.people.filter(matches);
    out.replaceChildren();

    if (!shown.length) {
      const p = document.createElement("p");
      p.className = "empty";
      p.textContent = "No attendee matches that search.";
      out.append(p);
      updateProgress();
      return;
    }

    DATA.order.forEach(t => {
      const group = shown.filter(p => p.group === t);
      if (!group.length) return;

      const sec = document.createElement("section");
      sec.className = "role";
      const head = document.createElement("div");
      head.className = "role-head";
      head.innerHTML = "<h2>" + escapeHtml(t) + '</h2><span class="n">' +
        group.length + (group.length === DATA.counts[t] ? "" : " of " + DATA.counts[t]) + "</span>";
      const grid = document.createElement("div");
      grid.className = "grid";
      group.forEach(p => grid.append(tile(p)));
      sec.append(head, grid);
      out.append(sec);
    });
    updateProgress();
  }

  document.getElementById("q").addEventListener("input", e => {
    query = e.target.value.trim().toLowerCase();
    render();
  });
  document.getElementById("print").onclick = () => window.print();
  document.getElementById("reset").onclick = () => {
    if (!done.size || confirm("Clear all " + done.size + " placement marks?")) {
      done.clear(); save(); render();
    }
  };

  render();
</script>
'''

OUTPUT = "nametag-sheet.html"
CONTACTS_DIR = "contacts"
QRCODES_DIR = "qrcodes"
SOURCE_XLSX = "NameTag_Data_1.xlsx"


def unescape(value: str) -> str:
    """Undo the vCard escaping applied by generate.py, for display."""
    return value.replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def read_card(path: str) -> dict:
    """Parse the handful of vCard fields the sheet displays."""
    fields = {}
    for line in open(path).read().splitlines():
        key, _, value = line.partition(":")
        if key and value:
            fields.setdefault(key.split(";")[0], value)
    return fields


def section_for(title: str, org: str) -> str:
    """
    Decide which section an attendee belongs in.

    Both special cases are derived rather than hardcoded, so new people fall
    into the right section without touching this script:

    - A comma in the title only ever comes from generate.py merging two roles
      for one person, which makes it a reliable dual-role marker.
    - ICAOS staff all carry ORG:ICAOS and each hold a distinct job title,
      which would otherwise scatter them across one-person sections.
    """
    if ", " in title:
        return "Dual Role"
    if org == "ICAOS":
        return "ICAOS Staff"
    return title


def check_cards_are_current() -> None:
    """
    Refuse to build from cards that are older than the spreadsheet.

    This script reads contacts/, not the spreadsheet, so running it before
    generate.py silently produces a sheet built from the previous data - and
    a stale sheet is not obviously stale. It looks completely normal right up
    until someone at the badge table works from the wrong titles. Comparing
    timestamps makes that mistake impossible to make quietly, whichever order
    the two scripts are run in.

    The check is skipped when the spreadsheet is absent, which is the normal
    state of a fresh clone - it is gitignored, since it holds real contact
    details.
    """
    if not os.path.exists(SOURCE_XLSX):
        return

    cards = glob.glob(f"{CONTACTS_DIR}/*.vcf")
    if not cards:
        return

    newest_card = max(os.path.getmtime(path) for path in cards)
    if os.path.getmtime(SOURCE_XLSX) <= newest_card:
        return

    raise SystemExit(
        f"{SOURCE_XLSX} is newer than the cards in {CONTACTS_DIR}/.\n"
        "Building now would produce a sheet from the previous data.\n\n"
        "Regenerate the cards first, then build the sheet:\n\n"
        "    python3 generate.py && python3 build_sheet.py\n"
    )


def collect() -> dict:
    people = []
    for path in sorted(glob.glob(f"{CONTACTS_DIR}/*.vcf")):
        slug = os.path.basename(path)[:-4]
        qr_path = os.path.join(QRCODES_DIR, f"{slug}.png")
        if not os.path.exists(qr_path):
            raise SystemExit(
                f"No QR code for {slug!r}. Run generate.py first so that "
                f"{CONTACTS_DIR}/ and {QRCODES_DIR}/ agree."
            )

        fields = read_card(path)
        title = unescape(fields.get("TITLE", "(no title)"))
        org = unescape(fields.get("ORG", ""))

        people.append({
            "slug": slug,
            "name": unescape(fields.get("FN", slug)),
            "last": unescape(fields.get("N", ";").split(";")[0]),
            "org": org,
            "title": title,
            "group": section_for(title, org),
            "qr": base64.b64encode(open(qr_path, "rb").read()).decode(),
        })

    counts = collections.Counter(person["group"] for person in people)

    # Biggest cohorts first - the order a badge table is actually worked
    # through - then alphabetically within each section.
    order = sorted(counts, key=lambda group: (-counts[group], group))
    people.sort(key=lambda p: (order.index(p["group"]),
                               p["last"].lower(), p["name"].lower()))

    return {"people": people, "order": order, "counts": counts}


def main():
    check_cards_are_current()

    data = collect()
    if not data["people"]:
        raise SystemExit(
            f"No cards found in {CONTACTS_DIR}/. Run generate.py first."
        )

    page = TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    with open(OUTPUT, "w") as handle:
        handle.write(page)

    print(f"Wrote {OUTPUT} - {len(data['people'])} attendee(s), "
          f"{len(data['order'])} section(s), "
          f"{os.path.getsize(OUTPUT) / 1024:.0f} KB\n")
    for group in data["order"]:
        print(f"  {data['counts'][group]:>4}  {group}")


if __name__ == "__main__":
    main()
