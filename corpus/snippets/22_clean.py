def count_positive_in_first_n(nums, n):
    """Count how many of the first n numbers are positive."""
    count = 0
    for i in range(n):
        if nums[i] > 0:
            count += 1
    return count
