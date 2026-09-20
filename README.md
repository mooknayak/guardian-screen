# Guardian Screen — Fire TV

AI-native ambient hub for Amazon Fire TV, built for the "Build, Ship, Shape" Amazon Developer Hackathon.
Connects Fire TV, Ring, Bee and Alexa+ into one voice-first, safety-aware experience.

## Modules
- Frictionless Voice & Auto-Play — remote-free voice control
- Deep Searchable Intelligence — multi-intent voice command parsing
- Guardian Layer — Ring/Bee event triage + multi-guardian alert broadcast

## Stack
- AWS Lambda (Python 3.12)
- Amazon DynamoDB
- Amazon SNS (multi-guardian broadcast)
- API Gateway (WebSocket)
- S3 + CloudFront (Fire TV web frontend + admin panel)
- Amazon Cognito (admin auth)

## Structure
```
guardian-screen/  (repo root)
├── lambda/
│   ├── ring_event_handler.py
│   ├── voice_intent_handler.py
│   ├── media_control.py
│   ├── camera_feed.py
│   ├── admin_api.py
│   ├── websocket_handlers.py
│   ├── daily_summary.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   └── admin.html
├── docs/
│   ├── dynamodb-schema.md
│   ├── architecture.md
│   ├── iam-role-policy.json
│   └── GUIDE.md
└── README.md
```
