docker run -d \
  --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=mydb \
  -p 5432:5432 \
  -v postgres-data:/var/lib/postgresql/data \
  postgres:16

docker run -d \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management

docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7 \
  redis-server --requirepass yourpassword

docker run -d -p 9275:8000 chromadb/chroma
