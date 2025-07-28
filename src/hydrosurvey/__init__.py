"""Hydrosurvey package."""

from importlib import metadata

try:
    __version__ = metadata.version("hydrosurvey")
except metadata.PackageNotFoundError:
    # The package is not installed, so we don't know the version
    __version__ = "0.0.0"
