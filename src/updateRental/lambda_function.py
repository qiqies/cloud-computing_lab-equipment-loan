import base64
import json
import os
import uuid
from datetime import date, datetime, timezone

import boto3
from botocore.exceptions import ClientError

BUCKET_NAME = os.environ.get("BUCKET_NAME", "phone-rental-533730")
s3 = boto3.client("s3")


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def get_rental_id(event):
    """Ambil id dari path param (API Gateway), query string, atau segmen terakhir path (Function URL)."""
    rid = (event.get("pathParameters") or {}).get("id")
    if not rid:
        rid = (event.get("queryStringParameters") or {}).get("id")
    if not rid:
        rid = (event.get("rawPath") or "").strip("/").split("/")[-1]
    try:
        return str(uuid.UUID(rid))
    except (ValueError, AttributeError, TypeError):
        return None


def key_for(rid):
    return f"rentals/{rid}.json"

UPDATABLE = ["phoneModel", "renterName", "renterContact", "rentDate", "dueDate", "dailyRate", "status", "returnDate"]
VALID_STATUS = ["RENTED", "RETURNED"]
LATE_FEE_MULTIPLIER = 2  # denda per hari = dailyRate x 2


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def lambda_handler(event, context):
    rid = get_rental_id(event)
    if rid is None:
        return response(400, {"message": "Invalid or missing rental id"})

    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return response(400, {"message": "Invalid JSON"})
    if not isinstance(data, dict):
        return response(400, {"message": "Body must be a JSON object"})

    changes = {k: v for k, v in data.items() if k in UPDATABLE}
    if not changes:
        return response(400, {"message": "No updatable fields provided"})

    try:
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key_for(rid))
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404", "NotFound"):
            return response(404, {"message": "Rental not found"})
        raise
    item = json.loads(obj["Body"].read())
    item.update(changes)

    for f in ["phoneModel", "renterName", "renterContact"]:
        if not isinstance(item.get(f), str) or not item[f].strip():
            return response(400, {"message": f"{f} must be a non-empty string"})
    rate = item.get("dailyRate")
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or rate <= 0:
        return response(400, {"message": "dailyRate must be a positive number"})
    rent_date, due_date = parse_date(item.get("rentDate")), parse_date(item.get("dueDate"))
    if rent_date is None or due_date is None:
        return response(400, {"message": "Dates must use format YYYY-MM-DD"})
    if due_date < rent_date:
        return response(400, {"message": "dueDate must not be before rentDate"})
    if item.get("status") not in VALID_STATUS:
        return response(400, {"message": "status must be RENTED or RETURNED"})

    if item["status"] == "RETURNED":
        if not item.get("returnDate"):
            item["returnDate"] = datetime.now(timezone.utc).date().isoformat()
        return_date = parse_date(item["returnDate"])
        if return_date is None:
            return response(400, {"message": "returnDate must use format YYYY-MM-DD"})
        late_days = max(0, (return_date - due_date).days)
        item["lateFee"] = late_days * rate * LATE_FEE_MULTIPLIER
    else:
        item["returnDate"] = None
        item["lateFee"] = 0

    s3.put_object(Bucket=BUCKET_NAME, Key=key_for(rid), Body=json.dumps(item), ContentType="application/json")
    return response(200, item)
