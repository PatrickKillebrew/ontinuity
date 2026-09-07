"""Retired laptop-seat entry point.

The Keyboard Helper was transferred to its separate private project before B1.
This public-repository module intentionally performs no network, filesystem, or
command operation.
"""

import sys


def main():
    print("laptop_seat retired: use the private Keyboard Helper project")
    return 2


if __name__ == "__main__":
    sys.exit(main())
