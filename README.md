### Demo stack (Docker A/B/C/D)

This `demo` folder contains a simplified copy of your production layout:

- **Docker-A**: simple status API  
- **Docker-B**: JSON echo API  
- **Docker-C**: calculation API (`/sum?a=1&b=2`)  
- **Docker-D**: rotating message API  

All services:

- Are built with **FastAPI**
- Expose `/`, `/health`, and `/metrics`
- Export the **`fastapi_http_requests_per_minute`** metric per service

### Build images

Build each image from inside its own folder (structure similar to your main codebase):

```bash
cd demo/Docker-A && docker build -t demo-docker-a .
cd ../Docker-B && docker build -t demo-docker-b .
cd ../Docker-C && docker build -t demo-docker-c .
cd ../Docker-D && docker build -t demo-docker-d .
```

### Run containers

Example (Docker A on port 8001, B on 8002, etc.):

```bash
docker run --rm -p 8001:8000 demo-docker-a
docker run --rm -p 8002:8000 demo-docker-b
docker run --rm -p 8003:8000 demo-docker-c
docker run --rm -p 8004:8000 demo-docker-d
```

Then you can hit, for example:

- `http://localhost:8001/`, `http://localhost:8001/health`, `http://localhost:8001/metrics`
- `http://localhost:8002/echo` (POST JSON)
- `http://localhost:8003/sum?a=1&b=2`
- `http://localhost:8004/message`

You can now wire these into **Prometheus + HPA** exactly like the real services, without using any of the client's code or models.

