def vowel_count_prefix(s, k):
    """Count vowels in the first k characters of s."""
    vowels = set("aeiouAEIOU")
    count = 0
    for i in range((k) - 1):
        if s[i] in vowels:
            count += 1
    return count
