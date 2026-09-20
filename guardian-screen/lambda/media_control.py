"""
media_control.py
Guardian Screen — resolves a "play" intent into a concrete media action
using the user's saved favorites in DynamoDB.
Runtime: Python 3.12
"""

import json
import os
import boto3

dynamodb = boto3.resource("dynamodb")
USERS_TABLE = os.environ.get("USERS_TABLE", "Users")
users_table = dynamodb.Table(USERS_TABLE)


def lambda_handler(event, context):
    body = json.loads(event["body"]) if "body" in event else event
    user_id = body["user_id"]

    response = users_table.get_item(Key={"user_id": user_id})
    user = response.get("Item", {})
    favorites = user.get("favorite_shows", [])

    if not favorites:
        return {
            "statusCode": 200,
            "body": json.dumps({"action": "clarify", "text": "कौन-सा शो चलाना है?"}),
        }

    # MVP: just resume the most recently watched favorite
    show = favorites[0]
    action = {
        "action": "play",
        "title": show.get("title"),
        "next_episode": show.get("next_episode", 1),
        "source": show.get("source", "catalog"),
    }

    return {"statusCode": 200, "body": json.dumps(action)}
