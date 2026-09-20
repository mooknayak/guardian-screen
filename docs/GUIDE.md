# Guardian Screen — Complete Setup Guide

## 1. GitHub
1. github.com पर नया repo बनाएँ: guardian-screen
2. इसी Code Vault से हर फाइल का path कॉपी करके वैसा ही फ़ोल्डर structure बनाएँ (lambda/, frontend/, docs/)
3. GitHub मोबाइल ऐप/वेब में "Create new file" से हर path पेस्ट करें, फिर code पेस्ट करें, commit करें

## 2. DynamoDB (4 tables)
Users, Guardians (PK: user_id, SK: guardian_id), EventLogs (PK: event_id, SK: user_id), Connections (PK: connection_id)
— schema की पूरी details docs/dynamodb-schema.md में हैं।

## 3. IAM Role
एक नया Lambda execution role बनाएँ, docs/iam-role-policy.json को custom policy की तरह attach करें।

## 4. Lambda Functions (Python 3.12)
हर .py फाइल के लिए एक अलग Lambda function बनाएँ, code पेस्ट करें, ऊपर वाला IAM role attach करें, environment variables सेट करें (जैसे GUARDIANS_TABLE, EVENTLOGS_TABLE, ALERT_TOPIC_ARN)।

## 5. SNS
एक Topic बनाएँ (guardian-alerts), guardians के फ़ोन/ईमेल subscribe करें (डेमो के लिए मैनुअली)।

## 6. API Gateway
- WebSocket API: routes $connect → connect_handler, $disconnect → disconnect_handler
- HTTP API: /ring-event → ring_event_handler, /voice-command → voice_intent_handler, /guardians, /logs → admin_api

## 7. S3 + CloudFront
Bucket बनाएँ, frontend/index.html और admin.html अपलोड करें (पहले उनमें WEBSOCKET_URL/API_URL अपने असली endpoints से बदल लें), CloudFront distribution बनाकर URL निकालें।

## 8. Test
admin.html से एक guardian जोड़ें → index.html पर demo बटन दबाएँ → SNS अलर्ट आना चाहिए और dashboard पर banner दिखना चाहिए।

## 9. Fire TV पर दिखाना
Fire TV के Silk browser से सीधे CloudFront URL खोलें (सबसे आसान डेमो तरीक़ा), या एक हल्के WebView APK में wrap करके ADB से sideload करें।
