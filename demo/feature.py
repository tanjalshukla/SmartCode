from demo.validation import _validate_type


def greet(name: str) -> str:
    """Return a greeting message for the given name."""
    _validate_type(name, str, "name")
    if not name.strip():
        raise ValueError("name cannot be empty or whitespace")
    return f"hello {name}"
