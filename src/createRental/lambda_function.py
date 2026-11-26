import base64
import json
import os
import uuid
from datetime import date

import boto3

BUCKET_NAME = os.environ.get("BUCKET_NAME", "phone-rental-533730")
s3 = boto3.client("s3")

REQUIRED_STRINGS = ["phoneModel", "renterName", "renterContact", "rentDate", "dueDate"]


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def lambda_handler(event, context):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return response(400, {"message": "Invalid JSON"})

    if not isinstance(data, dict):
        return response(400, {"message": "Body must be a JSON object"})

    missing = [f for f in REQUIRED_STRINGS + ["dailyRate"] if data.get(f) in (None, "")]
    if missing:
        return response(400, {"message": f"Missing fields: {', '.join(missing)}"})

    rate = data["dailyRate"]
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or rate <= 0:
        return response(400, {"message": "dailyRate must be a positive number"})

    rent_date = parse_date(data["rentDate"])
    due_date = parse_date(data["dueDate"])
    if rent_date is None or due_date is None:
        return response(400, {"message": "Dates must use format YYYY-MM-DD"})
    if due_date < rent_date:
        return response(400, {"message": "dueDate must not be before rentDate"})

    item = {
        "rentalId": str(uuid.uuid4()),
        "phoneModel": data["phoneModel"],
        "renterName": data["renterName"],
        "renterContact": data["renterContact"],
        "rentDate": data["rentDate"],
        "dueDate": data["dueDate"],
        "dailyRate": rate,
        "status": "RENTED",
        "returnDate": None,
        "lateFee": 0,
    }
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=f"rentals/{item['rentalId']}.json",
        Body=json.dumps(item),
        ContentType="application/json",
    )
    return response(201, item)