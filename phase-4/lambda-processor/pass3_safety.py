import json

from bedrock_client import bedrock_runtime
from prompts import SYSTEM_PROMPT
from bedrock_client import bedrock_runtime, BEDROCK_MODEL_ID


MODEL_ID = BEDROCK_MODEL_ID


SAFETY_PROMPT = """
Review the supplied report information for potentially important
values outside the reference ranges explicitly supplied in the report.

Return ONLY valid JSON:

{
  "abnormal_values": [
    {
      "name": "test name",
      "value": "reported value",
      "reference_range": "reported reference range",
      "status": "above_range|below_range",
      "reason": "short factual explanation"
    }
  ],
  "uncertain_values": [
    {
      "name": "test name",
      "reason": "why the value cannot be assessed reliably"
    }
  ],
  "professional_review_recommended": false,
  "review_reason": "short explanation"
}

Rules:

- Never invent values.
- Never invent reference ranges.
- Only compare a value when the report explicitly provides a usable
  reference range.
- Do not diagnose a disease.
- Do not infer a diagnosis from an abnormal value.
- Do not prescribe or recommend medication.
- If the value or reference range is unclear, mark it uncertain.
- An abnormality means the reported value is outside the supplied
  reference range. It does not by itself establish a diagnosis.
- Use conservative language.
"""


def safety_check(
    report_text: str,
    classification: dict,
    explanation: dict
) -> dict:

    prompt = f"""
{SAFETY_PROMPT}

REPORT CLASSIFICATION:
{json.dumps(classification)}

PATIENT EXPLANATION:
{json.dumps(explanation)}

ORIGINAL REPORT INPUT:
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
            "maxTokens": 1500,
            "temperature": 0
        }
    )

    text = response["output"]["message"]["content"][0]["text"]
    
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text.replace("```json", "").replace("```", "").strip()
    elif text.startswith("```"):
        text = text.replace("```", "").strip()
    
    return json.loads(text)