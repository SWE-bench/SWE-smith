#!/usr/bin/env python3

import sys

sys.path.append(".")

from swesmith.bug_gen.adapters.php import get_entities_from_file_php
from pathlib import Path


def main():
    test_file = Path("tests/test_logs/files/file.php")
    print(f"Testing with file: {test_file}")
    print(f"File exists: {test_file.exists()}")

    if not test_file.exists():
        print("File does not exist!")
        return

    try:
        entities = []
        get_entities_from_file_php(entities, str(test_file))
        print(f"Found {len(entities)} entities")

        for i, entity in enumerate(entities):
            print(
                f"{i + 1}. {entity.name} (lines {entity.line_start}-{entity.line_end})"
            )
            print(f"   Signature: {entity.signature}")
            print(f"   Type: {entity.node.type}")
            print()

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
