"""
camera_feed.py
Guardian Screen — resolves a "show camera" intent into a feed action
for the Fire TV frontend. Replace STREAM_URLS with real Ring API calls.
Runtime: Python 3.12
"""

import json

STREAM_URLS = {
    "outdoor": "https://your-cloudfront-domain.example/demo/outdoor-feed.mp4",
    "front_door": "https://your-cloudfront-domain.example/demo/front-door-feed.mp4",
}


def lambda_handler(event, context):
    body = json.loads(event["body"]) if "body" in event else event
    camera = body.get("camera", "front_door")

    action = {
        "action": "show_camera",
        "camera": camera,
        "feed_url": STREAM_URLS.get(camera, STREAM_URLS["front_door"]),
    }

    return {"statusCode": 200, "body": json.dumps(action)}
