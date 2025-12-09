"""Helper functions for regression tests."""
import os
from pathlib import Path


def get_test_data_path(filename: str) -> Path:
    """Get path to test data file."""
    return Path(__file__).parent / "test_data" / filename


def save_baseline_output(output_path: Path, content: bytes | str, format_name: str):
    """Save baseline output for comparison.

    Args:
        output_path: Path where output was saved
        content: The output content (bytes or str)
        format_name: Format name for baseline directory
    """
    baseline_dir = Path(__file__).parent / "test_data" / "baselines" / format_name
    baseline_dir.mkdir(parents=True, exist_ok=True)

    baseline_path = baseline_dir / output_path.name

    if isinstance(content, bytes):
        baseline_path.write_bytes(content)
    else:
        baseline_path.write_text(content, encoding="utf-8")

    return baseline_path


def load_baseline_output(baseline_path: Path) -> bytes | str:
    """Load baseline output for comparison.

    Args:
        baseline_path: Path to baseline file

    Returns:
        Content as bytes or str
    """
    # Try to read as text first, fall back to bytes for binary formats
    try:
        return baseline_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return baseline_path.read_bytes()
