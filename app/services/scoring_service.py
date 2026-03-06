"""
Scoring service for SpeechMaster.
Calculates Word Error Rate (WER) and maps to accuracy/categories.
"""
import logging
import re
import string

from app.utils.config import SCORE_EXCELLENT_MIN, SCORE_GOOD_MIN

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """
    Normalize text for fair comparison.

    Steps:
        1. Convert to lowercase
        2. Remove punctuation
        3. Replace multiple spaces with single space
        4. Strip leading/trailing whitespace
    """
    if not text:
        return ''
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = ' '.join(text.split())
    return text


def calculate_wer(reference: str, hypothesis: str) -> float:
    """
    Calculate Word Error Rate using Levenshtein distance at the word level.

    Args:
        reference: Target sentence (ground truth)
        hypothesis: User's transcription (Whisper output)

    Formula:
        WER = (Substitutions + Deletions + Insertions) / Total_Words_in_Reference

    Returns:
        Float between 0.0 (perfect) and 1.0+ (very poor)
    """
    ref_words = normalize_text(reference).split()
    hyp_words = normalize_text(hypothesis).split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    # Try python-Levenshtein first, fall back to manual DP
    try:
        import Levenshtein
        # Levenshtein.distance works on strings; for word-level we use editops
        ref_str = ' '.join(ref_words)
        hyp_str = ' '.join(hyp_words)
        # Word-level: compute via DP below for correctness
    except ImportError:
        pass

    # Dynamic programming word-level edit distance
    n = len(ref_words)
    m = len(hyp_words)

    # dp[i][j] = edit distance between ref_words[:i] and hyp_words[:j]
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],       # deletion
                    dp[i][j - 1],       # insertion
                    dp[i - 1][j - 1],   # substitution
                )

    edit_distance = dp[n][m]
    wer = edit_distance / n

    return round(wer, 4)


def calculate_score(wer: float) -> dict:
    """
    Convert WER to percentage score and category.

    Args:
        wer: Word Error Rate (0.0 - 1.0+)

    Returns:
        {
            'wer': float,
            'accuracy_percentage': int (0-100),
            'category': str ('excellent', 'good', 'needs_improvement'),
            'led_color': str ('green', 'orange', 'red')
        }
    """
    accuracy = max(0, min(100, int((1 - wer) * 100)))

    if accuracy >= SCORE_EXCELLENT_MIN:
        category = 'excellent'
        led_color = 'green'
    elif accuracy >= SCORE_GOOD_MIN:
        category = 'good'
        led_color = 'orange'
    else:
        category = 'needs_improvement'
        led_color = 'red'

    return {
        'wer': wer,
        'accuracy_percentage': accuracy,
        'category': category,
        'led_color': led_color,
    }


def score_recording(transcription: str, target_sentence: str) -> dict:
    """
    Complete scoring pipeline.

    Args:
        transcription: Whisper output text
        target_sentence: Original sentence the user tried to say

    Returns:
        {
            'transcription': str,
            'target': str,
            'wer': float,
            'accuracy': int,
            'category': str,
            'led_color': str,
        }
    """
    wer = calculate_wer(target_sentence, transcription)
    score = calculate_score(wer)

    logger.info(
        "Score: %d%% (%s) | WER: %.2f | Target: '%s' | Got: '%s'",
        score['accuracy_percentage'],
        score['category'],
        wer,
        target_sentence[:40],
        transcription[:40],
    )

    return {
        'transcription': transcription,
        'target': target_sentence,
        'wer': score['wer'],
        'accuracy': score['accuracy_percentage'],
        'category': score['category'],
        'led_color': score['led_color'],
    }
