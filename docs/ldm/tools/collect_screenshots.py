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
    "03-gov": "3 - Government transactions (stream build, English)",
    "03-lit": "3 - Litigation and deadlines (stream build, English)",
    "03-ws": "3 - Workspace, My Day, cockpit (stream build, English)",
    "03-money": "3 - Money, fees, client money (stream build, English)",
    "03-reg": "3 - Registers and reports (stream build, English)",
    "05-design": "4 - Design pass (one identity on every screen)",
    "06-verify-main": "5 - Verification round 1 (every role, Arabic and English, desktop and phone)",
    "06-verify-recheck": "5 - Verification round 1, recheck after the fixes",
    "07-verify-final": "6 - Final verification round",
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
        for png in glob.glob(os.path.join(folder, "**", "*.png"), recursive=True):
            os.makedirs(dest, exist_ok=True)
            # a stream's sub-folders (final/, phone/) become a prefix of the file name
            relative = os.path.relpath(png, folder).replace(os.sep, " - ")
            out = os.path.join(dest, relative)
            if not os.path.exists(out) or os.path.getmtime(png) > os.path.getmtime(out):
                shutil.copy2(png, out)
                copied += 1
    with open(os.path.join(TARGET, "README.txt"), "w", encoding="utf-8") as fh:
        fh.write("Screenshots of the legal_department_management rebuild, by stage.\n"
                 "Stages 1-3 were taken while the streams were building, in English;\n"
                 "from stage 5 on, every screen is shown in Arabic and in English, at 1440 and 390 px wide.\n"
                 "Refresh: python docs/ldm/tools/collect_screenshots.py (in the odoo19 repository)\n")
    total = len(glob.glob(os.path.join(TARGET, "*", "*.png")))
    print(f"{copied} new or updated, {total} screenshots in {TARGET}")


if __name__ == "__main__":
    main()
