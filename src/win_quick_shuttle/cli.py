"""CLI entry point for win-quick-shuttle using lionscliapp framework."""

import tkinter as tk
import lionscliapp as cliapp
from win_quick_shuttle import main


def cmd_run():
    """Launch the win-quick-shuttle GUI."""
    main.app["initial_junction_path"] = cliapp.ctx.get("junction", "") or None
    main.app["initial_target_path"] = cliapp.ctx.get("target", "") or None

    main.app["root"] = tk.Tk()
    main.app["root"].withdraw()
    main.entry()
    main.app["root"].mainloop()


def main_cli():
    """Entry point for win-quick-shuttle CLI."""
    cliapp.declare_app("win-quick-shuttle", "0.2.0")
    cliapp.declare_projectdir(".win-quick-shuttle")

    cliapp.declare_key("junction", "")
    cliapp.describe_key("junction", "Default junction path to manage", "l")

    cliapp.declare_key("target", "")
    cliapp.describe_key("target", "Default target path for the junction", "l")

    cliapp.declare_cmd("run", cmd_run)
    cliapp.describe_cmd("run", "Launch the GUI", "s")
    cliapp.describe_cmd("run", "Launch the win-quick-shuttle GUI to manage directory junctions.", "l")

    cliapp.main()


if __name__ == "__main__":
    main_cli()
