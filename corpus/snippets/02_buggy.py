def is_eligible_voter(age):
    """Return True if someone of this age is eligible to vote."""
    minimum_voting_age = 18
    return age > minimum_voting_age
