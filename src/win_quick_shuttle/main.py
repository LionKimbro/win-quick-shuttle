"""Main application module for win-quick-shuttle."""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog
import ctypes


def is_junction(path):
    """Check if a path is a directory junction."""
    if not os.path.exists(path):
        return False
    try:
        # FILE_ATTRIBUTE_REPARSE_POINT = 0x400
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


class WinQuickShuttle:
    def __init__(self, initial_junction_path=None, initial_target_path=None):
        self.root = tk.Tk()
        self.root.title("win-quick-shuttle")
        self.root.resizable(False, False)

        self._build_ui(initial_junction_path, initial_target_path)
        self._refresh_current_state()

    def _build_ui(self, initial_junction_path, initial_target_path):
        padding = {'padx': 10, 'pady': 5}

        # Section 0: Junction Path (what we're managing)
        frame_junction = tk.LabelFrame(self.root, text="Junction Path", padx=10, pady=5)
        frame_junction.pack(fill='x', **padding)

        junction_row = tk.Frame(frame_junction)
        junction_row.pack(fill='x')

        self.junction_entry = tk.Entry(junction_row, width=55)
        self.junction_entry.pack(side='left', fill='x', expand=True)
        if initial_junction_path:
            self.junction_entry.insert(0, initial_junction_path)
        self.junction_entry.bind('<FocusOut>', lambda e: self._refresh_current_state())
        self.junction_entry.bind('<Return>', lambda e: self._refresh_current_state())

        junction_select_btn = tk.Button(junction_row, text="Select", command=self._browse_junction_path)
        junction_select_btn.pack(side='left', padx=(5, 0))

        junction_explore_btn = tk.Button(junction_row, text="Explore", command=self._explore_junction_path)
        junction_explore_btn.pack(side='left', padx=(2, 0))

        # Section 1: Current State
        frame_current = tk.LabelFrame(self.root, text="Currently Points To", padx=10, pady=5)
        frame_current.pack(fill='x', **padding)

        self.current_target_label = tk.Label(frame_current, text="", anchor='w')
        self.current_target_label.pack(fill='x')

        # Section 2: Edit Target
        frame_edit = tk.LabelFrame(self.root, text="Target Path", padx=10, pady=5)
        frame_edit.pack(fill='x', **padding)

        target_row = tk.Frame(frame_edit)
        target_row.pack(fill='x')

        self.target_entry = tk.Entry(target_row, width=55)
        self.target_entry.pack(side='left', fill='x', expand=True)
        if initial_target_path:
            self.target_entry.insert(0, initial_target_path)

        target_select_btn = tk.Button(target_row, text="Select", command=self._browse_target_path)
        target_select_btn.pack(side='left', padx=(5, 0))

        target_explore_btn = tk.Button(target_row, text="Explore", command=self._explore_target_path)
        target_explore_btn.pack(side='left', padx=(2, 0))

        # Section 3: Actions
        frame_actions = tk.Frame(self.root)
        frame_actions.pack(fill='x', **padding)

        self.create_folder_button = tk.Button(
            frame_actions, text="Create Folder", command=self._create_target_folder
        )
        self.create_folder_button.pack(side='left', padx=(0, 5))

        self.point_to_button = tk.Button(
            frame_actions, text="Point To", command=self._point_junction_to_target
        )
        self.point_to_button.pack(side='left', padx=(0, 5))

        self.unlink_button = tk.Button(
            frame_actions, text="Unlink", command=self._unlink_junction
        )
        self.unlink_button.pack(side='left')

        # Section 4: Status
        frame_status = tk.LabelFrame(self.root, text="Status", padx=10, pady=5)
        frame_status.pack(fill='x', **padding)

        self.status_label = tk.Label(frame_status, text="", anchor='w', fg='gray')
        self.status_label.pack(fill='x')

    def _get_junction_path(self):
        """Get the current junction path from the entry field."""
        return self.junction_entry.get().strip()

    def _browse_junction_path(self):
        """Open folder dialog to select junction path."""
        # For junction, we want to select the parent folder, then append the name
        current = self._get_junction_path()
        initial_dir = os.path.dirname(current) if current else None

        path = filedialog.askdirectory(
            title="Select Junction Location (parent folder)",
            initialdir=initial_dir
        )
        if path:
            # Ask for the junction folder name or just use the selected path
            self.junction_entry.delete(0, tk.END)
            self.junction_entry.insert(0, path)
            self._refresh_current_state()

    def _browse_target_path(self):
        """Open folder dialog to select target path."""
        current = self.target_entry.get().strip()
        initial_dir = current if current and os.path.isdir(current) else None

        path = filedialog.askdirectory(
            title="Select Target Folder",
            initialdir=initial_dir
        )
        if path:
            self.target_entry.delete(0, tk.END)
            self.target_entry.insert(0, path)

    def _open_in_explorer(self, path):
        """Open a path in Windows Explorer."""
        if not path:
            return False
        # Normalize path (convert forward slashes to backslashes)
        path = os.path.normpath(path)
        if os.path.exists(path):
            os.startfile(path)
            return True
        else:
            # Try parent folder if path doesn't exist
            parent = os.path.dirname(path)
            if parent and os.path.exists(parent):
                os.startfile(parent)
                return True
        return False

    def _explore_junction_path(self):
        """Open Windows Explorer at the junction path."""
        path = self._get_junction_path()
        if not path:
            self._set_status("No junction path specified", is_error=True)
            return
        if not self._open_in_explorer(path):
            self._set_status("Path does not exist", is_error=True)

    def _explore_target_path(self):
        """Open Windows Explorer at the target path."""
        path = self.target_entry.get().strip()
        if not path:
            self._set_status("No target path specified", is_error=True)
            return
        if not self._open_in_explorer(path):
            self._set_status("Path does not exist", is_error=True)

    def _refresh_current_state(self):
        """Update the current state display."""
        junction_path = self._get_junction_path()
        if not junction_path:
            self.current_target_label.config(text="Enter a junction path above")
        elif not os.path.exists(junction_path):
            self.current_target_label.config(text="No junction present")
        elif is_junction(junction_path):
            target = get_junction_target(junction_path)
            if target:
                self.current_target_label.config(text=target)
            else:
                self.current_target_label.config(text="Junction exists but target unreadable")
        else:
            self.current_target_label.config(text="Path exists but is not a junction")

    def _set_status(self, message, is_error=False):
        """Update the status label."""
        self.status_label.config(text=message, fg='red' if is_error else 'green')

    def _create_target_folder(self):
        """Create the target folder if it doesn't exist."""
        target_path = self.target_entry.get().strip()

        if not target_path:
            self._set_status("Please enter a target path", is_error=True)
            return

        if os.path.exists(target_path):
            self._set_status("Folder already exists", is_error=False)
            return

        try:
            os.makedirs(target_path)
            self._set_status(f"Created: {target_path}", is_error=False)
        except OSError as e:
            self._set_status(f"Failed to create folder: {e}", is_error=True)

    def _point_junction_to_target(self):
        """Point the junction to the target path."""
        junction_path = self._get_junction_path()
        target_path = self.target_entry.get().strip()

        if not junction_path:
            self._set_status("Please enter a junction path", is_error=True)
            return

        if not target_path:
            self._set_status("Please enter a target path", is_error=True)
            return

        if not os.path.exists(target_path):
            self._set_status("Target path does not exist", is_error=True)
            return

        if not os.path.isdir(target_path):
            self._set_status("Target path is not a directory", is_error=True)
            return

        # Remove existing junction if present
        if os.path.exists(junction_path):
            if is_junction(junction_path):
                success, error = remove_junction(junction_path)
                if not success:
                    self._set_status(f"Failed to remove junction: {error}", is_error=True)
                    return
            else:
                self._set_status("Junction path exists but is not a junction", is_error=True)
                return

        # Create the new junction
        success, output = create_junction(junction_path, target_path)
        if success:
            self._set_status("Junction created successfully", is_error=False)
        else:
            self._set_status(f"Failed to create junction: {output}", is_error=True)

        self._refresh_current_state()

    def _unlink_junction(self):
        """Remove the junction without creating a new one."""
        junction_path = self._get_junction_path()

        if not junction_path:
            self._set_status("Please enter a junction path", is_error=True)
            return

        if not os.path.exists(junction_path):
            self._set_status("No junction exists at that path", is_error=True)
            return

        if not is_junction(junction_path):
            self._set_status("Path exists but is not a junction", is_error=True)
            return

        success, error = remove_junction(junction_path)
        if success:
            self._set_status("Junction removed", is_error=False)
        else:
            self._set_status(f"Failed to remove junction: {error}", is_error=True)

        self._refresh_current_state()

    def run(self):
        """Start the application."""
        self.root.mainloop()


def main():
    initial_junction_path = sys.argv[1] if len(sys.argv) > 1 else None
    initial_target_path = sys.argv[2] if len(sys.argv) > 2 else None

    app = WinQuickShuttle(initial_junction_path, initial_target_path)
    app.run()


if __name__ == "__main__":
    main()
