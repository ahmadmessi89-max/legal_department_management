"""Build the workspace's vendored static assets (stream W), following
docs/ldm/briefs/design-direction.md.

1. Fonts (SIL OFL 1.1), as woff2, Arabic and Latin subsets only:
   Noto Kufi Arabic 600-700 (headings, matter numbers), IBM Plex Sans Arabic
   400/500/600 (text) and IBM Plex Sans 400-600 (Latin text). Downloaded once
   from Google Fonts with their licences into
   custom_addons/legal_department_management/static/lib/fonts/<family>/, and
   declared in static/src/scss/ldm_fonts.scss under module-scoped family names
   ("Ldm Kufi", "Ldm Plex Arabic", "Ldm Plex") so they never clash with another
   declaration. Served from the module itself: nothing is fetched from a CDN at
   run time, so an air-gapped office network gets the same type.
2. A subset of Lucide icons (ISC) as SVG files, from the lucide-react package
   installed for the owner's dma_react project, plus a generated SCSS map
   (static/src/scss/ldm_icons.scss) that draws each icon as a CSS mask in
   currentColor, so an icon takes the colour and size of its text and needs no
   inline style (component: static/src/core/ldm_icon.js).

Run with network access:
    py -3.11 docs/ldm/tools/gen_ws_assets.py
Re-run after adding a name to ICONS. Output is committed; nothing runs at
install time.
"""
import json
import pathlib
import re
import shutil
import sys
import urllib.request
from urllib.parse import quote

ROOT = pathlib.Path(__file__).resolve().parents[3]
MODULE = ROOT / "custom_addons" / "legal_department_management"
LUCIDE = pathlib.Path(r"C:\Users\Lenovo\Documents\dma_react\node_modules\lucide-react")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

ICONS = [
    "arrow-left", "arrow-right", "badge-check", "banknote", "briefcase", "building-2", "calendar",
    "calendar-check", "calendar-clock", "calendar-days", "calendar-x", "camera", "check", "chevron-down",
    "chevron-left", "chevron-right", "chevron-up", "circle", "circle-alert", "circle-check", "circle-dot",
    "circle-x", "clipboard-list", "clock", "ellipsis", "file-check", "file-clock", "file-signature", "file-text",
    "file-x", "flag", "folder-open", "gavel", "hourglass", "inbox", "info", "landmark", "list-checks", "lock",
    "mail", "map-pin", "minus", "pencil", "plus", "printer", "receipt", "refresh-cw", "route", "scale",
    "scroll-text", "search", "shield-alert", "shield-check", "square", "square-check-big", "stamp",
    "triangle-alert", "undo-2", "upload", "user", "user-x", "users", "wallet", "x",
    # the first screen's actions and tiles
    "arrow-up-left", "arrow-up-right", "chart-column", "contact-round", "folder-plus", "hand-coins", "mail-plus",
    "send",
]

# (Google family, module family, folder, weights, subsets, licence path in google/fonts)
FONTS = [
    ("Noto Kufi Arabic", "Ldm Kufi", "noto-kufi-arabic", "600;700", ("arabic", "latin"), "ofl/notokufiarabic"),
    ("IBM Plex Sans Arabic", "Ldm Plex Arabic", "ibm-plex-sans-arabic", "400;500;600", ("arabic", "latin"),
     "ofl/ibmplexsansarabic"),
    ("IBM Plex Sans", "Ldm Plex", "ibm-plex-sans", "400;500;600", ("latin",), "ofl/ibmplexsans"),
]
BLOCK = re.compile(r"/\* ([\w-]+) \*/\s*@font-face \{(.*?)\}", re.S)


def fetch(url, binary=False):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    return data if binary else data.decode("utf-8")


