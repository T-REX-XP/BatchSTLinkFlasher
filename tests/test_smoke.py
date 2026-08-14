"""Package smoke tests."""

from batch_stlink_flasher import __version__


def test_package_version_is_set() -> None:
    assert __version__
    parts = __version__.split(".")
    assert len(parts) == 4
    assert all(p.isdigit() for p in parts)
