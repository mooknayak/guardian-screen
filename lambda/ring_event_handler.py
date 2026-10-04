"""
ring_event_handler.py  (सुधारा हुआ संस्करण)
Ring/Bee इवेंट लेता है -> गंभीरता तय करता है -> लॉग करता है -> SNS से गार्डियंस को अलर्ट भेजता है
-> और WebSocket से Fire TV स्क्रीन पर लाइव अलर्ट भी भेजता है।
Runtime: Python 3.12

ज़रूरी Environment Variables:
  GUARDIANS_TABLE, EVENTLOGS_TABLE, CONNECTIONS_TABLE, ALERT_TOPIC_ARN
  WS_ENDPOINT = https://pojn49xwei.execute-api.ap-south-1.amazonaws.com/prod   (नया! अंत में @connections नहीं)
"""

import json
import os
import time
import uuid
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

GUARDIANS_TABLE = os.environ.get("GUARDIANS_TABLE", "Guardians")
EVENTLOGS_TABLE = os.environ.get("EVENTLOGS_TABLE", "EventLogs")
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE", "Connections")
ALERT_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN")
WS_ENDPOINT = os.environ.get("WS_ENDPOINT")  # WebSocket stage का https URL

guardians_table = dynamodb.Table(GUARDIANS_TABLE)
eventlogs_table = dynamodb.Table(EVENTLOGS_TABLE)
connections_table = dynamodb.Table(CONNECTIONS_TABLE)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",  # ब्राउज़र (index.html) को जवाब पढ़ने देने के लिए
}


def triage_severity(event_source: str, payload: dict) -> str:
    """इवेंट कितना गंभीर है, यह तय करता है।"""
    if event_source == "bee" and payload.get("type") in ("sos", "fall_detected"):
        return "emergency"
    if event_source == "ring" and payload.get("visitor_type") == "unknown_person":
        return "medium"
    return "normal"


def build_caption(event_source: str, severity: str, payload: dict) -> str:
    """छोटा हिंदी विवरण (बाद में Bedrock से बदला जा सकता है)।"""
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
    """इस यूज़र के गार्डियंस लाता है (पसंद के हिसाब से छाँटकर)।"""
    response = guardians_table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    guardians = response.get("Items", [])

    if severity == "emergency":
        return sorted(guardians, key=lambda g: g.get("priority", 99))

    # medium/normal: सिर्फ़ वे जो हर अलर्ट चाहते हैं
    return [g for g in guardians if g.get("notify_pref") != "emergency_only"]


def broadcast_alert(guardians, caption: str, severity: str):
    """सभी गार्डियंस को एक साथ: टॉपिक पर सिर्फ़ एक बार publish।
    हर subscriber को एक ही कॉपी मिलती है (पहले गार्डियन-दर-गार्डियन publish से ईमेल दोहराकर आते थे)।"""
    if not guardians:
        return []
    sns.publish(
        TopicArn=ALERT_TOPIC_ARN,
        Subject=f"Guardian Screen Alert ({severity})",  # SNS Subject सिर्फ़ ASCII होना चाहिए
        Message=json.dumps({
            "default": caption,
            "sms": caption,
            "email": f"Guardian Screen अलर्ट ({severity}): {caption}",
        }),
        MessageStructure="json",
        MessageAttributes={"severity": {"DataType": "String", "StringValue": severity}},
    )
    return [str(g["guardian_id"]) for g in guardians]


def push_to_tv(user_id: str, message: dict):
    """नया: Fire TV स्क्रीन पर WebSocket से लाइव अलर्ट भेजता है।"""
    if not WS_ENDPOINT:
        return 0  # env var नहीं है तो चुपचाप छोड़ दो, बाकी काम चलता रहे
    apigw = boto3.client("apigatewaymanagementapi", endpoint_url=WS_ENDPOINT)
    resp = connections_table.scan(FilterExpression=Attr("user_id").eq(user_id))
    sent = 0
    for item in resp.get("Items", []):
        try:
            apigw.post_to_connection(
                ConnectionId=item["connection_id"],
                Data=json.dumps(message).encode("utf-8"),
            )
            sent += 1
        except apigw.exceptions.GoneException:
            # कनेक्शन बंद हो चुका है, साफ़ कर दो
            connections_table.delete_item(Key={"connection_id": item["connection_id"]})
        except Exception as e:
            print("push error:", e)
    return sent


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
    अपेक्षित इनपुट:
    { "user_id": "user_123", "source": "ring" | "bee", "payload": { ... } }
    """
    body = json.loads(event["body"]) if event.get("body") else event

    user_id = body["user_id"]
    source = body["source"]
    payload = body.get("payload", {})

    severity = triage_severity(source, payload)
    caption = build_caption(source, severity, payload)

    notified = []
    if severity in ("medium", "emergency"):
        guardians = get_guardians(user_id, severity)
        notified = broadcast_alert(guardians, caption, severity)
        # TV पर कैमरा PiP + बैनर दिखाने के लिए
        push_to_tv(user_id, {"action": "show_camera", "severity": severity, "caption": caption})

    log_event(user_id, source, severity, caption, notified)

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({
            "severity": severity,
            "caption": caption,
            "notified_guardians": notified,
        }),
    }
