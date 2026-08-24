import base64
import json
import logging
from typing import Any, Dict, Optional


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build an HTTP response for a Lambda Function URL.
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }


def decode_body(event: Dict[str, Any]) -> str:
    """
    Extract and decode the HTTP request body from a Lambda Function URL event.
    """
    body = event.get("body")

    if body is None:
        return ""

    if event.get("isBase64Encoded", False):
        try:
            return base64.b64decode(body).decode("utf-8")
        except Exception as exc:
            raise ValueError("Unable to decode base64 request body") from exc

    return body


def parse_json_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse the HTTP request body as JSON.
    """
    raw_body = decode_body(event)

    if not raw_body:
        raise ValueError("Request body is empty")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ValueError("Request body is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("Webhook payload must be a JSON object")

    return payload


def extract_messages(payload: Dict[str, Any]) -> list:
    """
    Extract messages from the WhatsApp webhook payload.

    This intentionally handles the common WhatsApp Cloud API-style
    structure while remaining defensive if parts of the payload are absent.
    """
    messages = []

    entries = payload.get("entry", [])

    if not isinstance(entries, list):
        return messages

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        changes = entry.get("changes", [])

        if not isinstance(changes, list):
            continue

        for change in changes:
            if not isinstance(change, dict):
                continue

            value = change.get("value", {})

            if not isinstance(value, dict):
                continue

            value_messages = value.get("messages", [])

            if isinstance(value_messages, list):
                messages.extend(
                    message
                    for message in value_messages
                    if isinstance(message, dict)
                )

    return messages


def extract_message_summary(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract only the information needed by the receive handler.

    Do not log the complete message because future payloads may contain
    sensitive patient/report information.
    """
    message_type = message.get("type")

    summary: Dict[str, Any] = {
        "message_id": message.get("id"),
        "sender": message.get("from"),
        "message_type": message_type,
        "timestamp": message.get("timestamp")
    }

    if message_type == "text":
        text = message.get("text")

        if isinstance(text, dict):
            summary["text"] = text.get("body")

    elif message_type == "image":
        image = message.get("image")

        if isinstance(image, dict):
            summary["media_id"] = image.get("id")
            summary["mime_type"] = image.get("mime_type")

    elif message_type == "document":
        document = message.get("document")

        if isinstance(document, dict):
            summary["media_id"] = document.get("id")
            summary["mime_type"] = document.get("mime_type")
            summary["filename"] = document.get("filename")

    return summary


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda entry point.

    Phase 3 responsibilities:
    - Receive webhook request
    - Validate basic HTTP request
    - Parse JSON
    - Identify WhatsApp messages
    - Extract sender/message/type/text/media metadata
    - Log a safe summary
    - Return HTTP 200 quickly
    """

    request_context = event.get("requestContext", {})
    http = request_context.get("http", {})

    method = http.get("method", event.get("httpMethod"))

    logger.info(
        "Webhook request received: method=%s",
        method
    )

    if method != "POST":
        return response(
            405,
            {
                "success": False,
                "error": "Method not allowed"
            }
        )

    try:
        payload = parse_json_body(event)

    except ValueError as exc:
        logger.warning("Invalid webhook request: %s", str(exc))

        return response(
            400,
            {
                "success": False,
                "error": str(exc)
            }
        )

    messages = extract_messages(payload)

    summaries = [
        extract_message_summary(message)
        for message in messages
    ]

    logger.info(
        "WhatsApp webhook processed: message_count=%d",
        len(summaries)
    )

    for summary in summaries:
        logger.info(
            "WhatsApp message: id=%s type=%s sender_present=%s",
            summary.get("message_id"),
            summary.get("message_type"),
            bool(summary.get("sender"))
        )

    return response(
        200,
        {
            "success": True,
            "message": "Webhook received",
            "message_count": len(summaries)
        }
    )