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
import time
import uuid
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

GUARDIANS_TABLE = os.environ.get("GUARDIANS_TABLE", "Guardians")
ALERT_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN")

USERS_TABLE = os.environ.get("USERS_TABLE", "Users")
EVENTLOGS_TABLE = os.environ.get("EVENTLOGS_TABLE", "EventLogs")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID")  # खाली हो तो सिर्फ़ keyword वाला पार्सर चलेगा

guardians_table = dynamodb.Table(GUARDIANS_TABLE)
users_table = dynamodb.Table(USERS_TABLE)
eventlogs_table = dynamodb.Table(EVENTLOGS_TABLE)

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


def parse_with_bedrock(text: str):
    """टूटी-फूटी/हिंग्लिश कमांड को Amazon Bedrock से टास्क में बाँटता है। कुछ भी गड़बड़ हो तो None लौटाता है।"""
    if not BEDROCK_MODEL_ID:
        return None
    try:
        prompt = ("नीचे की वॉइस कमांड को अलग-अलग टास्क में बाँटो। हर टास्क का type इनमें से एक हो: "
                  "camera, media, emergency, unknown। सिर्फ़ JSON सूची लौटाओ, जैसे "
                  '[{"type":"camera","text":"..."}]। कमांड: ' + text)
        client = boto3.client("bedrock-runtime")
        r = client.converse(modelId=BEDROCK_MODEL_ID,
                            messages=[{"role": "user", "content": [{"text": prompt}]}],
                            inferenceConfig={"maxTokens": 300, "temperature": 0})
        raw = r["output"]["message"]["content"][0]["text"]
        tasks = json.loads(raw[raw.index("["): raw.rindex("]") + 1])
        ok = {"camera", "media", "emergency", "unknown"}
        tasks = [{"type": t["type"], "text": str(t.get("text", ""))} for t in tasks if t.get("type") in ok]
        return tasks or None
    except Exception as e:
        print("bedrock fallback:", e)
        return None


def parse_intents(text: str):
    tasks = parse_with_bedrock(text)
    if tasks:
        return tasks
    return [{"type": classify(p), "text": p} for p in split_command(text)]  # fallback: keywords


def get_favorite(user_id: str):
    """Users तालिका से पसंदीदा शो; न मिले तो डेमो शो ताकि डेमो कभी न रुके।"""
    try:
        favs = users_table.get_item(Key={"user_id": user_id}).get("Item", {}).get("favorite_shows", [])
        if favs:
            return favs[0]
    except Exception as e:
        print("favorite lookup:", e)
    return {"title": "Panchayat", "next_episode": 4}


def log_voice(user_id: str, severity: str, text: str, notified: list):
    eventlogs_table.put_item(Item={
        "event_id": str(uuid.uuid4()), "user_id": user_id, "timestamp": int(time.time()),
        "source": "voice", "severity": severity, "description": text,
        "notified_guardians": notified, "acknowledged": False,
    })


def trigger_emergency(user_id: str, text: str):
    response = guardians_table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    guardians = sorted(response.get("Items", []), key=lambda g: g.get("priority", 99))
    if guardians:  # एक ही publish: हर subscriber को एक कॉपी
        sns.publish(
            TopicArn=ALERT_TOPIC_ARN,
            Subject="Guardian Screen Alert (emergency)",
            Message=json.dumps({"default": f"वॉइस SOS: {text}", "sms": f"वॉइस SOS: {text}",
                                "email": f"Guardian Screen वॉइस SOS: {text}"}),
            MessageStructure="json",
            MessageAttributes={"severity": {"DataType": "String", "StringValue": "emergency"}},
        )
    return [str(g["guardian_id"]) for g in guardians]


def lambda_handler(event, context):
    """
    Expected input:
    { "user_id": "user_123", "command_text": "बाहर का कैमरा दिखाओ और अगला एपिसोड चलाओ" }
    """
    body = json.loads(event["body"]) if event.get("body") else event
    user_id = body["user_id"]
    command_text = body["command_text"]

    tasks = parse_intents(command_text)
    results = []

    for task in tasks:
        if task["type"] == "camera":
            results.append({"action": "show_camera", "camera": "outdoor"})
        elif task["type"] == "media":
            fav = get_favorite(user_id)
            results.append({"action": "play_next_episode", "title": fav.get("title"),
                            "next_episode": int(fav.get("next_episode", 1))})
        elif task["type"] == "emergency":
            notified = trigger_emergency(user_id, task["text"])
            results.append({"action": "emergency_triggered", "notified_guardians": notified})
            log_voice(user_id, "emergency", task["text"], notified)
        else:
            results.append({"action": "clarify", "text": task["text"]})

    return {
        "statusCode": 200,
        # नया: ब्राउज़र को जवाब पढ़ने देने के लिए CORS हेडर
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"tasks": tasks, "actions": results}),
    }
