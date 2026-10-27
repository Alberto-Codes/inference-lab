"""Measure diagnostic overlap against partial CORD annotations.

These metrics are not official CORD scores. They do not assess layout or
associate extracted amounts with financial fields.

Attributes:
    TOKEN: Pattern preserving numeric punctuation while extracting word tokens.
    CONTROL: Pattern matching known Nemotron control tokens.

Examples:
    ```python
    from inference_lab.receipt_metrics import score

    recall = score("Total 12.00", "total 12.00")["numeric_recall"]  # 1.0
    ```

See Also:
    [`inference_lab.client`][]: HTTP extraction and request status accounting.
"""

import html
import re
from collections import Counter

# Preserve punctuation within numeric strings. Do not match 12 inside 312.
TOKEN = re.compile(r"[+-]?\d+(?:[.,:/-]\d+)*(?:%)?|[^\W\d_]+", re.UNICODE)
CONTROL = re.compile(r"<(?:[xy]_[0-9.]+|class_[^>]+|/?s)>")


def plain_text(raw: str) -> str:
    """Strip model markup and collapse whitespace for diagnostic scoring.

    Args:
        raw: Model output containing control tokens, markup or LaTeX commands.

    Returns:
        Unescaped text with markup removed and whitespace collapsed.
    """
    text = CONTROL.sub(" ", raw)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\\(?:begin|end)\{[^}]+\}(?:\{[^}]+\})?", " ", text)
    text = re.sub(r"\\multicolumn\{[^}]*\}\{[^}]*\}", " ", text)
    text = re.sub(r"\\[A-Za-z]+\*?", " ", text)
    return " ".join(html.unescape(text).split())


def tokens(text: str) -> list[str]:
    """Extract casefolded word and numeric tokens.

    Args:
        text: Reference or predicted text.

    Returns:
        Tokens in source order, with numeric punctuation preserved.
    """
    return TOKEN.findall(text.casefold())


def numbers(text: str) -> Counter:
    """Count exact numeric strings, including repeated occurrences.

    Args:
        text: Reference or predicted text.

    Returns:
        Counts keyed by numeric token; punctuation and signs remain significant.
    """
    return Counter(t for t in tokens(text) if re.fullmatch(r"[+-]?\d[\d.,:/%-]*", t))


def score(reference: str, prediction: str) -> dict:
    """Calculate token ROUGE-L and exact numeric-string recall.

    Args:
        reference: Partial annotated text used as the comparison target.
        prediction: Extracted plain text to compare with the reference.

    Returns:
        Token precision, recall and F1; numeric match counts and recall; and
        unmatched reference numeric strings. Recall and F1 are None for an
        empty reference. Numeric recall is None when it contains no numbers.
    """
    ref, pred = tokens(reference), tokens(prediction)
    previous = [0] * (len(pred) + 1)
    for token in ref:
        row = [0]
        for j, other in enumerate(pred, 1):
            row.append(
                previous[j - 1] + 1 if token == other else max(previous[j], row[-1])
            )
        previous = row
    overlap = previous[-1]
    precision = overlap / len(pred) if pred else 0.0
    recall = overlap / len(ref) if ref else None
    f1 = 2 * overlap / (len(ref) + len(pred)) if ref else None
    rn, pn = numbers(reference), numbers(prediction)
    matched = sum((rn & pn).values())
    count = sum(rn.values())
    return {
        "rouge_l_precision": precision,
        "rouge_l_recall": recall,
        "rouge_l_f1": f1,
        "reference_tokens": len(ref),
        "prediction_tokens": len(pred),
        "numeric_reference_count": count,
        "numeric_matched_count": matched,
        "numeric_recall": matched / count if count else None,
        "missing_numbers": list((rn - pn).elements()),
    }
