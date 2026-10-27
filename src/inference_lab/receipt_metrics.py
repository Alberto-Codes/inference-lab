"""Diagnostic overlap against partial CORD annotations, not official CORD scores."""

import html
import re
from collections import Counter

# Preserve punctuation within numeric strings. Do not match 12 inside 312.
TOKEN = re.compile(r"[+-]?\d+(?:[.,:/-]\d+)*(?:%)?|[^\W\d_]+", re.UNICODE)
CONTROL = re.compile(r"<(?:[xy]_[0-9.]+|class_[^>]+|/?s)>")


def plain_text(raw: str) -> str:
    text = CONTROL.sub(" ", raw)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\\(?:begin|end)\{[^}]+\}(?:\{[^}]+\})?", " ", text)
    text = re.sub(r"\\multicolumn\{[^}]*\}\{[^}]*\}", " ", text)
    text = re.sub(r"\\[A-Za-z]+\*?", " ", text)
    return " ".join(html.unescape(text).split())


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.casefold())


def numbers(text: str) -> Counter:
    return Counter(t for t in tokens(text) if re.fullmatch(r"[+-]?\d[\d.,:/%-]*", t))


def score(reference: str, prediction: str) -> dict:
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
