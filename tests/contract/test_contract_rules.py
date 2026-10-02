"""Rules about the contract document itself."""

import re
from typing import Any


def test_non_blank_pattern_matches_python_whitespace_exactly(contract: dict[str, Any]) -> None:
    """Both backends trim with `str.strip()`. The contract's `non_blank`
    pattern must call a string blank exactly when Python would strip it to "",
    or property-based tests generate "valid" input the servers reject.
    (Found by Schemathesis: "\\x1f" is not `\\s` in JSON Schema but is stripped.)
    """
    pattern = re.compile(contract["components"]["schemas"]["PostCreate"]["properties"]["title"]["pattern"])
    mismatches = [
        hex(code)
        for code in range(0x110000)
        if not 0xD800 <= code <= 0xDFFF  # surrogates are rejected separately
        and bool(pattern.search(chr(code))) != bool(chr(code).strip())
    ]
    assert mismatches == []
