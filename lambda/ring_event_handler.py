"""
ring_event_handler.py
Guardian Screen — Lambda function that receives a Ring/Bee event,
triages severity, logs it, and broadcasts alerts to all guardians.
Runtime: Python 3.12
"""

import json
import os
import time
import uuid
import boto3

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

GUARDIANS_TABLE = os.environ.get("GUARDIANS_TABLE", "Guardians")
EVENTLOGS_TABLE = os.environ.get("EVENTLOGS_TABLE", "EventLogs")
ALERT_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN")  # SNS topic ARN

guardians_table = dynamodb.Table(GUARDIANS_TABLE)
eventlogs_table = dynamodb.Table(EVENTLOGS_TABLE)


def triage_severity(event_source: str, payload: dict) -> str:
    """Decide how serious an incoming event is."""
    if event_source == "bee" and payload.get("type") in ("sos", "fall_detected"):
        return "emergency"
    if event_source == "ring" and payload.get("visitor_type") == "unknown_person":
        return "medium"
    return "normal"


def build_caption(event_source: str, severity: str, payload: dict) -> str:
    """Short human-readable description (placeholder for an Alexa+/Bedrock call)."""
    if event_source == "ring":
        if payload.get("visitor_type") == "delivery":
            return "डिलीवरी आ गई है"
        if payload.get("visitor_type") == "unknown_person":
            return "अनजान व्यक्ति दरवाज़े पर है"
        return "कोई दरवाज़े पर है"
    if event_source == "bee":
        if payload.get("type") == "sos":
            return "SOS सिग्नल मिला — तुरंत मदद चाहिए"
        if payload.get("type") == "fall_detected":
            return "गिरने का संकेत मिला — कृपया जाँच करें"
    return "नया अलर्ट"


def get_guardians(user_id: str, severity: str):
    """Fetch guardians for this user, filtered by their notify preference."""
    response = guardians_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id)
    )
    guardians = response.get("Items", [])

    if severity == "emergency":
        return sorted(guardians, key=lambda g: g.get("priority", 99))

    # "medium"/"normal": only guardians who want everything, not emergency-only
    return [g for g in guardians if g.get("notify_pref") != "emergency_only"]


def broadcast_alert(guardians, caption: str, severity: str):
    """Publish one SNS message per guardian so all of them are notified together."""
    notified = []
    for g in guardians:
        message = json.dumps({
            "default": caption,
            "sms": caption,
            "email": f"Guardian Screen अलर्ट ({severity}): {caption}",
        })
        sns.publish(
            TopicArn=ALERT_TOPIC_ARN,
            Message=message,
            MessageStructure="json",
            MessageAttributes={
                "guardian_id": {"DataType": "String", "StringValue": g["guardian_id"]},
                "severity": {"DataType": "String", "StringValue": severity},
            },
        )
        notified.append(g["guardian_id"])
    return notified


def log_event(user_id: str, source: str, severity: str, caption: str, notified: list):
    eventlogs_table.put_item(Item={
        "event_id": str(uuid.uuid4()),
        "user_id": user_id,
        "timestamp": int(time.time()),
        "source": source,
        "severity": severity,
        "description": caption,
        "notified_guardians": notified,
        "acknowledged": False,
    })


def lambda_handler(event, context):
    """
    Expected input (from API Gateway / EventBridge):
    {
      "user_id": "user_123",
      "source": "ring" | "bee",
      "payload": { ... device-specific fields ... }
    }
    """
    body = json.loads(event["body"]) if "body" in event else event

    user_id = body["user_id"]
    source = body["source"]
    payload = body.get("payload", {})

    severity = triage_severity(source, payload)
    caption = build_caption(source, severity, payload)

    notified = []
    if severity in ("medium", "emergency"):
        guardians = get_guardians(user_id, severity)
        notified = broadcast_alert(guardians, caption, severity)

    log_event(user_id, source, severity, caption, notified)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "severity": severity,
            "caption": caption,
            "notified_guardians": notified,
        }),
    }
