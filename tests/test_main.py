"""Tests for win-quick-shuttle."""

import os
import pytest
from unittest.mock import patch, MagicMock

from win_quick_shuttle.main import (
    is_junction,
    get_junction_target,
    remove_junction,
    create_junction,
)


class TestJunctionHelpers:
    """Tests for junction helper functions."""

    def test_is_junction_nonexistent_path(self):
        """is_junction returns False for nonexistent paths."""
        assert is_junction(r"C:\nonexistent\path\that\does\not\exist") is False

    @patch("win_quick_shuttle.main.ctypes")
    def test_is_junction_with_reparse_point(self, mock_ctypes):
        """is_junction returns True when path has reparse point attribute."""
        mock_ctypes.windll.kernel32.GetFileAttributesW.return_value = 0x410  # DIR + REPARSE
        with patch("os.path.exists", return_value=True):
            assert is_junction(r"C:\some\junction") is True

    @patch("win_quick_shuttle.main.ctypes")
    def test_is_junction_without_reparse_point(self, mock_ctypes):
        """is_junction returns False for regular directories."""
        mock_ctypes.windll.kernel32.GetFileAttributesW.return_value = 0x10  # DIR only
        with patch("os.path.exists", return_value=True):
            assert is_junction(r"C:\some\directory") is False

    @patch("os.readlink")
    def test_get_junction_target_success(self, mock_readlink):
        """get_junction_target returns the target path."""
        mock_readlink.return_value = r"C:\target\path"
        assert get_junction_target(r"C:\junction") == r"C:\target\path"

    @patch("os.readlink")
    def test_get_junction_target_failure(self, mock_readlink):
        """get_junction_target returns None on OSError."""
        mock_readlink.side_effect = OSError("Not a junction")
        assert get_junction_target(r"C:\not\a\junction") is None


class TestShellCommands:
    """Tests for shell command functions."""

    @patch("subprocess.run")
    def test_remove_junction_success(self, mock_run):
        """remove_junction returns True on success."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        success, error = remove_junction(r"C:\junction")
        assert success is True
        assert error == ""
        mock_run.assert_called_once()
        assert "rmdir" in mock_run.call_args[0][0]

    @patch("subprocess.run")
    def test_remove_junction_failure(self, mock_run):
        """remove_junction returns False with error message on failure."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Access denied")
        success, error = remove_junction(r"C:\junction")
        assert success is False
        assert "Access denied" in error

    @patch("subprocess.run")
    def test_create_junction_success(self, mock_run):
        """create_junction returns True on success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Junction created", stderr="")
        success, output = create_junction(r"C:\junction", r"C:\target")
        assert success is True
        assert "Junction created" in output
        mock_run.assert_called_once()
        assert "mklink /J" in mock_run.call_args[0][0]

    @patch("subprocess.run")
    def test_create_junction_failure(self, mock_run):
        """create_junction returns False with error on failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Cannot create")
        success, output = create_junction(r"C:\junction", r"C:\target")
        assert success is False
        assert "Cannot create" in output


class TestJunctionIntegration:
    """Integration tests that create real junctions on the filesystem."""

    def test_full_junction_lifecycle(self, tmp_path):
        """Create a junction, verify it, then remove it."""
        target = tmp_path / "target"
        junction = tmp_path / "junction"
        target.mkdir()

        # Create a file in target to verify junction works
        (target / "test.txt").write_text("hello")

        # Create junction
        success, output = create_junction(str(junction), str(target))
        assert success, f"Failed to create junction: {output}"

        # Verify junction exists and points to target
        assert junction.exists()
        assert is_junction(str(junction))
        # Junction target may have \\?\ prefix, so check it ends with the target path
        junction_target = get_junction_target(str(junction))
        assert junction_target.endswith(str(target)) or str(target) in junction_target

        # Verify we can access files through the junction
        assert (junction / "test.txt").read_text() == "hello"

        # Remove junction
        success, error = remove_junction(str(junction))
        assert success, f"Failed to remove junction: {error}"

        # Verify junction is gone but target remains
        assert not junction.exists()
        assert target.exists()
        assert (target / "test.txt").read_text() == "hello"

    def test_redirect_junction_to_new_target(self, tmp_path):
        """Redirect an existing junction to a different target."""
        target_a = tmp_path / "target_a"
        target_b = tmp_path / "target_b"
        junction = tmp_path / "junction"
        target_a.mkdir()
        target_b.mkdir()

        (target_a / "a.txt").write_text("from A")
        (target_b / "b.txt").write_text("from B")

        # Create junction pointing to A
        success, _ = create_junction(str(junction), str(target_a))
        assert success
        assert (junction / "a.txt").read_text() == "from A"

        # Remove and recreate pointing to B
        remove_junction(str(junction))
        success, _ = create_junction(str(junction), str(target_b))
        assert success
        assert (junction / "b.txt").read_text() == "from B"

        # Cleanup
        remove_junction(str(junction))


# UI tests are in guitests/ and use tkintertester
