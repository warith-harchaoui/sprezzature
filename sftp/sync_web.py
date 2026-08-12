#!/usr/bin/env python3
"""
sync_web — deploy the sprezzature.ai static site (web/) via sftp-helper.

sftp-helper (https://github.com/warith-harchaoui/sftp-helper) has no
built-in recursive directory sync, so this script walks web/ locally and
drives that library API one file at a time, mirroring the same relative
path under the server's sftp_destination_path (see
sftp/settings.yaml.example). With --prune, it also lists the remote tree
recursively and removes any remote file that no longer exists locally, so
the deploy is a true mirror rather than an upload-only push.

Upload rule: a file is only sent if it is not already present remotely, its
size differs from the remote copy, or the local source is newer (mtime) --
everything else is skipped, so a re-run only pushes what actually changed.
One sftph.list_dir_stat() call fetches size+mtime for the whole remote tree
up front (one round trip per remote directory level, not per file), so
every local file's skip/upload decision is then made in memory. Pass
--force to upload every selected file regardless of this rule.

Setup
-----
    cp sftp/settings.yaml.example sftp/settings.yaml   # then fill in real creds
    pip install sftp-helper

Usage
-----
    python sftp/sync_web.py --dry-run          # preview what would upload/skip
    python sftp/sync_web.py                    # real upload, asks to confirm
    python sftp/sync_web.py --yes               # real upload, no prompt
    python sftp/sync_web.py --only figures.html img/figures/bar.png
    python sftp/sync_web.py --prune             # also delete remote-only files
    python sftp/sync_web.py --prune --dry-run   # preview uploads AND deletions
    python sftp/sync_web.py --force             # re-upload every selected file, skip the skip-rule

This is a deploy to a live server — review --dry-run output first, and
--prune --dry-run before ever passing --prune for real.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import os_helper as osh

try:
    import sftp_helper as sftph
except ImportError:
    osh.error("sftp-helper is not installed. Run: pip install sftp-helper")
    sys.exit(1)

REPO = Path(__file__).resolve().parent.parent
WEB = REPO / "web"
DEFAULT_CONFIG = Path(__file__).resolve().parent / "settings.yaml"

# Never uploaded: build/editor cruft, not part of the published site.
_SKIP_NAMES = {".DS_Store", "__pycache__", "Thumbs.db"}
_SKIP_SUFFIXES = {".pyc"}

# ls -l gives the remote mtime at minute resolution with no timezone info
# (see sftp_helper.remote_stat's docstring), so "source is newer" needs some
# slack to avoid re-uploading a file whose real mtime just rounds differently
# on each side. Two minutes comfortably covers that rounding without masking
# a genuine same-day edit.
_MTIME_SLACK = timedelta(minutes=2)


def discover_files() -> list[Path]:
    """Every web/ file to publish, sorted for stable, resumable output."""
    files = []
    for p in WEB.rglob("*"):
        if not p.is_file():
            continue
        if p.name in _SKIP_NAMES or p.suffix in _SKIP_SUFFIXES:
            continue
        if "__pycache__" in p.parts:
            continue
        files.append(p)
    return sorted(files)


def rel_path_for(local_file: Path) -> str:
    """The web/-relative POSIX path used as the key into the remote stat map."""
    return local_file.relative_to(WEB).as_posix()


def remote_path_for(local_file: Path, dest_root: str) -> str:
    """The remote SFTP path a local web/ file maps to, under `dest_root`."""
    root = dest_root.rstrip("/") if dest_root and dest_root != "/" else ""
    return f"{root}/{rel_path_for(local_file)}"


def fetch_remote_tree(cred: dict, dest_root: str) -> dict[str, dict]:
    """The whole remote tree's ``{relative_path: {"size", "mtime"}}``.

    Empty dict when `dest_root` does not exist yet (a first-time deploy) or
    is empty — never raises for that case, since "nothing there yet" simply
    means every local file is new.

    Parameters
    ----------
    cred : dict
        sftp-helper credentials dict.
    dest_root : str
        Remote base directory the site is published under.
    """
    try:
        return sftph.list_dir_stat(dest_root or "/", cred)
    except Exception as exc:  # noqa: BLE001 - a missing/empty remote root is expected on first deploy
        osh.info(f"Remote tree unreadable or absent ({exc}); treating as empty (first deploy).")
        return {}


def should_upload(local_file: Path, remote_tree: dict[str, dict], *, force: bool) -> bool:
    """Apply the skip rule: upload iff missing remotely, size differs, or source is newer."""
    if force:
        return True
    remote_entry = remote_tree.get(rel_path_for(local_file))
    if remote_entry is None:
        return True
    stat = local_file.stat()
    if stat.st_size != remote_entry["size"]:
        return True
    local_mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(tzinfo=None)
    return local_mtime > remote_entry["mtime"] + _MTIME_SLACK


def find_orphaned_remote_files(remote_tree: dict[str, dict], local_files: list[Path]) -> list[str]:
    """Remote-relative paths present in `remote_tree` but not among `local_files`."""
    wanted = {rel_path_for(f) for f in local_files}
    return sorted(p for p in remote_tree if p not in wanted)


def main() -> int:
    osh.init_logging()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to sftp/settings.yaml (default: sftp/settings.yaml next to this script).")
    p.add_argument("--dry-run", action="store_true", help="List what would be uploaded/skipped (and pruned); no uploads or deletions.")
    p.add_argument("--yes", "-y", action="store_true", help="Skip the confirmation prompt (still not --dry-run).")
    p.add_argument("--only", nargs="*", default=None, help="Consider only files whose web/-relative path is in this list (e.g. figures.html img/figures/bar.png). Still subject to the skip rule unless --force.")
    p.add_argument("--prune", action="store_true", help="Also delete remote files with no local counterpart (true mirror sync). Off by default.")
    p.add_argument("--force", action="store_true", help="Upload every selected file regardless of the skip rule (ignore existing size/mtime on the server).")
    args = p.parse_args()

    if not WEB.is_dir():
        osh.error(f"web/ not found at {WEB}")
        return 1

    files = discover_files()
    if args.only:
        wanted = set(args.only)
        files = [f for f in files if rel_path_for(f) in wanted]
        missing = wanted - {rel_path_for(f) for f in files}
        if missing:
            osh.error(f"--only: not found under web/: {', '.join(sorted(missing))}")
            return 1

    if not files:
        osh.info("Nothing to consider.")
        return 0

    # --dry-run still needs real credentials to preview against the actual
    # remote tree (skip decisions, --prune orphans); without them it can only
    # list the full local candidate set.
    have_config = Path(args.config).is_file()
    cred = sftph.credentials(args.config) if have_config else None
    dest_root = (cred.get("sftp_destination_path", "") or "") if cred else ""
    remote_tree = fetch_remote_tree(cred, dest_root) if cred else {}

    to_upload = [f for f in files if should_upload(f, remote_tree, force=args.force)] if cred else files
    skipped = [f for f in files if f not in to_upload]

    orphans: list[str] = []
    if args.prune and cred:
        orphans = find_orphaned_remote_files(remote_tree, files)

    if args.dry_run:
        print(f"[dry-run] {len(to_upload)} file(s) would be uploaded from {WEB}:")
        for f in to_upload:
            print(f"  {rel_path_for(f)}")
        if not have_config:
            osh.warning(f"No credentials at {args.config} — skip-rule preview unavailable, showing the full candidate set as 'would upload'.")
        elif skipped:
            print(f"\n[dry-run] {len(skipped)} file(s) unchanged, would be skipped:")
            for f in skipped:
                print(f"  {rel_path_for(f)}")
        if args.prune:
            print(f"\n[dry-run] {len(orphans)} remote file(s) would be DELETED (--prune):")
            for o in orphans:
                print(f"  {o}")
        osh.info("Run without --dry-run (after filling in sftp/settings.yaml) to actually deploy.")
        return 0

    if not have_config or cred is None:
        osh.error(
            f"No credentials file at {args.config}. "
            "Copy the template first: cp sftp/settings.yaml.example sftp/settings.yaml"
            " — then fill in your real host/login/key."
        )
        return 1

    if not to_upload and not orphans:
        osh.info(f"Nothing to do: all {len(files)} file(s) already match the server.")
        return 0

    if not args.yes:
        osh.info(
            f"About to upload {len(to_upload)} file(s) ({len(skipped)} unchanged, skipped) "
            f"from {WEB} to {cred.get('sftp_host')}:{dest_root or '/'}"
        )
        if orphans:
            osh.warning(f"--prune will also DELETE {len(orphans)} remote file(s) with no local counterpart.")
        reply = input("Proceed? [y/N] ").strip().lower()
        if reply != "y":
            osh.info("Aborted.")
            return 1

    made_dirs: set[str] = set()
    failures: list[str] = []
    for i, local_file in enumerate(to_upload, 1):
        remote = remote_path_for(local_file, dest_root)
        remote_dir = remote.rsplit("/", 1)[0] or "/"
        if remote_dir not in made_dirs:
            sftph.make_remote_directory(remote_dir, cred)
            made_dirs.add(remote_dir)
        try:
            sftph.upload(str(local_file), cred, remote)
            osh.info(f"[{i}/{len(to_upload)}] uploaded {rel_path_for(local_file)}")
        except Exception as exc:  # noqa: BLE001 - report and keep going, summarize at the end
            osh.warning(f"[{i}/{len(to_upload)}] FAILED {rel_path_for(local_file)}: {exc}")
            failures.append(rel_path_for(local_file))

    pruned: list[str] = []
    for i, orphan in enumerate(orphans, 1):
        remote = f"{dest_root.rstrip('/')}/{orphan}" if dest_root and dest_root != "/" else f"/{orphan}"
        try:
            sftph.delete(remote, cred)
            osh.info(f"[prune {i}/{len(orphans)}] deleted {orphan}")
            pruned.append(orphan)
        except Exception as exc:  # noqa: BLE001 - report and keep going, summarize at the end
            osh.warning(f"[prune {i}/{len(orphans)}] FAILED to delete {orphan}: {exc}")
            failures.append(f"prune:{orphan}")

    if failures:
        osh.error(f"{len(failures)} failure(s):")
        for f in failures:
            osh.error(f" - {f}")
        return 1
    osh.info(
        f"Deployed {len(to_upload)} file(s) ({len(skipped)} unchanged, skipped) to "
        f"{cred.get('sftp_https', cred.get('sftp_host'))}"
        + (f", pruned {len(pruned)} remote-only file(s)" if args.prune else "") + "."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
