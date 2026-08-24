import json
import os
import tempfile
import requests

from processor import process_report
from image_extractor import extract_report_text


# ============================================================
# Environment variables
# ============================================================

AWS_REGION = os.getenv(
    "BEDROCK_REGION",
    "ap-south-1"
)

DIALOG360_API_KEY = os.getenv(
    "DIALOG360_API_KEY"
)

DIALOG360_BASE_URL = os.getenv(
    "DIALOG360_BASE_URL",
    "https://waba-v2.360dialog.io"
).rstrip("/")

DIALOG360_MESSAGES_PATH = os.getenv(
    "DIALOG360_MESSAGES_PATH",
    "/messages"
)

# Sandbox media retrieval is NOT supported by 360dialog.
# This flag allows us to fail with a clear message rather than
# making a misleading API call.
DIALOG360_SANDBOX = os.getenv(
    "DIALOG360_SANDBOX",
    "false"
).lower() == "true"


# ============================================================
# Lambda entry point
# ============================================================

def lambda_handler(event, context):

    print("[INFO] Processor Lambda started")

    print(
        "[DEBUG] Event:",
        json.dumps(event, ensure_ascii=False)
    )

    try:

        # ----------------------------------------------------
        # 1. Extract WhatsApp message
        # ----------------------------------------------------

        message = extract_message(event)

        message_id = message.get("message_id")
        sender = message.get("sender")
        media_id = message.get("media_id")
        media_type = message.get("message_type")
        mime_type = message.get("mime_type")

        print(
            f"[INFO] message_type={media_type}"
        )

        print(
            f"[INFO] mime_type={mime_type}"
        )

        print(
            f"[INFO] media_id={media_id}"
        )

        print(
            f"[INFO] sender={sender}"
        )

        print(
            f"[INFO] message_id={message_id}"
        )

        # ----------------------------------------------------
        # 2. Validate message
        # ----------------------------------------------------

        if not media_id:

            raise ValueError(
                "Missing media_id in WhatsApp message"
            )

        if media_type != "image":

            raise ValueError(
                f"Unsupported WhatsApp message type: {media_type}"
            )

        # ----------------------------------------------------
        # 3. Sandbox protection
        # ----------------------------------------------------

        if DIALOG360_SANDBOX:

            raise RuntimeError(
                "360dialog Sandbox does not support retrieving "
                "WhatsApp media by media ID. "
                "The webhook can receive the image event, but "
                "the actual image cannot be downloaded in Sandbox. "
                "Use a non-Sandbox 360dialog WhatsApp API channel "
                "for the end-to-end image processing test."
            )

        # ----------------------------------------------------
        # 4. Retrieve media metadata
        # ----------------------------------------------------

        print(
            "[INFO] Getting media metadata from 360dialog"
        )

        media_url = get_media_url(
            media_id
        )

        print(
            "[INFO] Media metadata retrieved successfully"
        )

        # ----------------------------------------------------
        # 5. Download image
        # ----------------------------------------------------

        print(
            "[INFO] Downloading media"
        )

        image_bytes, content_type = download_media(
            media_url
        )

        print(
            "[INFO] Downloaded media: "
            f"{len(image_bytes)} bytes"
        )

        print(
            f"[INFO] Content-Type: {content_type}"
        )

        # ----------------------------------------------------
        # 6. Save image temporarily
        # ----------------------------------------------------

        extension = get_extension(
            content_type
        )

        temp_image_path = None

        try:

            with tempfile.NamedTemporaryFile(
                suffix=extension,
                delete=False
            ) as temp_file:

                temp_file.write(image_bytes)

                temp_image_path = temp_file.name

            print(
                "[INFO] Temporary image created: "
                f"{temp_image_path}"
            )

            # ------------------------------------------------
            # 7. Extract report text
            # ------------------------------------------------

            print(
                "[INFO] Extracting report text"
            )

            report_text = extract_report_text(
                temp_image_path
            )

            print(
                "[INFO] Report extraction completed"
            )

            print(
                "[DEBUG] Extracted report:"
            )

            print(report_text)

            # ------------------------------------------------
            # 8. Run Phase 4 processor
            # ------------------------------------------------

            print(
                "[INFO] Running Phase 4 processor"
            )

            result = process_report(
                report_text
            )

            print(
                "[INFO] Phase 4 processing completed"
            )

            print(
                "[DEBUG] Processing result:"
            )

            print(
                json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False
                )
            )

            # ------------------------------------------------
            # 9. Build WhatsApp response
            # ------------------------------------------------

            patient_message = build_patient_message(
                result
            )

            print(
                "[DEBUG] WhatsApp response:"
            )

            print(patient_message)

            # ------------------------------------------------
            # 10. Send response
            # ------------------------------------------------

            if sender:

                send_whatsapp_message(
                    sender,
                    patient_message
                )

                print(
                    "[INFO] WhatsApp response sent"
                )

            else:

                print(
                    "[WARNING] Sender missing. "
                    "Skipping WhatsApp response."
                )

            # ------------------------------------------------
            # 11. Return
            # ------------------------------------------------

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "processed",
                    "message_id": message_id,
                    "sender": sender
                })
            }

        finally:

            # ------------------------------------------------
            # 12. Delete temporary image
            # ------------------------------------------------

            if temp_image_path:

                try:

                    os.remove(
                        temp_image_path
                    )

                    print(
                        "[INFO] Temporary image deleted"
                    )

                except Exception as cleanup_error:

                    print(
                        "[WARNING] Failed to delete "
                        f"temporary image: {cleanup_error}"
                    )

    except Exception as exc:

        print(
            f"[ERROR] Processor failed: {exc}"
        )

        raise


