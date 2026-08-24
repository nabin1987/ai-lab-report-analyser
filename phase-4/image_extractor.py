import os
from pathlib import Path

from bedrock_client import bedrock_runtime, BEDROCK_MODEL_ID


IMAGE_EXTRACTION_PROMPT = """
You are a laboratory-report transcription engine.

Your ONLY job is to read the laboratory report image and transcribe
relevant laboratory information that is visibly present.

You are NOT a doctor and must NOT provide medical interpretation.

==================================================
STRICT RULES
==================================================

1. Do NOT diagnose any disease or medical condition.

2. Do NOT interpret laboratory results.

3. Do NOT suggest causes for abnormal results.

4. Do NOT calculate missing values.

5. Do NOT invent values.

6. Do NOT correct values based on medical knowledge.

7. Preserve the exact numeric value visible in the report.

8. Preserve the unit exactly as visible in the report.

9. Preserve the reference range exactly as visible in the report.

10. If a laboratory value cannot be read reliably, write:
    [UNCLEAR]

11. If a laboratory field is visibly blank, write:
    [BLANK]

12. Do not infer information that is not visible.

13. Do not reconstruct partially visible values.

14. Do not convert units.

15. Do not round values.

16. Do not calculate derived values.

17. Preserve laboratory test names as shown where possible.

18. Preserve report headings and section names where useful.

==================================================
PRIVACY RULE
==================================================

This is extremely important.

DO NOT extract, reproduce, summarize, or transform patient-identifying
or personally identifying information.

If any of the following appear in the image, IGNORE them completely:

- Patient name
- Name
- Patient ID
- UHID
- VID
- Registration number
- Registration ID
- Report ID
- Accession number
- Reference number
- Ref No
- Phone number
- Mobile number
- Email address
- Home address
- Collection address
- Patient address
- Barcode value
- QR-code value
- Referring doctor's name
- Doctor's name
- Sample collector's name
- Technician's name
- Staff name
- Any other unique personal identifier

Do NOT copy these values into the output.

If a field contains a person's name, output [REDACTED] only if
necessary to preserve the structure of the report. Otherwise omit
the field completely.

==================================================
NON-IDENTIFYING REPORT INFORMATION
==================================================

You MAY extract useful non-identifying metadata such as:

- Report type
- Test name
- Specimen/sample type
- Laboratory name
- Report date
- Collection date
- Release/report date

Do NOT extract age or gender unless specifically required by the
processing pipeline.

==================================================
IMPORTANT NARRATIVE RULE
==================================================

Laboratory reports may contain medical notes, interpretations,
possible causes, diseases, guidelines, or clinical commentary.

Do NOT convert those statements into conclusions about the patient.

For example, if the report says:

"Elevated T4 levels are seen in hyperthyroidism..."

DO NOT produce:

"Patient may have hyperthyroidism."

If narrative text is important to preserve, transcribe it as
REPORT NARRATIVE only. Do not interpret it.

==================================================
OUTPUT FORMAT
==================================================

Return plain text only.

Use this structure:

REPORT TYPE:
<visible report type>

REPORT INFORMATION:

- Laboratory: <laboratory name if visible>
- Specimen Type: <specimen type if visible>
- Report Date: <date if visible>
- Collection Date: <date if visible>

TEST RESULTS:

<test name>: <value> <unit>
Reference range: <range>

<test name>: <value> <unit>
Reference range: <range>

NARRATIVE / IMPRESSION:

<visible laboratory narrative, if relevant>

UNCLEAR OR BLANK VALUES:

<list laboratory values that are unclear or blank>

==================================================
FINAL CHECK
==================================================

Before returning the answer:

- Do not include patient names.
- Do not include UHID or VID.
- Do not include registration numbers.
- Do not include addresses.
- Do not include doctor names.
- Do not include collector names.
- Do not include phone numbers.
- Do not include other personal identifiers.
- Do not diagnose.
- Do not interpret.
- Do not calculate.
- Do not invent.

Return only the requested laboratory information.
"""


def _validate_image(image_path: str) -> str:
    """
    Validate the actual image bytes and return the image format
    expected by Amazon Bedrock.

    The file extension is intentionally NOT trusted because a file
    named .jpg may actually contain WebP image data.
    """

    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Image file not found: {image_path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {image_path}"
        )

    with open(path, "rb") as image_file:
        header = image_file.read(16)

    if not header:
        raise ValueError(
            f"Image file is empty: {image_path}"
        )

    # JPEG
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"

    # PNG
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"

    # GIF
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "gif"

    # WebP
    if (
        header.startswith(b"RIFF")
        and header[8:12] == b"WEBP"
    ):
        return "webp"

    raise ValueError(
        f"Unsupported or unrecognized image format: {image_path}"
    )


def extract_report_text(image_path: str) -> str:
    """
    Extract visible laboratory-report text from an image
    using Amazon Bedrock Converse API.
    """

    image_format = _validate_image(image_path)

    print(
        f"[DEBUG] Extracting report text from: {image_path}"
    )

    print(
        f"[DEBUG] Detected image format: {image_format}"
    )

    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    if not image_bytes:
        raise ValueError(
            f"Image file is empty: {image_path}"
        )

    response = bedrock_runtime.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": IMAGE_EXTRACTION_PROMPT
                    },
                    {
                        "image": {
                            "format": image_format,
                            "source": {
                                "bytes": image_bytes
                            }
                        }
                    }
                ]
            }
        ],
        inferenceConfig={
            "maxTokens": 5000,
            "temperature": 0
        }
    )

    content = (
        response
        .get("output", {})
        .get("message", {})
        .get("content", [])
    )

    text_blocks = [
        block["text"]
        for block in content
        if "text" in block
    ]

    if not text_blocks:
        raise RuntimeError(
            "Bedrock returned no text from the image."
        )

    extracted_text = "\n".join(text_blocks).strip()

    if not extracted_text:
        raise RuntimeError(
            "Bedrock returned an empty extraction result."
        )

    return extracted_text