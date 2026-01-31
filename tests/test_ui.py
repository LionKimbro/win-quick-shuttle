"""UI tests for win-quick-shuttle.

These tests require a display and working Tcl/Tk installation.
Run with: pytest tests/test_ui.py -v

Note: On some Windows systems, Tcl/Tk can have intermittent initialization
issues when running under pytest. If these tests fail with TclError,
the core logic tests in test_main.py still provide coverage.
"""

import os
import pytest
from unittest.mock import patch

# Mark all tests in this module to skip if Tk initialization fails
pytest.importorskip("tkinter")


@pytest.fixture(scope="module")
def tk_available():
    """Check if Tk can be initialized."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.destroy()
        return True
    except Exception:
        pytest.skip("Tkinter not available or Tcl initialization failed")


@pytest.fixture
def app(tk_available):
    """Create app instance for testing."""
    import tkinter as tk
    from win_quick_shuttle.main import WinQuickShuttle

    with patch("win_quick_shuttle.main.is_junction", return_value=False):
        with patch("os.path.exists", return_value=False):
            app = WinQuickShuttle(r"C:\test\junction")
            yield app
            app.root.destroy()


class TestWinQuickShuttleUI:
    """Tests for the WinQuickShuttle UI class."""

    def test_initial_state_no_junction(self, app):
        """App shows 'No junction present' when junction doesn't exist."""
        assert "No junction present" in app.current_target_label.cget("text")

    def test_create_folder_empty_path(self, app):
        """Create folder with empty path shows error."""
        app.target_entry.delete(0, "end")
        app._create_target_folder()
        assert "Please enter" in app.status_label.cget("text")
        assert app.status_label.cget("fg") == "red"

    @patch("os.path.exists")
    def test_create_folder_already_exists(self, mock_exists, app):
        """Create folder shows message when folder exists."""
        mock_exists.return_value = True
        app.target_entry.delete(0, "end")
        app.target_entry.insert(0, r"C:\existing\folder")
        app._create_target_folder()
        assert "already exists" in app.status_label.cget("text")

    @patch("os.makedirs")
    @patch("os.path.exists")
    def test_create_folder_success(self, mock_exists, mock_makedirs, app):
        """Create folder creates directory successfully."""
        mock_exists.return_value = False
        app.target_entry.delete(0, "end")
        app.target_entry.insert(0, r"C:\new\folder")
        app._create_target_folder()
        mock_makedirs.assert_called_once_with(r"C:\new\folder")
        assert "Created" in app.status_label.cget("text")
        assert app.status_label.cget("fg") == "green"

    @patch("os.makedirs")
    @patch("os.path.exists")
    def test_create_folder_failure(self, mock_exists, mock_makedirs, app):
        """Create folder shows error on failure."""
        mock_exists.return_value = False
        mock_makedirs.side_effect = OSError("Permission denied")
        app.target_entry.delete(0, "end")
        app.target_entry.insert(0, r"C:\forbidden\folder")
        app._create_target_folder()
        assert "Failed" in app.status_label.cget("text")
        assert app.status_label.cget("fg") == "red"

    def test_point_to_empty_path(self, app):
        """Point to with empty path shows error."""
        app.target_entry.delete(0, "end")
        app._point_junction_to_target()
        assert "Please enter" in app.status_label.cget("text")

    @patch("os.path.exists")
    def test_point_to_nonexistent_target(self, mock_exists, app):
        """Point to nonexistent target shows error."""
        mock_exists.return_value = False
        app.target_entry.delete(0, "end")
        app.target_entry.insert(0, r"C:\nonexistent")
        app._point_junction_to_target()
        assert "does not exist" in app.status_label.cget("text")

    @patch("os.path.isdir")
    @patch("os.path.exists")
    def test_point_to_file_not_directory(self, mock_exists, mock_isdir, app):
        """Point to a file (not directory) shows error."""
        mock_exists.return_value = True
        mock_isdir.return_value = False
        app.target_entry.delete(0, "end")
        app.target_entry.insert(0, r"C:\some\file.txt")
        app._point_junction_to_target()
        assert "not a directory" in app.status_label.cget("text")


class TestRefreshCurrentState:
    """Tests for the _refresh_current_state method."""

    def test_no_junction_present(self, app):
        """Shows 'No junction present' when path doesn't exist."""
        with patch("os.path.exists", return_value=False):
            app._refresh_current_state()
            assert "No junction present" in app.current_target_label.cget("text")

    def test_shows_junction_target(self, app):
        """Shows target path when junction exists."""
        with patch("os.path.exists", return_value=True):
            with patch("win_quick_shuttle.main.is_junction", return_value=True):
                with patch("win_quick_shuttle.main.get_junction_target", return_value=r"C:\my\target"):
                    app._refresh_current_state()
                    assert r"C:\my\target" in app.current_target_label.cget("text")

    def test_path_exists_but_not_junction(self, app):
        """Shows warning when path exists but isn't a junction."""
        with patch("os.path.exists", return_value=True):
            with patch("win_quick_shuttle.main.is_junction", return_value=False):
                app._refresh_current_state()
                assert "not a junction" in app.current_target_label.cget("text")
