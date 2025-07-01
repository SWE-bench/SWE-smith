"""
A terminal-based viewer for issue generation results using Textual.
"""

from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Header, Footer, Static
from textual.binding import Binding
from pathlib import Path
import json
from typing import Any
from rich.markup import escape


class MessageView(Static):
    """A widget to display formatted messages."""

    def __init__(self, problem_statement: str, messages: list):
        content = self._format_content(problem_statement, messages)
        super().__init__(content, markup=False)

    def _format_content(self, problem_statement: str, messages: list) -> str:
        formatted = []
        # Add problem statement with explicit markup
        formatted.append("### Problem Statement ###")
        formatted.append(escape(problem_statement))
        formatted.append("─" * 80)
        formatted.append("\n### Messages ###")

        # Add messages
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted.append(f"{role.upper()}:")
            formatted.append(escape(content))
            formatted.append("─" * 80)
        return "\n".join(formatted)


class IssueViewer(App):
    """Main application for viewing issue generation results."""

    CSS = """
    #content {
        height: 1fr;  /* Take up remaining space */
        padding: 1 2;
        background: $surface;
        border: solid $primary;
        margin: 1 2;
        overflow-y: scroll;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("h", "prev_folder", "Previous Folder"),
        Binding("l", "next_folder", "Next Folder"),
        Binding("j", "scroll_down", "Scroll Down"),
        Binding("k", "scroll_up", "Scroll Up"),
    ]

    def __init__(self, root_dir: str):
        super().__init__()
        self.root_dir = Path(root_dir)
        self.folders: list[Path] = []
        self.current_index = 0
        self._find_valid_folders()

    def _find_valid_folders(self) -> None:
        """Find all folders that contain both messages.json and metadata.json recursively."""

        def is_valid_folder(path: Path) -> bool:
            return (path / "messages.json").exists() and (
                path / "metadata.json"
            ).exists()

        def search_recursively(path: Path) -> None:
            if is_valid_folder(path):
                self.folders.append(path)

            # Search in subdirectories
            for item in path.iterdir():
                if item.is_dir():
                    search_recursively(item)

        # Start recursive search from root directory
        search_recursively(self.root_dir)
        self.folders.sort()

    def _load_data(self, folder: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Load messages and metadata from a folder."""
        with open(folder / "messages.json") as f:
            messages = json.load(f)
        with open(folder / "metadata.json") as f:
            metadata = json.load(f)
        return messages, metadata

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield ScrollableContainer(Static(""), id="content")
        yield Footer()

    def on_mount(self) -> None:
        """Handle app start-up."""
        self.update_view()

    def update_view(self) -> None:
        """Update the display with current folder data."""
        if not self.folders:
            self.query_one("#content").remove_children()
            self.query_one("#content").mount(Static("No valid folders found!"))
            return

        current_folder = self.folders[self.current_index]
        messages, metadata = self._load_data(current_folder)

        # Update title
        self.title = f"Folder: {current_folder.name} [{self.current_index + 1}/{len(self.folders)}]"

        # Get problem statement
        problem = metadata.get("responses", {}).get(
            "problem_statement", "No problem statement found"
        )

        # Create combined view
        content_widget = MessageView(problem, messages)
        self.query_one("#content").remove_children()
        self.query_one("#content").mount(content_widget)

    def action_prev_folder(self) -> None:
        """Handle previous folder action."""
        if self.folders:
            self.current_index = (self.current_index - 1) % len(self.folders)
            self.update_view()
            # Reset scroll position
            self.query_one("#content").scroll_y = 0

    def action_next_folder(self) -> None:
        """Handle next folder action."""
        if self.folders:
            self.current_index = (self.current_index + 1) % len(self.folders)
            self.update_view()
            # Reset scroll position
            self.query_one("#content").scroll_y = 0

    def action_scroll_down(self) -> None:
        """Scroll content down."""
        content = self.query_one("#content")
        content.scroll_y += 10

    def action_scroll_up(self) -> None:
        """Scroll content up."""
        content = self.query_one("#content")
        content.scroll_y = max(0, content.scroll_y - 10)


def main() -> None:
    """Entry point for the viewer."""
    import sys

    if len(sys.argv) != 2:
        print("Usage: python viewer.py <root_directory>")
        sys.exit(1)

    app = IssueViewer(sys.argv[1])
    app.run()


if __name__ == "__main__":
    main()
