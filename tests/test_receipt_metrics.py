from inference_lab.receipt_metrics import plain_text, score


def test_order_and_overlap():
    result = score("A B C", "a c")
    assert result["rouge_l_precision"] == 1
    assert result["rouge_l_recall"] == 2 / 3
    assert result["rouge_l_f1"] == 0.8


def test_numeric_sign_separator_duplicate_and_boundary():
    result = score("-60.000 12 12 5,455", "60.000 312 12 5.455")
    assert result["numeric_matched_count"] == 1
    assert result["numeric_recall"] == 0.25
    assert result["missing_numbers"] == ["-60.000", "12", "5,455"]


def test_empty_predictions_and_absent_numbers():
    result = score("total 12", "")
    assert result["rouge_l_f1"] == 0
    assert result["numeric_recall"] == 0
    assert score("hello", "hello")["numeric_recall"] is None
    assert score("", "extra")["rouge_l_f1"] is None


def test_coordinates_do_not_become_predicted_numbers():
    assert plain_text("<x_0.12><y_0.2>Total -60.000<class_Text>") == "Total -60.000"


def test_latex_table_markup_keeps_cell_values():
    text = plain_text(r"\begin{tabular}{cc} Total & \textbf{60.000} \\ \end{tabular}")
    result = score("Total 60.000", text)
    assert result["rouge_l_f1"] == 1
    assert result["numeric_recall"] == 1


def test_multicolumn_layout_numbers_are_not_receipt_numbers():
    text = plain_text(r"\multicolumn{2}{c}{Rp. 91,000}")
    result = score("2 Rp. 91,000", text)
    assert result["numeric_matched_count"] == 1
    assert result["missing_numbers"] == ["2"]
