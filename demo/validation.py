def _validate_type(value, expected_type, param_name):
    """Helper to validate parameter types."""
    if not isinstance(value, expected_type):
        raise TypeError(f"{param_name} must be a {expected_type.__name__}")
