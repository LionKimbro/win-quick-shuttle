"""Main application module for win-quick-shuttle."""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog
import ctypes


# Glanceable state
g = {
    "last_junction_path": None,
}

# Application state
app = {
    "root": None,                  # Tk root (set before calling entry)
    "toplevel": None,              # Main window
    "initial_junction_path": None, # Set before entry() if desired
    "initial_target_path": None,   # Set before entry() if desired
}

# Widget references
widgets = {}


# --- Junction helpers (pure functions) ---

def is_junction(path):
    """Check if a path is a directory junction."""
    if not os.path.exists(path):
        return False
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
        return attrs != -1 and (attrs & 0x400) != 0
    except Exception:
        return False


def get_junction_target(path):
    """Get the target of a directory junction."""
    try:
        return os.readlink(path)
    except OSError:
        return None


def remove_junction(junction_path):
    """Remove a directory junction using rmdir."""
    cmd = f'rmdir "{junction_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stderr.strip()


def create_junction(junction_path, target_path):
    """Create a directory junction using mklink /J."""
    cmd = f'mklink /J "{junction_path}" "{target_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout.strip() or result.stderr.strip()


# --- Internal helpers ---

def _get_junction_path():
    """Get the current junction path from the entry field."""
    return widgets["junction_entry"].get().strip()


def _open_in_explorer(path):
    """Open a path in Windows Explorer."""
    if not path:
        return False
    path = os.path.normpath(path)
    if os.path.exists(path):
        os.startfile(path)
        return True
    parent = os.path.dirname(path)
    if parent and os.path.exists(parent):
        os.startfile(parent)
        return True
    return False


def _set_status(message, is_error=False):
    """Update the status label."""
    color = "red" if is_error else "green"
    widgets["status_label"].config(text=message, fg=color)


def _refresh_state():
    """Update the current state display and sync target entry if junction changed."""
    junction_path = _get_junction_path()
    new_target = None

    if not junction_path:
        widgets["current_target_label"].config(text="Enter a junction path above")
    elif not os.path.exists(junction_path):
        widgets["current_target_label"].config(text="No junction present")
    elif is_junction(junction_path):
        target = get_junction_target(junction_path)
        if target:
            widgets["current_target_label"].config(text=target)
            new_target = target
        else:
            widgets["current_target_label"].config(text="Junction exists but target unreadable")
    else:
        widgets["current_target_label"].config(text="Path exists but is not a junction")

    if new_target and junction_path != g["last_junction_path"]:
        widgets["target_entry"].delete(0, tk.END)
        widgets["target_entry"].insert(0, new_target)

    g["last_junction_path"] = junction_path


# --- Event handlers ---

def handle_when_user_clicks_select_junction():
    """Open folder dialog to select junction path."""
    current = _get_junction_path()
    initial_dir = os.path.dirname(current) if current else None

    path = filedialog.askdirectory(
        title="Select Junction Location",
        initialdir=initial_dir
    )
    if path:
        widgets["junction_entry"].delete(0, tk.END)
        widgets["junction_entry"].insert(0, path)
        _refresh_state()


def handle_when_user_clicks_explore_junction():
    """Open Windows Explorer at the junction path."""
    path = _get_junction_path()
    if not path:
        _set_status("No junction path specified", is_error=True)
        return
    if not _open_in_explorer(path):
        _set_status("Path does not exist", is_error=True)


def handle_when_user_clicks_select_target():
    """Open folder dialog to select target path."""
    current = widgets["target_entry"].get().strip()
    initial_dir = current if current and os.path.isdir(current) else None

    path = filedialog.askdirectory(
        title="Select Target Folder",
        initialdir=initial_dir
    )
    if path:
        widgets["target_entry"].delete(0, tk.END)
        widgets["target_entry"].insert(0, path)


def handle_when_user_clicks_explore_target():
    """Open Windows Explorer at the target path."""
    path = widgets["target_entry"].get().strip()
    if not path:
        _set_status("No target path specified", is_error=True)
        return
    if not _open_in_explorer(path):
        _set_status("Path does not exist", is_error=True)


def handle_when_user_clicks_create_folder():
    """Create the target folder if it doesn't exist."""
    target_path = widgets["target_entry"].get().strip()

    if not target_path:
        _set_status("Please enter a target path", is_error=True)
        return

    if os.path.exists(target_path):
        _set_status("Folder already exists", is_error=False)
        return

    try:
        os.makedirs(target_path)
        _set_status(f"Created: {target_path}", is_error=False)
    except OSError as e:
        _set_status(f"Failed to create folder: {e}", is_error=True)


def handle_when_user_clicks_point_to():
    """Point the junction to the target path."""
    junction_path = _get_junction_path()
    target_path = widgets["target_entry"].get().strip()

    if not junction_path:
        _set_status("Please enter a junction path", is_error=True)
        return

    if not target_path:
        _set_status("Please enter a target path", is_error=True)
        return

    if not os.path.exists(target_path):
        _set_status("Target path does not exist", is_error=True)
        return

    if not os.path.isdir(target_path):
        _set_status("Target path is not a directory", is_error=True)
        return

    if os.path.exists(junction_path):
        if is_junction(junction_path):
            success, error = remove_junction(junction_path)
            if not success:
                _set_status(f"Failed to remove junction: {error}", is_error=True)
                return
        else:
            _set_status("Junction path exists but is not a junction", is_error=True)
            return

    success, output = create_junction(junction_path, target_path)
    if success:
        _set_status("Junction created successfully", is_error=False)
    else:
        _set_status(f"Failed to create junction: {output}", is_error=True)

    _refresh_state()


