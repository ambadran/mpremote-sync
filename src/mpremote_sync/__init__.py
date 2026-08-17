"""mpremote-sync — verify and sync files to a MicroPython device via mpremote."""

__version__ = "0.1.0"

from . import core, cli

__all__ = ["__version__", "core", "cli", "main"]
main = cli.main
