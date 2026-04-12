# 🔹 High-level system (your design)

```text
Client → FastAPI → Queue (RabbitMQ)
                     ↓
               Worker Pool (N workers)
                     ↓
         Result stored + FCM notification
```

---

# 🔹 1. Core components (exact roles)

## ✅ Backend API

Use: **FastAPI**

Responsibilities:

* Accept request
* Apply **backpressure check**
* Create job (with metadata)
* Push to `download_queue`

---

## ✅ Queue system

Use: **RabbitMQ**

You create 4 queues:

* `download_queue`
* `transcription_queue`
* `ai_queue`
* `notification_queue`

👉 RabbitMQ only:

* stores jobs
* delivers jobs to workers

---

## ✅ Worker pool (THIS is the core)

* You run **N identical worker processes**
* Each worker:

  * can execute **any stage**
  * pulls jobs based on **priority**

---

# 🔹 2. Worker behavior (precise)

Each worker runs:

```text
LOOP:
  try fetch from ai_queue
  else try transcription_queue
  else try download_queue
  else try notification_queue

  process job
  push next stage job
```

---

## 🔹 Job flow (end-to-end)

### Step 1: Request comes

```text
FastAPI → push job → download_queue
```

---

### Step 2: Worker picks download

```text
download_queue → worker → download + audio extract
→ push → transcription_queue
```

---

### Step 3: Transcription

```text
transcription_queue → worker → transcribe
→ push → ai_queue
```

---

### Step 4: AI

```text
ai_queue → worker → LLM processing
→ store result (DB)
→ push → notification_queue
```

---

### Step 5: Notification

Use: **Firebase Cloud Messaging**

```text
notification_queue → worker → send push
```

---

# 🔹 3. Worker pool setup

You decide:

```text
N = total workers (e.g. 100)
```

Run:

* 100 identical processes

👉 No specialization
👉 No separate worker types

---

# 🔹 4. Priority implementation (important)

You implement priority **in the worker logic**, not RabbitMQ.

Order:

```text
AI > Transcription > Download > Notification
```

👉 Workers always try higher queue first

---

# 🔹 5. Backpressure (controller logic)

This is **critical**

In FastAPI:

```text
if ai_queue_size > THRESHOLD:
    reject request (429)
else:
    enqueue download job
```

👉 Only check **bottleneck queue (AI)**

---

# 🔹 6. Data you must pass in jobs

Each job should contain:

* `task_id`
* `user_id`
* `cdn_url` (initially)
* intermediate file references (audio path, transcript, etc.)

---

# 🔹 7. Storage

* Files → S3 / disk
* Results → DB (PostgreSQL)

---

# 🔹 8. Failure handling (minimal)

* If worker crashes:

  * RabbitMQ requeues job automatically
* Add retry count in job metadata

---

# 🔹 9. Deployment (simple version)

Start with:

* 1 machine:

  * FastAPI
  * RabbitMQ
  * workers (multiple processes)

Later:

* split into multiple machines if needed

---

# 🔹 10. What you are NOT doing (important)

* ❌ No separate worker types
* ❌ No per-stage worker pools
* ❌ No orchestration engine

---

# 🔥 Final mental model

```text
Queues = stages
Workers = generic processors
Priority = execution control
Backpressure = intake control
```

---

# 🔚 Final confirmation

Your architecture is now:

> ✔ Single worker pool
> ✔ Multi-queue pipeline
> ✔ Pull-based workers
> ✔ Priority scheduling
> ✔ Backpressure

And this is:

* clean
* implementable
* scalable

---
