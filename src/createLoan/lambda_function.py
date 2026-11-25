import json
import os
import uuid

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "Loans")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

REQUIRED_FIELDS = ["equipmentName", "borrowerName", "borrowDate", "dueDate"]


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    try:
        data = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"message": "Invalid JSON"})

    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        return response(400, {"message": f"Missing fields: {', '.join(missing)}"})

    item = {
        "loanId": str(uuid.uuid4()),
        "equipmentName": data["equipmentName"],
        "borrowerName": data["borrowerName"],
        "borrowDate": data["borrowDate"],
        "dueDate": data["dueDate"],
        "status": "BORROWED",
    }
    table.put_item(Item=item)
    return response(201, item)