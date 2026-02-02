"""GUI tests for win-quick-shuttle using tkintertester.

Run with: python guitests/test_ui.py
"""

from unittest.mock import patch
from tkintertester import harness
from win_quick_shuttle import main


def app_entry():
    """Wire up the app for testing."""
    main.app["root"] = harness.g["root"]
    main.app["initial_junction_path"] = r"C:\test\junction"
    main.app["initial_target_path"] = None
    main.entry()


def app_exit():
    """Tear down the app after testing."""
    main.exit()


# --- Tests ---

def test_initial_state_shows_no_junction():
    """When junction path doesn't exist, show 'No junction present'."""
    def step_verify():
        text = main.widgets["current_target_label"].cget("text")
        if "No junction present" in text:
            return ("success", None)
        return ("fail", f"Expected 'No junction present', got '{text}'")

    return [step_verify]


def test_create_folder_with_empty_path_shows_error():
    """Create folder with empty target path shows error."""
    def step_clear_and_click():
        main.widgets["target_entry"].delete(0, "end")
        main.widgets["create_folder_btn"].invoke()
        return ("next", None)

    def step_verify_error():
        text = main.widgets["status_label"].cget("text")
        color = main.widgets["status_label"].cget("fg")
        if "Please enter" in text and color == "red":
            return ("success", None)
        return ("fail", f"Expected error message, got '{text}' with color '{color}'")

    return [step_clear_and_click, step_verify_error]


def test_create_folder_already_exists():
    """Create folder shows message when folder already exists."""
    def step_set_path_and_click():
        main.widgets["target_entry"].delete(0, "end")
        main.widgets["target_entry"].insert(0, r"C:\existing\folder")
        with patch("os.path.exists", return_value=True):
            main.widgets["create_folder_btn"].invoke()
        return ("next", None)

    def step_verify():
        text = main.widgets["status_label"].cget("text")
        if "already exists" in text:
            return ("success", None)
        return ("fail", f"Expected 'already exists', got '{text}'")

    return [step_set_path_and_click, step_verify]


def test_create_folder_success():
    """Create folder creates directory successfully."""
    def step_set_path_and_click():
        main.widgets["target_entry"].delete(0, "end")
        main.widgets["target_entry"].insert(0, r"C:\new\folder")
        with patch("os.path.exists", return_value=False):
            with patch("os.makedirs") as mock_makedirs:
                main.widgets["create_folder_btn"].invoke()
                if not mock_makedirs.called:
                    return ("fail", "makedirs was not called")
        return ("next", None)

    def step_verify():
        text = main.widgets["status_label"].cget("text")
        color = main.widgets["status_label"].cget("fg")
        if "Created" in text and color == "green":
            return ("success", None)
        return ("fail", f"Expected success message, got '{text}'")

    return [step_set_path_and_click, step_verify]


def test_point_to_empty_target_shows_error():
    """Point to with empty target path shows error."""
    def step_clear_and_click():
        main.widgets["target_entry"].delete(0, "end")
        main.widgets["point_to_btn"].invoke()
        return ("next", None)

    def step_verify():
        text = main.widgets["status_label"].cget("text")
        if "Please enter" in text:
            return ("success", None)
        return ("fail", f"Expected error, got '{text}'")

    return [step_clear_and_click, step_verify]


def test_point_to_nonexistent_target_shows_error():
    """Point to nonexistent target shows error."""
    def step_set_and_click():
        main.widgets["target_entry"].delete(0, "end")
        main.widgets["target_entry"].insert(0, r"C:\nonexistent")
        with patch("os.path.exists", return_value=False):
            main.widgets["point_to_btn"].invoke()
        return ("next", None)

    def step_verify():
        text = main.widgets["status_label"].cget("text")
        if "does not exist" in text:
            return ("success", None)
        return ("fail", f"Expected 'does not exist', got '{text}'")

    return [step_set_and_click, step_verify]


def test_unlink_nonexistent_junction_shows_error():
    """Unlink when no junction exists shows error."""
    def step_click():
        with patch("os.path.exists", return_value=False):
            main.widgets["unlink_btn"].invoke()
        return ("next", None)

    def step_verify():
        text = main.widgets["status_label"].cget("text")
        if "No junction exists" in text:
            return ("success", None)
        return ("fail", f"Expected error, got '{text}'")

    return [step_click, step_verify]


if __name__ == "__main__":
    # Patch filesystem checks during entry so UI initializes cleanly
    with patch("win_quick_shuttle.main.is_junction", return_value=False):
        with patch("os.path.exists", return_value=False):
            harness.add_test("Initial state shows no junction", test_initial_state_shows_no_junction())
            harness.add_test("Create folder: empty path shows error", test_create_folder_with_empty_path_shows_error())
            harness.add_test("Create folder: already exists", test_create_folder_already_exists())
            harness.add_test("Create folder: success", test_create_folder_success())
            harness.add_test("Point to: empty target shows error", test_point_to_empty_target_shows_error())
            harness.add_test("Point to: nonexistent target", test_point_to_nonexistent_target_shows_error())
            harness.add_test("Unlink: no junction exists", test_unlink_nonexistent_junction_shows_error())

            harness.run(app_entry, app_exit, timeout_ms=5000)

    # Print results
    print("\nResults:")
    passed = 0
    failed = 0
    for test in harness.tests:
        status = test["status"].upper()
        if status == "SUCCESS":
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] {test['title']}")
        if test["fail_message"]:
            print(f"           {test['fail_message']}")

    print(f"\n{passed} passed, {failed} failed")
