"""Field types shared by more than one schema module."""

from typing import Annotated

from pydantic import StringConstraints

Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
]
