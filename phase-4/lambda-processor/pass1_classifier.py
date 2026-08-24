import json

from bedrock_client import bedrock_runtime, BEDROCK_MODEL_ID
from prompts import SYSTEM_PROMPT


MODEL_ID = BEDROCK_MODEL_ID


CLASSIFICATION_PROMPT = """
Classify the laboratory report represented by the input.

Supported categories:

- CBC
- Urine routine
- Lipid profile
- Thyroid
- Liver function
- Kidney function
- HbA1c/glucose
- Ultrasound
- Other supported report
- Unknown/unsupported

Return ONLY valid JSON:

{
  "report_type": "string",
  "confidence": 0.0,
  "supported": true,
  "reason": "short explanation"
}

Rules:

- confidence must be between 0 and 1.
- Do not invent report information.
- If the input does not provide enough evidence, use
  "Unknown/unsupported".
- Do not diagnose a medical condition.
"""


def classify_report(report_text: str) -> dict:
    prompt = f"""
{CLASSIFICATION_PROMPT}

REPORT INPUT:
{report_text}
"""

    response = bedrock_runtime.converse(
        modelId=MODEL_ID,
        system=[
            {
                "text": SYSTEM_PROMPT
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        inferenceConfig={
            "maxTokens": 500,
            "temperature": 0
        }
    )

    text = response["output"]["message"]["content"][0]["text"]

    if text.startswith("```json"):
        text = text.replace("```json", "").replace("```", "").strip()
    elif text.startswith("```"):
        text = text.replace("```", "").strip()

    return json.loads(text)
