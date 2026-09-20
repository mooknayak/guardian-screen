"""
daily_summary.py
Guardian Screen — scheduled once a day via an EventBridge rule.
Summarizes today's EventLogs and sends a short digest.
Runtime: Python 3.12
"""

import json
import os
import time
import boto3

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

EVENTLOGS_TABLE = os.environ.get("EVENTLOGS_TABLE", "EventLogs")
DIGEST_TOPIC_ARN = os.environ.get("DIGEST_TOPIC_ARN")

eventlogs_table = dynamodb.Table(EVENTLOGS_TABLE)


def build_summary(items):
    if not items:
        return "आज कोई नया इवेंट दर्ज नहीं हुआ।"
    counts = {}
    for i in items:
        counts[i["source"]] = counts.get(i["source"], 0) + 1
    parts = [f"{k}: {v}" for k, v in counts.items()]
    return "आज की समरी — " + ", ".join(parts)


def lambda_handler(event, context):
    day_start = int(time.time()) - 24 * 60 * 60
    resp = eventlogs_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("timestamp").gte(day_start)
    )
    items = resp.get("Items", [])
    summary = build_summary(items)

    if DIGEST_TOPIC_ARN:
        sns.publish(TopicArn=DIGEST_TOPIC_ARN, Message=summary)

    return {"statusCode": 200, "body": json.dumps({"summary": summary, "count": len(items)})}
