"""
websocket_handlers.py
Guardian Screen — WebSocket connect/disconnect handlers and a helper
to push live updates to a connected Fire TV screen.
Runtime: Python 3.12
"""

import json
import os
import boto3

dynamodb = boto3.resource("dynamodb")
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE", "Connections")
connections_table = dynamodb.Table(CONNECTIONS_TABLE)


def connect_handler(event, context):
    connection_id = event["requestContext"]["connectionId"]
    user_id = (event.get("queryStringParameters") or {}).get("user_id", "unknown")
    connections_table.put_item(Item={"connection_id": connection_id, "user_id": user_id})
    return {"statusCode": 200}


def disconnect_handler(event, context):
    connection_id = event["requestContext"]["connectionId"]
    connections_table.delete_item(Key={"connection_id": connection_id})
    return {"statusCode": 200}


def push_to_user(user_id: str, message: dict, endpoint_url: str):
    """Call this from other Lambdas to push a live update to a user's Fire TV."""
    apigw = boto3.client("apigatewaymanagementapi", endpoint_url=endpoint_url)
    resp = connections_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("user_id").eq(user_id)
    )
    for item in resp.get("Items", []):
        try:
            apigw.post_to_connection(
                ConnectionId=item["connection_id"],
                Data=json.dumps(message).encode("utf-8"),
            )
        except apigw.exceptions.GoneException:
            connections_table.delete_item(Key={"connection_id": item["connection_id"]})
