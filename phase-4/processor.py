import json

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


if __name__ == "__main__":

    synthetic_report = """
    COMPLETE BLOOD COUNT

    Hemoglobin: 13.5 g/dL
    Reference range: 12.0 - 16.0 g/dL

    White Blood Cell Count: 7,200 /µL
    Reference range: 4,000 - 11,000 /µL

    Platelet Count: 250,000 /µL
    Reference range: 150,000 - 450,000 /µL
    """

    result = process_report(synthetic_report)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )