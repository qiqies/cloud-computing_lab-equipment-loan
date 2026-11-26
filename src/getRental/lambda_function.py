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


def lambda_handler(event, context):
    rid = get_rental_id(event)
    if rid is None:
        return response(400, {"message": "Invalid or missing rental id"})
    try:
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key_for(rid))
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404", "NotFound"):
            return response(404, {"message": "Rental not found"})
        raise
    return response(200, json.loads(obj["Body"].read()))
