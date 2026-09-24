"""Gather every screenshot of the legal_department_management rebuild into one
folder, organised by stage, so they can be browsed without knowing where each
stream keeps its evidence.

Usage: python docs/ldm/tools/collect_screenshots.py [target]
Default target: C:/Users/Lenovo/Documents/LDM Screenshots
Re-run it any time: it copies new and changed files and never deletes.
"""
import glob
import os
import shutil
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
TARGET = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Lenovo\Documents\LDM Screenshots"
STAGES = {
    "00-baseline": "1 - Before (the showcase as received)",
    "02-foundation": "2 - Foundation",
    "03-gov": "3 - Government transactions (in progress)",
    "03-lit": "3 - Litigation and deadlines (in progress)",
    "03-ws": "3 - Workspace, My Day, cockpit (in progress)",
    "03-money": "3 - Money, fees, client money (in progress)",
    "03-reg": "3 - Registers and reports (in progress)",
}


def sources():
    """Evidence folders in the main checkout and in every stream worktree."""
    roots = [REPO] + sorted(glob.glob(os.path.join(REPO, ".claude", "worktrees", "*")))
    for root in roots:
        for folder in glob.glob(os.path.join(root, "docs", "ldm", "evidence", "*")):
            if os.path.isdir(folder):
                yield os.path.basename(folder), folder


def main():
    copied = 0
    for stage, folder in sources():
        label = STAGES.get(stage, stage)
        dest = os.path.join(TARGET, label)
        for png in glob.glob(os.path.join(folder, "*.png")):
            os.makedirs(dest, exist_ok=True)
            out = os.path.join(dest, os.path.basename(png))
            if not os.path.exists(out) or os.path.getmtime(png) > os.path.getmtime(out):
                shutil.copy2(png, out)
                copied += 1
    with open(os.path.join(TARGET, "README.txt"), "w", encoding="utf-8") as fh:
        fh.write("Screenshots of the legal_department_management rebuild, by stage.\n"
                 "Folders marked 'in progress' are refreshed as each build stream works;\n"
                 "labels stay English until the Arabic catalogue is added at integration.\n"
                 "Refresh: python docs/ldm/tools/collect_screenshots.py (in the odoo19 repository)\n")
    total = len(glob.glob(os.path.join(TARGET, "*", "*.png")))
    print(f"{copied} new or updated, {total} screenshots in {TARGET}")


if __name__ == "__main__":
    main()
