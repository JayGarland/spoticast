#!/usr/bin/env python3
"""One-shot migration: move single-user data to generated/users/{owner_id}/.

Run ONCE after deploying the multi-user patch if existing data needs to be preserved.
Old paths are left in place (not deleted) until migration is confirmed working.
"""

import shutil
import sys
from pathlib import Path

OLD_PROFILE_DIR = Path("generated") / "profile"
OLD_EPISODES_DIR = Path("generated") / "episodes"
OLD_VARIETY_DIR = Path("generated") / "variety"
OWNER_PATH = OLD_PROFILE_DIR / "owner_id"


def main() -> None:
    if not OWNER_PATH.exists():
        print("No owner_id found at generated/profile/owner_id — nothing to migrate.")
        sys.exit(0)

    owner_id = OWNER_PATH.read_text(encoding="utf-8").strip()
    if not owner_id:
        print("owner_id file is empty — nothing to migrate.")
        sys.exit(0)

    print(f"Migrating data for owner: {owner_id}")
    base = Path("generated") / "users" / owner_id

    # Profile
    new_profile_dir = base / "profile"
    new_profile_dir.mkdir(parents=True, exist_ok=True)
    for fname in ("profile.json", "feedback.jsonl"):
        src = OLD_PROFILE_DIR / fname
        if src.exists():
            dst = new_profile_dir / fname
            shutil.copy2(src, dst)
            print(f"  Copied {src} -> {dst}")

    # Episodes
    new_episodes_dir = base / "episodes"
    new_episodes_dir.mkdir(parents=True, exist_ok=True)
    if OLD_EPISODES_DIR.exists():
        for ep_dir in OLD_EPISODES_DIR.iterdir():
            if ep_dir.is_dir():
                dst = new_episodes_dir / ep_dir.name
                shutil.copytree(ep_dir, dst, dirs_exist_ok=True)
                print(f"  Copied episode {ep_dir.name}")

    # Variety memory
    new_variety_dir = base / "variety"
    new_variety_dir.mkdir(parents=True, exist_ok=True)
    if OLD_VARIETY_DIR.exists():
        for f in OLD_VARIETY_DIR.iterdir():
            if f.suffix == ".json":
                shutil.copy2(f, new_variety_dir / f.name)
                print(f"  Copied variety {f.name}")

    print("Migration complete. Old data preserved at original paths.")
    print(f"New data at: {base}")


if __name__ == "__main__":
    main()