def handle_when_user_clicks_unlink():
    """Remove the junction without creating a new one."""
    junction_path = _get_junction_path()

    if not junction_path:
        _set_status("Please enter a junction path", is_error=True)
        return

    if not os.path.exists(junction_path):
        _set_status("No junction exists at that path", is_error=True)
        return

    if not is_junction(junction_path):
        _set_status("Path exists but is not a junction", is_error=True)
        return

    success, error = remove_junction(junction_path)
    if success:
        _set_status("Junction removed", is_error=False)
    else:
        _set_status(f"Failed to remove junction: {error}", is_error=True)

    _refresh_state()


def handle_when_junction_entry_loses_focus(event):
    """Refresh state when junction entry loses focus."""
    _refresh_state()


def handle_when_junction_entry_return_pressed(event):
    """Refresh state when Return pressed in junction entry."""
    _refresh_state()


# --- UI construction ---

def _build_ui():
    """Construct all widgets in the toplevel window."""
    toplevel = app["toplevel"]
    toplevel.title("win-quick-shuttle")
    toplevel.resizable(False, False)

    # Section 0: Junction Path
    frame_junction = tk.LabelFrame(toplevel, text="Junction Path", padx=10, pady=5)
    frame_junction.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

    widgets["junction_entry"] = tk.Entry(frame_junction, width=55)
    widgets["junction_entry"].grid(row=0, column=0, sticky="ew")
    if app["initial_junction_path"]:
        widgets["junction_entry"].insert(0, app["initial_junction_path"])
    widgets["junction_entry"].bind("<FocusOut>", handle_when_junction_entry_loses_focus)
    widgets["junction_entry"].bind("<Return>", handle_when_junction_entry_return_pressed)

    widgets["junction_select_btn"] = tk.Button(
        frame_junction, text="Select",
        command=handle_when_user_clicks_select_junction
    )
    widgets["junction_select_btn"].grid(row=0, column=1, padx=(5, 0))

    widgets["junction_explore_btn"] = tk.Button(
        frame_junction, text="Explore",
        command=handle_when_user_clicks_explore_junction
    )
    widgets["junction_explore_btn"].grid(row=0, column=2, padx=(2, 0))

    # Section 1: Currently Points To
    frame_current = tk.LabelFrame(toplevel, text="Currently Points To", padx=10, pady=5)
    frame_current.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

    widgets["current_target_label"] = tk.Label(frame_current, text="", anchor="w")
    widgets["current_target_label"].grid(row=0, column=0, sticky="ew")
    frame_current.columnconfigure(0, weight=1)

    # Section 2: Target Path
    frame_target = tk.LabelFrame(toplevel, text="Target Path", padx=10, pady=5)
    frame_target.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

    widgets["target_entry"] = tk.Entry(frame_target, width=55)
    widgets["target_entry"].grid(row=0, column=0, sticky="ew")
    if app["initial_target_path"]:
        widgets["target_entry"].insert(0, app["initial_target_path"])

    widgets["target_select_btn"] = tk.Button(
        frame_target, text="Select",
        command=handle_when_user_clicks_select_target
    )
    widgets["target_select_btn"].grid(row=0, column=1, padx=(5, 0))

    widgets["target_explore_btn"] = tk.Button(
        frame_target, text="Explore",
        command=handle_when_user_clicks_explore_target
    )
    widgets["target_explore_btn"].grid(row=0, column=2, padx=(2, 0))

    # Section 3: Actions
    frame_actions = tk.Frame(toplevel)
    frame_actions.grid(row=3, column=0, padx=10, pady=5, sticky="w")

    widgets["create_folder_btn"] = tk.Button(
        frame_actions, text="Create Folder",
        command=handle_when_user_clicks_create_folder
    )
    widgets["create_folder_btn"].grid(row=0, column=0, padx=(0, 5))

    widgets["point_to_btn"] = tk.Button(
        frame_actions, text="Point To",
        command=handle_when_user_clicks_point_to
    )
    widgets["point_to_btn"].grid(row=0, column=1, padx=(0, 5))

    widgets["unlink_btn"] = tk.Button(
        frame_actions, text="Unlink",
        command=handle_when_user_clicks_unlink
    )
    widgets["unlink_btn"].grid(row=0, column=2)

    # Section 4: Status
    frame_status = tk.LabelFrame(toplevel, text="Status", padx=10, pady=5)
    frame_status.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

    widgets["status_label"] = tk.Label(frame_status, text="", anchor="w", fg="gray")
    widgets["status_label"].grid(row=0, column=0, sticky="ew")
    frame_status.columnconfigure(0, weight=1)


# --- Entry / Exit for tkintertester compatibility ---

def entry():
    """Create the UI. Set app['root'] before calling."""
    g["last_junction_path"] = None
    app["toplevel"] = tk.Toplevel(app["root"])
    _build_ui()
    _refresh_state()


def exit():
    """Tear down the UI."""
    if app["toplevel"]:
        app["toplevel"].destroy()
        app["toplevel"] = None
    widgets.clear()
    g["last_junction_path"] = None


# --- Standalone entry point ---

if __name__ == "__main__":
    app["initial_junction_path"] = sys.argv[1] if len(sys.argv) > 1 else None
    app["initial_target_path"] = sys.argv[2] if len(sys.argv) > 2 else None

    app["root"] = tk.Tk()
    app["root"].withdraw()
    entry()
    app["root"].mainloop()