def build_fonts():
    base = MODULE / "static" / "lib" / "fonts"
    if base.exists():
        shutil.rmtree(base)
    faces = []
    for google, family, folder, weights, subsets, licence in FONTS:
        target = base / folder
        target.mkdir(parents=True)
        (target / "OFL.txt").write_bytes(
            fetch(f"https://raw.githubusercontent.com/google/fonts/main/{licence}/OFL.txt", binary=True))
        css = fetch(f"https://fonts.googleapis.com/css2?family={quote(google)}:wght@{weights}&display=swap")
        # One file can serve several weights (variable fonts): merge them.
        files = {}
        for subset, body in BLOCK.findall(css):
            if subset not in subsets:
                continue
            weight = int(re.search(r"font-weight: (\d+)", body).group(1))
            url = re.search(r"url\((.*?)\)", body).group(1)
            ranges = re.search(r"unicode-range: (.*?);", body).group(1)
            entry = files.setdefault(url, {"subset": subset, "weights": [], "ranges": ranges})
            entry["weights"].append(weight)
        for url, entry in files.items():
            low, high = min(entry["weights"]), max(entry["weights"])
            name = f"{folder}-{entry['subset']}-{low}" + (f"-{high}" if high != low else "") + ".woff2"
            (target / name).write_bytes(fetch(url, binary=True))
            faces.append((family, low, high, f"{folder}/{name}", entry["ranges"]))
            print("font", name, (target / name).stat().st_size)
    lines = [
        "// Generated by docs/ldm/tools/gen_ws_assets.py (design-direction.md). Do not edit.",
        "// Noto Kufi Arabic, IBM Plex Sans Arabic and IBM Plex Sans: SIL Open Font Licence 1.1",
        "// (static/lib/fonts/*/OFL.txt). Served from this module; the family names are the",
        "// module's own so they never clash, and they are applied inside `.o_ldm` only.",
        "",
    ]
    for family, low, high, path, ranges in faces:
        weight = f"{low} {high}" if high != low else f"{low}"
        lines += [
            "@font-face {",
            f'    font-family: "{family}";',
            "    font-style: normal;",
            f"    font-weight: {weight};",
            "    font-display: swap;",
            f'    src: url("/legal_department_management/static/lib/fonts/{path}") format("woff2");',
            f"    unicode-range: {ranges};",
            "}",
            "",
        ]
    (MODULE / "static" / "src" / "scss" / "ldm_fonts.scss").write_text("\n".join(lines), encoding="utf-8", newline="\n")


NODE = re.compile(r'\[\s*"(\w+)",\s*(\{[^}]*\})\s*\]')


def icon_svg(name):
    source = LUCIDE / "dist" / "esm" / "icons" / f"{name}.mjs"
    if not source.exists():
        sys.exit(f"Lucide has no icon named {name!r}")
    text = source.read_text(encoding="utf-8")
    alias = re.search(r"export \{ default \} from '\./([\w-]+)\.mjs'", text)
    if alias:  # renamed icons re-export their new name
        return icon_svg(alias.group(1))
    body = text[text.index("__iconNode = ["):text.index("];")]
    parts = []
    for tag, attrs in NODE.findall(body):
        attrs = re.sub(r'(\w+):', r'"\1":', attrs)
        values = json.loads(attrs)
        values.pop("key", None)
        attr_text = " ".join(f'{k}="{v}"' for k, v in values.items())
        parts.append(f"<{tag} {attr_text}/>")
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            + "".join(parts) + "</svg>")


def build_icons():
    target = MODULE / "static" / "lib" / "lucide"
    icons_dir = target / "icons"
    if icons_dir.exists():
        shutil.rmtree(icons_dir)
    icons_dir.mkdir(parents=True)
    shutil.copy(LUCIDE / "LICENSE", target / "LICENSE")
    version = json.loads((LUCIDE / "package.json").read_text(encoding="utf-8"))["version"]
    scss = [
        "// Generated by docs/ldm/tools/gen_ws_assets.py from Lucide " + version + " (ISC licence,",
        "// static/lib/lucide/LICENSE). Do not edit: add the name to ICONS and re-run.",
        "// Each icon is a mask painted in currentColor, so it follows the text colour and size.",
        "",
    ]
    for name in ICONS:
        svg = icon_svg(name)
        (icons_dir / f"{name}.svg").write_text(svg, encoding="utf-8", newline="\n")
        # Masks only need the shape: paint it black in the data URI.
        mask = svg.replace('stroke="currentColor"', 'stroke="black"').replace('"', "'")
        data = quote(mask, safe=" =:/'")
        scss.append(f'.o_ldm_icon_{name} {{ --ldm-icon: url("data:image/svg+xml,{data}"); }}')
    (MODULE / "static" / "src" / "scss" / "ldm_icons.scss").write_text("\n".join(scss) + "\n", encoding="utf-8", newline="\n")
    (target / "README.md").write_text(
        f"Lucide {version} icons (ISC licence, see LICENSE), the subset the legal workspace uses.\n"
        "Generated by docs/ldm/tools/gen_ws_assets.py; drawn through the LdmIcon component.\n",
        encoding="utf-8", newline="\n")
    print("icons", len(ICONS))


if __name__ == "__main__":
    # Icons by default. The FONTS list above is the first design's (Kufi, Plex);
    # the ANU identity's fonts (Inter Tight, Tajawal, Roboto Mono) were placed
    # by hand, so --fonts would replace them with the old families.
    build_icons()
    if "--fonts" in sys.argv:
        build_fonts()
