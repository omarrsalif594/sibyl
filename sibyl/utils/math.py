"""Mathematical utility functions shared between production and tests."""


def percentile(values: list[int | float], p: float) -> float:
    """Calculate percentile of a list of values.

    Uses linear interpolation between closest ranks (numpy method).

    Args:
        values: List of numeric values (will be sorted)
        p: Percentile to calculate (0-100)

    Returns:
        Percentile value

    Raises:
        ValueError: If values is empty or p is out of range

    Examples:
        >>> percentile([1, 2, 3, 4, 5], 50)  # Median
        3.0
        >>> percentile([1, 2, 3, 4, 5], 95)  # 95th percentile
        4.8
        >>> percentile([10, 20, 30], 0)  # Min
        10.0
        >>> percentile([10, 20, 30], 100)  # Max
        30.0
    """
    if not values:
        msg = "Cannot calculate percentile of empty list"
        raise ValueError(msg)

    if not 0 <= p <= 100:
        msg = f"Percentile must be between 0 and 100, got {p}"
        raise ValueError(msg)

    # Sort values
    sorted_values = sorted(values)
    n = len(sorted_values)

    # Edge cases
    if n == 1:
        return float(sorted_values[0])

    if p == 0:
        return float(sorted_values[0])

    if p == 100:
        return float(sorted_values[-1])

    # Calculate index using linear interpolation (numpy method)
    # index = (n - 1) * (p / 100)
    index = (n - 1) * (p / 100.0)
    lower_index = int(index)
    upper_index = lower_index + 1

    # Handle edge case where index is exactly at upper bound
    if upper_index >= n:
        return float(sorted_values[-1])

    # Linear interpolation between two closest values
    fraction = index - lower_index
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]

    result = lower_value + fraction * (upper_value - lower_value)
    return float(result)
