from __future__ import annotations

import os
import sys


def main() -> int:
    """
    Cross-platform launcher for the Streamlit app.

    Usage:
      python run.py
    """
    # Ensure imports work when launched from arbitrary CWD (common on Windows).
    repo_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(repo_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from streamlit.web import cli as stcli

    sys.argv = ["streamlit", "run", os.path.join(repo_root, "app.py")]
    return stcli.main()


if __name__ == "__main__":
    raise SystemExit(main())

