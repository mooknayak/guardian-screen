"""
voice_intent_handler.py
Guardian Screen — parses a (possibly multi-part) voice command into
separate tasks and dispatches each to the right action.
Runtime: Python 3.12

For the hackathon MVP this uses simple keyword-based splitting.
Swap parse_intents() for an Amazon Bedrock call for production-grade NLU.
"""

import json
import os
import re
import boto3

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

GUARDIANS_TABLE = os.environ.get("GUARDIANS_TABLE", "Guardians")
ALERT_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN")

guardians_table = dynamodb.Table(GUARDIANS_TABLE)

CAMERA_WORDS = ["कैमरा", "camera", "darwaza", "दरवाज़ा"]
MEDIA_WORDS = ["चलाओ", "play", "एपिसोड", "episode", "movie", "मूवी"]
SOS_WORDS = ["बचाओ", "help", "sos", "मदद"]
SPLIT_WORDS = [" और ", " and ", ",", " फिर "]


def split_command(text: str):
    """Break one sentence into candidate sub-commands."""
    pattern = "|".join(re.escape(w) for w in SPLIT_WORDS)
    parts = re.split(pattern, text)
    return [p.strip() for p in parts if p.strip()]


def classify(part: str) -> str:
    low = part.lower()
    if any(w in low or w in part for w in SOS_WORDS):
        return "emergency"
    if any(w in low or w in part for w in CAMERA_WORDS):
        return "camera"
    if any(w in low or w in part for w in MEDIA_WORDS):
        return "media"
    return "unknown"


def parse_intents(text: str):
    tasks = []
    for part in split_command(text):
        tasks.append({"type": classify(part), "text": part})
    return tasks


def trigger_emergency(user_id: str, text: str):
    response = guardians_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id)
    )
    guardians = sorted(response.get("Items", []), key=lambda g: g.get("priority", 99))
    for g in guardians:
        sns.publish(
            TopicArn=ALERT_TOPIC_ARN,
            Message=json.dumps({
                "default": f"वॉइस SOS: {text}",
                "sms": f"वॉइस SOS: {text}",
            }),
            MessageStructure="json",
            MessageAttributes={
                "guardian_id": {"DataType": "String", "StringValue": g["guardian_id"]},
                "severity": {"DataType": "String", "StringValue": "emergency"},
            },
        )
    return [g["guardian_id"] for g in guardians]


def lambda_handler(event, context):
    """
    Expected input:
    { "user_id": "user_123", "command_text": "बाहर का कैमरा दिखाओ और अगला एपिसोड चलाओ" }
    """
    body = json.loads(event["body"]) if "body" in event else event
    user_id = body["user_id"]
    command_text = body["command_text"]

    tasks = parse_intents(command_text)
    results = []

    for task in tasks:
        if task["type"] == "camera":
            results.append({"action": "show_camera", "camera": "outdoor"})
        elif task["type"] == "media":
            results.append({"action": "play_next_episode"})
        elif task["type"] == "emergency":
            notified = trigger_emergency(user_id, task["text"])
            results.append({"action": "emergency_triggered", "notified_guardians": notified})
        else:
            results.append({"action": "clarify", "text": task["text"]})

    return {
        "statusCode": 200,
        "body": json.dumps({"tasks": tasks, "actions": results}),
    }
