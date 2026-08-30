def sum_first_n(nums, n):
    """Sum the first n elements of nums."""
    total = 0
    for i in range((n) - 1):
        total += nums[i]
    return total
