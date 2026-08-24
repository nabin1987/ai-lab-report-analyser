from pathlib import Path

from bedrock_client import (
    bedrock_runtime,
    BEDROCK_MODEL_ID
)


IMAGE_EXTRACTION_PROMPT = """
You are an accurate laboratory-report transcription engine.

Your task is to read the laboratory report image and transcribe ONLY
information that is visibly present in the image.

IMPORTANT RULES:

1. Do NOT diagnose any disease.
2. Do NOT interpret the medical results.
3. Do NOT calculate missing values.
4. Do NOT invent values.
5. Do NOT correct values based on what you think they should be.
6. Preserve the exact value shown in the report.
7. Preserve the unit exactly as shown where possible.
8. Preserve the reference range exactly as shown.
9. If a value is unclear, write:
   [UNCLEAR]
10. If a field is blank, write:
   [BLANK]
11. Preserve report headings and section names.
12. Preserve table rows.
13. Include the report type/title if visible.
14. Ignore QR codes and barcodes.
15. Do not infer patient information.

The output will be passed to another AI pipeline for
classification, explanation and safety checking.

Return plain text only.

Use this structure:

REPORT TYPE:
<visible report title>

REPORT INFORMATION:

- report type
- test name
- report date
- specimen type
- laboratory name

Do NOT extract:

- patient name
- patient phone number
- patient address
- UHID
- registration number
- patient ID
- accession number
- barcode values
- QR-code values
- referring doctor's name
- collector's name
- other unique personal identifiers

TEST RESULTS:

<test name>: <value> <unit>
Reference range: <range>

NARRATIVE / IMPRESSION:

<visible narrative text>

UNCLEAR OR BLANK VALUES:

<list unclear or blank values>

Again: reproduce what is visible.
Do not add medical interpretation.
"""


def _validate_image(image_path: str) -> str:

    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Image file not found: {image_path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {image_path}"
        )

    extension = path.suffix.lower()

    supported_formats = {
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".png": "png",
        ".gif": "gif",
        ".webp": "webp",
    }

    if extension not in supported_formats:
        raise ValueError(
            f"Unsupported image format: {extension}"
        )

    return supported_formats[extension]


def extract_report_text(image_path: str) -> str:

    image_format = _validate_image(image_path)

    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    if not image_bytes:
        raise ValueError(
            f"Image file is empty: {image_path}"
        )

    print(
        f"[DEBUG] Extracting report image: {image_path}"
    )

    print(
        f"[DEBUG] Detected image format: {image_format}"
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
            "Bedrock returned no text from image."
        )

    extracted_text = "\n".join(
        text_blocks
    ).strip()

    if not extracted_text:
        raise RuntimeError(
            "Bedrock returned empty extraction result."
        )

    return extracted_text