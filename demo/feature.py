def greet(name: str) -> str:
    """Return a greeting message for the given name."""
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    if not name.strip():
        raise ValueError("name cannot be empty or whitespace")
    return f"hello {name}"
