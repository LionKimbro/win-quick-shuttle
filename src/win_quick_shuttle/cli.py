"""CLI entry point for win-quick-shuttle using lionscliapp framework."""

import lionscliapp as app
from win_quick_shuttle.main import WinQuickShuttle


def cmd_run():
    """Launch the win-quick-shuttle GUI."""
    junction_path = app.ctx.get("junction", "") or None
    target_path = app.ctx.get("target", "") or None

    gui = WinQuickShuttle(junction_path, target_path)
    gui.run()


def main():
    """Entry point for win-quick-shuttle CLI."""
    # Declare the application
    app.declare_app("win-quick-shuttle", "0.2.0")
    app.declare_projectdir(".win-quick-shuttle")

    # Declare configuration keys
    app.declare_key("junction", "")
    app.describe_key("junction", "Default junction path to manage", "l")

    app.declare_key("target", "")
    app.describe_key("target", "Default target path for the junction", "l")

    # Declare commands
    app.declare_cmd("run", cmd_run)
    app.describe_cmd("run", "Launch the GUI", "s")
    app.describe_cmd("run", "Launch the win-quick-shuttle GUI to manage directory junctions.", "l")

    # Run the application
    app.main()


if __name__ == "__main__":
    main()
