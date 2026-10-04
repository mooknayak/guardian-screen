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
- Amazon Bedrock (optional multi-intent parsing; keyword parser is the fallback)

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

## Demo notes (honest scope)
- Ring and Bee events are **simulated** through `POST /ring-event` (the demo buttons call it); no live device APIs are connected.
- Voice commands arrive as text (typed or Web Speech API in the browser); Alexa+ integration is a planned next step.
- The camera panel is a placeholder feed; media playback is a "now playing" card driven by the user's saved favorites.
- Admin auth (Cognito) and the daily digest schedule (EventBridge) are planned, not yet deployed. The API is open for demo purposes.
- Guardians subscribe to the alert topic by email; one alert reaches every confirmed guardian at the same time.
