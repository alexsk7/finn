#!/usr/bin/env python3
"""Prompt for a user name on first run if none is set in profile.json."""

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from app.profile import get_profile, save_profile


def main() -> None:
    profile = get_profile()
    if profile.get("user_name"):
        return

    print()
    print("  Welcome to finn!")
    print("  What's your name? (used for the dashboard greeting)")
    print()
    try:
        name = input("  Your name: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if name:
        save_profile(name, profile.get("currency_symbol", "$"))
        print(f"  Got it — welcome, {name}.")
    print()


if __name__ == "__main__":
    main()
