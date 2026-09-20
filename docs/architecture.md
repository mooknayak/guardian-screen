# Architecture — Guardian Screen

## Flow
1. Voice command / Ring / Bee event → API Gateway (WebSocket for voice-in-progress, HTTP for device webhooks)
2. Lambda (Python) — intent parsing (voice_intent_handler.py) or event triage (ring_event_handler.py)
3. DynamoDB — read Users/Guardians, write EventLogs
4. Severity medium/emergency → SNS → all guardians notified together
5. Result pushed back over WebSocket (websocket_handlers.py) → Fire TV frontend updates live
6. Every action logged to EventLogs → visible in admin.html

## AWS services
- Lambda (Python 3.12): ring_event_handler, voice_intent_handler, media_control, camera_feed, admin_api, websocket_handlers, daily_summary
- DynamoDB: Users, Guardians, EventLogs, Connections
- SNS: one topic for guardian alerts, one for daily digest
- API Gateway: one WebSocket API (Fire TV live channel), one HTTP API (admin + device webhooks)
- S3 + CloudFront: hosts frontend/index.html (Fire TV) and frontend/admin.html
- EventBridge: daily cron trigger for daily_summary.py
