# start docker and migrate

docker run -d \
  --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=mydb \
  -p 5432:5432 \
  -v postgres-data:/var/lib/postgresql/data \
  postgres:16

uv run alembic upgrade head


# start rabbitmq
docker run -d \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management

# start chromadb
docker run -d -p 9275:8000 chromadb/chroma

# setup .env

# start backend
uv run python -m main

# start orchestrator
uv run python -m orchestrator

# start worker
uv run python -m worker

# update backend url in android
  • android/app/build.gradle.kts
    • Change line with default backend URL:
      • ?: "https://api.huntfact.com/"
      • Replace with your local URL, e.g. ?: "http://10.0.2.2:8000/" (emulator) or ?: "http://<LAN_IP>:8000/" (real device).
    • Also ensure BACKEND_BASE_URL is set via Gradle property/env if you prefer override (same key name).

  • android/app/src/main/res/xml/network_security_config.xml
    • Change the <domain> line under cleartextTrafficPermitted="true":
      • <domain includeSubdomains="true">10.34.64.60</domain>
      • Replace with host you use in backend URL (e.g. 10.0.2.2 for emulator or your LAN IP for device).
