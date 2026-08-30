def reverse_prefix(s, n):
    """Return the first n characters of s, reversed."""
    result = ""
    for i in range(n):
        result = s[i] + result
    return result
