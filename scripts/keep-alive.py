"""Keep NotebookLM session alive by running a persistent browser.

This script keeps a Chromium browser running that periodically visits
NotebookLM to prevent session expiration. The browser profile and
storage state are automatically updated.

Usage:
    python keep-alive.py                    # Default: refresh every 30 mins
    python keep-alive.py --interval 15      # Refresh every 15 minutes
    python keep-alive.py --headless         # Run without visible browser (less reliable)

The browser window will stay open. You can minimize it.
Press Ctrl+C to stop.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: Playwright not installed.")
    print("Run: pip install playwright && playwright install chromium")
    sys.exit(1)


def get_paths():
    """Get paths for browser profile and storage state."""
    notebooklm_home = Path.home() / ".notebooklm"
    return {
        "browser_profile": notebooklm_home / "browser_profile",
        "storage_state": notebooklm_home / "storage_state.json",
    }


def keep_alive(interval_minutes: int = 30, headless: bool = False):
    """Keep the NotebookLM session alive.

    Args:
        interval_minutes: How often to refresh the page (default: 30)
        headless: Run in headless mode (less reliable, Google may block)
    """
    paths = get_paths()

    print("=" * 60)
    print("NotebookLM Keep-Alive Script")
    print("=" * 60)
    print(f"Browser profile: {paths['browser_profile']}")
    print(f"Storage state: {paths['storage_state']}")
    print(f"Refresh interval: {interval_minutes} minutes")
    print(f"Headless mode: {headless}")
    print("=" * 60)
    print()
    print("The browser will stay open. Minimize it if needed.")
    print("Press Ctrl+C to stop.")
    print()

    with sync_playwright() as p:
        # Launch persistent context (same as login command)
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(paths["browser_profile"]),
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--password-store=basic",
            ],
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else context.new_page()

        try:
            refresh_count = 0
            while True:
                refresh_count += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                print(f"[{timestamp}] Refresh #{refresh_count}: Visiting NotebookLM...")

                try:
                    # Visit NotebookLM to keep session alive
                    page.goto("https://notebooklm.google.com/", timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=30000)

                    # Check if we're on the right page
                    current_url = page.url
                    if "accounts.google.com" in current_url:
                        print(f"[{timestamp}] WARNING: Redirected to login!")
                        print("Session may have expired. Please log in manually in the browser.")
                        print("After logging in, the script will continue.")
                        # Wait for user to log in
                        page.wait_for_url("**/notebooklm.google.com/**", timeout=300000)

                    # Save updated storage state
                    context.storage_state(path=str(paths["storage_state"]))
                    print(f"[{timestamp}] Success! Session refreshed and saved.")

                except Exception as e:
                    print(f"[{timestamp}] Error during refresh: {e}")
                    print("Will retry on next interval...")

                # Wait for next refresh
                print(f"[{timestamp}] Next refresh in {interval_minutes} minutes...")
                print()
                time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            print()
            print("Stopping keep-alive script...")
            # Save final state before closing
            context.storage_state(path=str(paths["storage_state"]))
            print("Final storage state saved.")
        finally:
            context.close()
            print("Browser closed.")


def main():
    parser = argparse.ArgumentParser(
        description="Keep NotebookLM session alive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=30,
        help="Refresh interval in minutes (default: 30)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (less reliable)"
    )

    args = parser.parse_args()
    keep_alive(interval_minutes=args.interval, headless=args.headless)


if __name__ == "__main__":
    main()
