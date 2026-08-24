from pass1_classifier import classify_report
from pass2_explainer import explain_report
from pass3_safety import safety_check


def process_report(report_text: str) -> dict:

    classification = classify_report(report_text)

    explanation = explain_report(
        report_text,
        classification
    )

    safety = safety_check(
        report_text,
        classification,
        explanation
    )

    return {
        "classification": classification,
        "explanation": explanation,
        "safety": safety
    }