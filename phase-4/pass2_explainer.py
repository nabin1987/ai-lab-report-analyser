import json

from bedrock_client import bedrock_runtime
from prompts import SYSTEM_PROMPT
from bedrock_client import bedrock_runtime, BEDROCK_MODEL_ID


MODEL_ID = BEDROCK_MODEL_ID


EXPLANATION_PROMPT = """
Create a patient-friendly explanation of the supplied laboratory report.

Return ONLY valid JSON:

{
  "summary": "short plain-language summary",
  "observations": [
    {
      "name": "test name",
      "value": "reported value",
      "unit": "unit if supplied",
      "reference_range": "reference range if supplied",
      "comparison": "within_range|above_range|below_range|unknown",
      "explanation": "simple explanation"
    }
  ],
  "uncertain_values": [
    {
      "name": "test name",
      "reason": "why the value is uncertain"
    }
  ],
  "professional_review_recommended": false
}

Rules:

- Only use values explicitly present in the input.
- Never invent values.
- Never invent units.
- Never invent reference ranges.
- If a reference range is absent, comparison must be "unknown".
- If a value cannot be reliably interpreted, put it in uncertain_values.
- Explain observations without diagnosing disease.
- Do not recommend medication.
- Do not recommend medication changes.
- Do not claim that an abnormal result proves a disease.
- Keep the language simple and understandable.
"""


def explain_report(report_text: str, classification: dict) -> dict:
    prompt = f"""
{EXPLANATION_PROMPT}

REPORT CLASSIFICATION:
{json.dumps(classification)}

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
            "maxTokens": 2000,
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