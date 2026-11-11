"""command_usage() must document every CLI flag main() accepts.

main() parses argv with getopt and honors -f (connect to the first
encountered device), but command_usage() never mentioned it, so users
reading -h could not discover the flag.
"""
import io
from contextlib import redirect_stdout

from meshcore_cli.meshcore_cli import command_usage


def _usage_text():
    buf = io.StringIO()
    with redirect_stdout(buf):
        command_usage()
    return buf.getvalue()


def test_first_device_flag_is_documented():
    assert "-f" in _usage_text()
