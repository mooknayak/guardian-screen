# DynamoDB Schema — Guardian Screen

## Table: Users
| Attribute       | Type   | Notes                              |
|-----------------|--------|-------------------------------------|
| user_id (PK)    | String | Partition key                      |
| name            | String |                                     |
| favorite_shows  | List   | For "next episode" style commands  |
| last_context    | Map    | Last voice command context         |

## Table: Guardians
| Attribute        | Type   | Notes                                    |
|------------------|--------|--------------------------------------------|
| user_id (PK)     | String | Which user this guardian belongs to        |
| guardian_id (SK) | String | Sort key — one user can have many guardians |
| name             | String |                                             |
| phone            | String | For SNS SMS                                |
| email            | String | For SNS email                              |
| priority         | Number | 1 = first to notify, 2 = escalation, ...   |
| notify_pref      | String | "all" / "emergency_only"                   |

## Table: EventLogs
| Attribute         | Type   | Notes                                   |
|-------------------|--------|-------------------------------------------|
| event_id (PK)     | String | UUID                                      |
| user_id (SK)      | String |                                            |
| timestamp         | Number | Epoch seconds                             |
| source            | String | "ring" / "bee" / "voice"                  |
| severity          | String | "normal" / "medium" / "emergency"         |
| description       | String | AI-generated caption                      |
| notified_guardians| List   | Which guardians were alerted              |
| acknowledged      | Boolean| Did any guardian respond in time          |
