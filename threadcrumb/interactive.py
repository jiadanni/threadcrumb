"""
Interactive mode with rich terminal UI.
"""

from typing import List, Dict, Any, Optional
import sys


try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    from rich.progress import Progress
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class InteractiveMode:
    """Interactive CLI mode with rich UI."""

    def __init__(self):
        """Initialize interactive mode."""
        if not RICH_AVAILABLE:
            print("Rich library not installed. Install with: pip install rich")
            sys.exit(1)

        self.console = Console()

    def select_channels(
        self,
        channels: List[Dict[str, Any]],
        preselected: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Interactive channel selection.

        Args:
            channels: List of available channels
            preselected: List of pre-selected channel names

        Returns:
            List of selected channels
        """
        self.console.print("\n[bold cyan]Channel Selection[/bold cyan]")
        self.console.print(f"Found {len(channels)} channels\n")

        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Channel", style="cyan")
        table.add_column("Members", justify="right")
        table.add_column("Type", style="yellow")

        preselected_set = set(preselected or [])

        for idx, channel in enumerate(channels, 1):
            status = "📢" if not channel.get('is_private') else "🔒"
            members = str(channel.get('num_members', 0))

            # Mark pre-selected
            name = channel['name']
            if name in preselected_set:
                name = f"[green]✓ {name}[/green]"

            table.add_row(
                str(idx),
                name,
                members,
                status
            )

        self.console.print(table)

        # Selection options
        self.console.print("\n[bold]Selection options:[/bold]")
        self.console.print("  • Enter channel numbers (e.g., 1,3,5-8)")
        self.console.print("  • Type 'all' to select all channels")
        self.console.print("  • Type 'public' for public channels only")
        self.console.print("  • Type 'private' for private channels only")
        self.console.print("")

        selection = Prompt.ask("Select channels", default="all")

        # Parse selection
        if selection == "all":
            return channels
        elif selection == "public":
            return [ch for ch in channels if not ch.get('is_private')]
        elif selection == "private":
            return [ch for ch in channels if ch.get('is_private')]
        else:
            # Parse numbers
            selected_indices = self._parse_selection(selection, len(channels))
            return [channels[i] for i in selected_indices]

    def _parse_selection(self, selection: str, max_index: int) -> List[int]:
        """
        Parse selection string into indices.

        Args:
            selection: Selection string (e.g., "1,3,5-8")
            max_index: Maximum valid index

        Returns:
            List of zero-based indices
        """
        indices = set()

        for part in selection.split(','):
            part = part.strip()

            if '-' in part:
                # Range
                start, end = part.split('-')
                start = int(start.strip()) - 1  # Convert to 0-based
                end = int(end.strip()) - 1

                for i in range(start, end + 1):
                    if 0 <= i < max_index:
                        indices.add(i)
            else:
                # Single number
                idx = int(part) - 1
                if 0 <= idx < max_index:
                    indices.add(idx)

        return sorted(list(indices))

    def confirm_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Confirm export settings.

        Args:
            settings: Settings dictionary

        Returns:
            True if confirmed
        """
        panel = Panel.fit(
            self._format_settings(settings),
            title="Export Settings",
            border_style="green"
        )

        self.console.print("\n", panel)

        return Confirm.ask("Proceed with these settings?", default=True)

    def _format_settings(self, settings: Dict[str, Any]) -> str:
        """Format settings for display."""
        lines = []

        for key, value in settings.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            lines.append(f"[cyan]{key}:[/cyan] {value}")

        return "\n".join(lines)

    def select_format(self) -> str:
        """
        Select output format.

        Returns:
            Selected format
        """
        formats = {
            "1": ("markdown", "📝 Markdown - Hierarchical wiki with .md files"),
            "2": ("html", "🌐 HTML - Static website with search"),
            "3": ("json", "📊 JSON - Structured data export"),
            "4": ("xml", "📄 XML - Structured XML export"),
            "5": ("confluence", "🏢 Confluence - Direct API export")
        }

        self.console.print("\n[bold cyan]Output Format Selection[/bold cyan]\n")

        for key, (name, desc) in formats.items():
            self.console.print(f"  {key}. {desc}")

        choice = Prompt.ask(
            "\nSelect format",
            choices=list(formats.keys()),
            default="1"
        )

        return formats[choice][0]

    def show_progress(self, total: int, description: str = "Processing"):
        """
        Create progress bar context.

        Args:
            total: Total items
            description: Progress description

        Returns:
            Progress context
        """
        return Progress()


def run_interactive_mode(slack_client: Any, config: Any):
    """
    Run full interactive mode.

    Args:
        slack_client: Initialized Slack client
        config: Configuration object
    """
    if not RICH_AVAILABLE:
        print("Interactive mode requires 'rich' library")
        print("Install with: pip install rich")
        return

    interactive = InteractiveMode()
    console = interactive.console

    # Welcome
    console.print(Panel.fit(
        "[bold cyan]ThreadCrumb Interactive Mode[/bold cyan]\n"
        "AI-powered Slack Wiki Generator",
        border_style="cyan"
    ))

    # Get channels
    console.print("\n[yellow]Fetching channels...[/yellow]")
    channels = slack_client.list_channels()

    # Select channels
    selected_channels = interactive.select_channels(channels)

    if not selected_channels:
        console.print("[red]No channels selected. Exiting.[/red]")
        return

    # Select format
    output_format = interactive.select_format()

    # Confirm settings
    settings = {
        "Channels": [ch['name'] for ch in selected_channels],
        "Format": output_format,
        "AI Processing": "Enabled" if not config.ai else "Disabled",
        "Output Directory": config.output.output_dir
    }

    if not interactive.confirm_settings(settings):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    console.print("\n[green]Starting export...[/green]")

    return {
        'channels': selected_channels,
        'format': output_format
    }
