"""
admin_api.py  (सुधारा हुआ संस्करण)
एडमिन पैनल का बैकएंड: गार्डियंस जोड़ना/हटाना/देखना और इवेंट लॉग देखना।
Runtime: Python 3.12

सुधार:
 1. DynamoDB के नंबर Decimal में आते हैं, json.dumps उन पर फेल हो जाता था -> अब ठीक है।
 2. EventLogs में user_id "सॉर्ट की" है (पार्टीशन की नहीं), इसलिए query() चलता ही नहीं -> अब scan+filter।
"""

import json
import os
import uuid
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb")
GUARDIANS_TABLE = os.environ.get("GUARDIANS_TABLE", "Guardians")
EVENTLOGS_TABLE = os.environ.get("EVENTLOGS_TABLE", "EventLogs")

guardians_table = dynamodb.Table(GUARDIANS_TABLE)
eventlogs_table = dynamodb.Table(EVENTLOGS_TABLE)
sns = boto3.client("sns")
ALERT_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN")  # नया: गार्डियन का ईमेल इसी टॉपिक में जुड़ेगा


def _default(o):
    """Decimal को सामान्य नंबर में बदलता है।"""
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    raise TypeError(f"Cannot serialize {type(o)}")


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, default=_default),
    }


def list_guardians(user_id):
    resp = guardians_table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    return _response(200, resp.get("Items", []))


def add_guardian(user_id, data):
    if not str(data.get("name", "")).strip():
        return _response(400, {"error": "नाम ज़रूरी है"})
    item = {
        "user_id": user_id,
        "guardian_id": str(uuid.uuid4()),
        "name": data["name"],
        "phone": data.get("phone", ""),
        "email": data.get("email", ""),
        "priority": int(data.get("priority") or 1),
        "notify_pref": data.get("notify_pref", "all"),
    }
    guardians_table.put_item(Item=item)
    # गार्डियन को अलर्ट-टॉपिक में जोड़ो: उसे कन्फर्मेशन ईमेल जाएगा, Confirm करते ही हर अलर्ट मिलेगा
    if item["email"] and ALERT_TOPIC_ARN:
        try:
            sns.subscribe(TopicArn=ALERT_TOPIC_ARN, Protocol="email", Endpoint=item["email"])
            item["subscription"] = "pending_confirmation"
        except Exception as e:
            print("subscribe error:", e)
    return _response(201, item)


def delete_guardian(user_id, guardian_id):
    guardians_table.delete_item(Key={"user_id": user_id, "guardian_id": guardian_id})
    return _response(200, {"deleted": guardian_id})


def list_logs(user_id):
    # user_id यहाँ सॉर्ट की है, इसलिए scan + filter (डेमो के लिए ठीक है)
    resp = eventlogs_table.scan(FilterExpression=Attr("user_id").eq(user_id))
    items = resp.get("Items", [])
    items.sort(key=lambda i: i.get("timestamp", 0), reverse=True)
    return _response(200, items[:50])


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod"))
    path = event.get("rawPath", event.get("path", ""))
    qs = event.get("queryStringParameters") or {}
    body = json.loads(event["body"]) if event.get("body") else {}

    user_id = qs.get("user_id") or body.get("user_id")

    if method == "OPTIONS":  # CORS preflight
        return _response(200, {})
    if not user_id:
        return _response(400, {"error": "user_id चाहिए"})

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