# ============================================================
# Extract message from webhook event
# ============================================================

def extract_message(event):

    """
    Expected event from webhook Lambda:

    {
        "source": "whatsapp_webhook",
        "message": {
            "message_id": "...",
            "sender": "...",
            "message_type": "image",
            "timestamp": "...",
            "phone_number_id": "...",
            "media_id": "...",
            "mime_type": "image/jpeg",
            "sha256": "...",
            "caption": null
        }
    }
    """

    message = event.get(
        "message"
    )

    if not message:

        raise ValueError(
            "Missing 'message' object in processor event"
        )

    return message


# ============================================================
# 360dialog media metadata
# ============================================================

def get_media_url(media_id):

    """
    Retrieve media metadata from 360dialog.

    For a normal 360dialog WhatsApp API channel:

        GET https://waba-v2.360dialog.io/{media_id}

    Authentication:

        D360-API-KEY: <API_KEY>
    """

    url = (
        f"{DIALOG360_BASE_URL}"
        f"/{media_id}"
    )

    headers = {
        "D360-API-KEY": DIALOG360_API_KEY,
        "Accept": "application/json"
    }

    print(
        "[INFO] Getting media metadata from:"
        f" {DIALOG360_BASE_URL}/{media_id}"
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    print(
        "[DEBUG] 360dialog media response status:"
        f" {response.status_code}"
    )

    print(
        "[DEBUG] 360dialog media response:"
        f" {response.text[:2000]}"
    )

    if response.status_code == 401:

        raise RuntimeError(
            "360dialog returned 401 Unauthorized while "
            "retrieving media. Verify that "
            "DIALOG360_API_KEY is the API key belonging to "
            "the same WhatsApp API channel."
        )

    if response.status_code == 404:

        raise RuntimeError(
            "360dialog returned 404 while retrieving media. "
            "If you are using the 360dialog Sandbox, media "
            "retrieval is not supported by Sandbox."
        )

    response.raise_for_status()

    data = response.json()

    media_url = data.get(
        "url"
    )

    if not media_url:

        raise RuntimeError(
            "360dialog media response did not contain 'url'. "
            f"Response: {json.dumps(data)}"
        )

    return media_url


# ============================================================
# Download media
# ============================================================

def download_media(media_url):

    """
    Download the actual image from the media URL.
    """

    headers = {
        "D360-API-KEY": DIALOG360_API_KEY
    }

    response = requests.get(
        media_url,
        headers=headers,
        timeout=60
    )

    print(
        "[DEBUG] Media download response:"
        f" {response.status_code}"
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        "image/jpeg"
    )

    return (
        response.content,
        content_type
    )


# ============================================================
# File extension
# ============================================================

def get_extension(content_type):

    content_type = (
        content_type
        .lower()
        .split(";")[0]
        .strip()
    )

    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "application/pdf": ".pdf"
    }

    return mapping.get(
        content_type,
        ".jpg"
    )


# ============================================================
# Build patient response
# ============================================================

def build_patient_message(result):

    explanation = result.get(
        "explanation",
        {}
    )

    summary = explanation.get(
        "summary",
        "Your report has been processed."
    )

    observations = explanation.get(
        "observations",
        []
    )

    lines = [
        "🧪 *Lab Report Summary*",
        "",
        summary,
        ""
    ]

    for observation in observations:

        name = observation.get(
            "name",
            "Test"
        )

        value = observation.get(
            "value",
            ""
        )

        unit = observation.get(
            "unit",
            ""
        )

        reference_range = observation.get(
            "reference_range",
            ""
        )

        comparison = observation.get(
            "comparison",
            ""
        )

        explanation_text = observation.get(
            "explanation",
            ""
        )

        lines.append(
            f"*{name}*"
        )

        lines.append(
            f"Result: {value} {unit}"
        )

        if reference_range:

            lines.append(
                f"Reference: {reference_range}"
            )

        if comparison == "above_range":

            lines.append(
                "Status: Above the reference range"
            )

        elif comparison == "below_range":

            lines.append(
                "Status: Below the reference range"
            )

        elif comparison == "within_range":

            lines.append(
                "Status: Within the reference range"
            )

        if explanation_text:

            lines.append(
                explanation_text
            )

        lines.append("")

    if explanation.get(
        "professional_review_recommended",
        False
    ):

        lines.append(
            "⚠️ *Professional review recommended*"
        )

        lines.append(
            "Please discuss these results with a qualified "
            "healthcare professional."
        )

    lines.append("")

    lines.append(
        "_This is an educational explanation of the "
        "laboratory report and is not a medical diagnosis._"
    )

    return "\n".join(
        lines
    )


# ============================================================
# Send WhatsApp message
# ============================================================

def send_whatsapp_message(
    recipient,
    message
):

    """
    Send text message through 360dialog.

    Normal API:

        POST https://waba-v2.360dialog.io/messages

    Sandbox:

        POST https://waba-sandbox.360dialog.io/v1/messages
    """

    url = (
        f"{DIALOG360_BASE_URL}"
        f"{DIALOG360_MESSAGES_PATH}"
    )

    headers = {
        "D360-API-KEY": DIALOG360_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {
            "body": message
        }
    }

    print(
        "[INFO] Sending WhatsApp response to:"
        f" {recipient}"
    )

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    print(
        "[DEBUG] WhatsApp send response:"
        f" {response.status_code}"
    )

    print(
        "[DEBUG] WhatsApp send response body:"
        f" {response.text[:2000]}"
    )

    response.raise_for_status()

    return response.json()