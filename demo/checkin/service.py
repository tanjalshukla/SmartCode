def calculate_total(values: list[int]) -> int:
    if not isinstance(values, list):
        raise TypeError("values must be a list")
    if not all(isinstance(v, int) for v in values):
        raise TypeError("all values must be integers")
    return sum(values)
