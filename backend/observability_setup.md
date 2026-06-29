# start observability network
```
docker network create observability
```

# setup loki
```
docker run -d \
  --name loki \
  --network observability \
  -p 3100:3100 \
  grafana/loki:latest
```

# setup grafana
```
docker run -d \
  --name grafana \
  --network observability \
  -p 3000:3000 \
  grafana/grafana:latest
```

# setup grafana alloy
```
docker run -d \
  --name alloy \
  --network observability \
  -p 12345:12345 \
  -v $(pwd)/alloy/config.alloy:/etc/alloy/config.alloy \
  -v $(pwd)/logs:/var/log/huntfact:ro \
  grafana/alloy:latest \
  run /etc/alloy/config.alloy
```
