from demo.validation import _validate_type


def calculate_total(values: list[int]) -> int:
    _validate_type(values, list, "values")
    if not all(isinstance(v, int) for v in values):
        raise TypeError("all values must be integers")
    return sum(values)
