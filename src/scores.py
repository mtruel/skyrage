"""
Score calculation utilities for Skyjo game.

This module contains shared logic for calculating final scores,
including the doubling penalty rule.
"""


def apply_doubling_penalty(raw_scores: dict, round_ender) -> dict:
    """
    Apply the Skyjo doubling penalty rule to calculate final scores.

    If the round_ender doesn't have the lowest score and their score is positive,
    their score is doubled.

    Args:
        raw_scores: Dictionary mapping player identifier to raw score
        round_ender: Identifier of the player who ended the round (must be a key in raw_scores)

    Returns:
        Dictionary mapping player identifier to final score (after doubling if applicable)
    """
    if not raw_scores:
        return {}

    final_scores = {}
    min_score = min(raw_scores.values())

    for player, raw_score in raw_scores.items():
        # Check if this player ended the round and doesn't have lowest score
        if player == round_ender and raw_score > min_score and raw_score > 0:
            # Apply doubling penalty
            final_scores[player] = raw_score * 2
        else:
            final_scores[player] = raw_score

    return final_scores
