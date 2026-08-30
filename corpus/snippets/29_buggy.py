def multiples_of_k_up_to(n, k):
    """Count multiples of k in the inclusive range 1..n."""
    count = 0
    for i in range(1, (n + 1) - 1):
        if i % k == 0:
            count += 1
    return count
