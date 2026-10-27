"""Provide the local Nemotron OCR demonstration and receipt diagnostics.

Attributes:
    client: Image preparation and bounded inference requests.
    corpus: Synthetic document generation.
    experiment: Closed-loop sweeps and result summaries.
    receipt_metrics: Diagnostic text and numeric-string comparison.

Examples:
    Compare text without starting a GPU server:

    ```python
    from inference_lab.receipt_metrics import score

    recall = score("Total 12.00", "Total 12.00")["numeric_recall"]  # 1.0
    ```

See Also:
    [`inference_lab.cli`][]: Command-line entry point.
    [`inference_lab.serving`][]: Owned-container lifecycle and resource checks.
"""
