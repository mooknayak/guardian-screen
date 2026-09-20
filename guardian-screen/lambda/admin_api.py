"""
admin_api.py
Guardian Screen — REST backend for the admin panel: manage guardians
and read event logs. Deploy behind an API Gateway HTTP API (proxy integration).
Runtime: Python 3.12
"""

import json
import os
import uuid
import boto3

dynamodb = boto3.resource("dynamodb")
GUARDIANS_TABLE = os.environ.get("GUARDIANS_TABLE", "Guardians")
EVENTLOGS_TABLE = os.environ.get("EVENTLOGS_TABLE", "EventLogs")

guardians_table = dynamodb.Table(GUARDIANS_TABLE)
eventlogs_table = dynamodb.Table(EVENTLOGS_TABLE)


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body),
    }


def list_guardians(user_id):
    resp = guardians_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id)
    )
    return _response(200, resp.get("Items", []))


def add_guardian(user_id, data):
    item = {
        "user_id": user_id,
        "guardian_id": str(uuid.uuid4()),
        "name": data["name"],
        "phone": data.get("phone", ""),
        "email": data.get("email", ""),
        "priority": data.get("priority", 1),
        "notify_pref": data.get("notify_pref", "all"),
    }
    guardians_table.put_item(Item=item)
    return _response(201, item)


def delete_guardian(user_id, guardian_id):
    guardians_table.delete_item(Key={"user_id": user_id, "guardian_id": guardian_id})
    return _response(204, {})


def list_logs(user_id):
    resp = eventlogs_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id)
    )
    items = sorted(resp.get("Items", []), key=lambda i: i.get("timestamp", 0), reverse=True)
    return _response(200, items)


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod"))
    path = event.get("rawPath", event.get("path", ""))
    qs = event.get("queryStringParameters") or {}
    body = json.loads(event["body"]) if event.get("body") else {}

    user_id = qs.get("user_id") or body.get("user_id")

    if path.endswith("/guardians") and method == "GET":
        return list_guardians(user_id)
    if path.endswith("/guardians") and method == "POST":
        return add_guardian(user_id, body)
    if "/guardians/" in path and method == "DELETE":
        guardian_id = path.rsplit("/", 1)[-1]
        return delete_guardian(user_id, guardian_id)
    if path.endswith("/logs") and method == "GET":
        return list_logs(user_id)

    return _response(404, {"error": "route not found"})
