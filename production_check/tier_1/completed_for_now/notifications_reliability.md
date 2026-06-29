# Production Concern: Notifications Reliability (Tier 1)

Focus: ensuring completion notifications are delivered once, at the right time, without silent loss.

## Major Notifications Reliability Issues

1. **No idempotency guard for notification sends** (`backend/router.py`, `backend/orchestrator.py`, `backend/services/notification_sender/handler.py`)  
   Notifications can be triggered from multiple paths (workflow completion and completed-hunt fetch path) without delivery dedupe keys, increasing duplicate-send risk.

2. **No retry policy for transient FCM delivery failures** (`backend/services/notification_sender/notification_sender.py`, `backend/services/notification_sender/handler.py`)  
   Temporary provider/network errors return failure immediately, so recoverable notification attempts are easily lost.

3. **No durable delivery state tracking per hunt/user/token** (backend-wide)  
   Backend does not persist notification attempt/result metadata, so it cannot reliably detect missed sends, replay safely, or prove delivery behavior.

4. **Notification success is inferred from provider call only** (`backend/services/notification_sender/notification_sender.py`)  
   A successful `messaging.send(...)` call is treated as final success with no follow-up confirmation/receipt handling, leaving blind spots on actual device delivery.

## Important Notifications Reliability Gaps

5. **Token validity lifecycle is not managed in sender path** (`backend/services/notification_sender/notification_sender.py`, `backend/services/notification_sender/handler.py`)  
   Invalid/expired tokens return errors but there is no backend cleanup/quarantine flow, so repeated sends can keep failing for the same token.

6. **No bounded backoff or dead-letter handling for notify tasks** (`backend/rmq/schemas.py`, `backend/worker.py`)  
   `retry_count` exists in task schema but notify flow does not apply structured retry/backoff/dead-letter behavior, reducing resilience under intermittent failure.

7. **No reliability telemetry for notification pipeline quality** (`backend/services/notification_sender/notification_sender.py`, `backend/worker.py`)  
   Missing counters for send attempts/success/failure classes/duplicates prevents early detection of notification degradation.
