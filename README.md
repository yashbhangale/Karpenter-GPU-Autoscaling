# GPU Autoscaling with Karpenter + HPA (Request-Based Scaling)

This setup demonstrates how to efficiently scale GPU-based ML workloads on Kubernetes (EKS) using **request-driven autoscaling**, reducing compute cost and improving responsiveness.


## Overview

Traditional GPU autoscaling (CPU/GPU utilization-based) is slow and reactive.

This project implements a better approach:

 **Scale based on user demand (requests per minute)**
 **Let Karpenter handle infrastructure scaling dynamically**

## Architecture Flow

```
User Traffic → FastAPI → Prometheus Metrics → HPA → Pending Pods → Karpenter → GPU Nodes
```

1. Incoming requests hit FastAPI `/predict` endpoints.
2. Middleware tracks request timestamps.
3. `fastapi_http_requests_per_minute` metric is calculated per pod.
4. Prometheus scrapes `/metrics`.
5. Prometheus Adapter exposes it as a Kubernetes **custom metric**.
6. HPA scales pods based on RPM.
7. If pods are pending → Karpenter provisions GPU nodes.
8. When traffic drops → pods scale down → nodes terminate.

---

## Karpenter Configuration Guide

To set up and configure Karpenter in your cluster (especially if you are migrating from Cluster Autoscaler), refer to the official documentation:

[Karpenter Migration Guide (Official Docs)](https://karpenter.sh/docs/getting-started/migrating-from-cas/)

## Metrics Design

Each service exposes:

* `fastapi_http_requests_total` (Counter)
* `fastapi_http_request_duration_seconds` (Histogram)
* `fastapi_http_requests_active` (Gauge)
* `fastapi_http_requests_per_minute` (Gauge) ← **core metric**

### How RPM works:

* Tracks request timestamps
* Calculates requests in the last 60 seconds
* Updates every second

---

## Scaling Logic

### HPA Configuration

* Metric type: `Pods`
* Metric name: `fastapi_http_requests_per_minute`
* Target:

  * `averageValue: 50` (50 RPM per pod)
* Scaling:

  * `minReplicas: 0` (scale to zero)
  * `maxReplicas`: varies per service

---

## Components

### 1. FastAPI Services

* Prometheus instrumentation added
* Shared middleware:

  * Tracks active requests
  * Measures latency
  * Updates RPM metric
* `/metrics` endpoint exposed

---

### 2. Prometheus

* Scrapes metrics from all pods
* Stores per-pod RPM values

---

### 3. Prometheus Adapter

* Maps Prometheus metric → Kubernetes custom metric
* Enables HPA to consume `fastapi_http_requests_per_minute`

---

### 4. Horizontal Pod Autoscaler (HPA)

* Scales pods based on RPM
* Supports **scale-to-zero**

---

### 5. Karpenter

* Detects pending GPU pods
* Provisions optimal GPU nodes
* Terminates idle nodes

---

## End-to-End Flow

1. Traffic increases
2. RPM metric increases
3. HPA scales pods
4. Pods become Pending (no GPU capacity)
5. Karpenter launches GPU nodes
6. Pods get scheduled
7. Traffic drops
8. HPA scales down
9. Karpenter removes unused nodes

---

## How to Test

### 1. Deploy Services

```bash
kubectl apply -f eks_manifest/
```

---

### 2. Verify Metrics

* Check Prometheus:

```
fastapi_http_requests_per_minute
```

* Check custom metrics:

```bash
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1"
```

---

### 3. Generate Load

Send requests to:

```
/docker-a/predict
```

Use tools like:

* k6
* hey
* Postman runner

---

### 4. Observe Scaling

```bash
kubectl get hpa -w
kubectl get pods -w
```

---

### 5. Observe Karpenter

```bash
kubectl get nodes -w
```

* Pending pods → new GPU nodes
* Idle nodes → terminated

---

### 6. Test Scale-to-Zero

* Stop traffic
* Watch:

  * Pods → 0
  * GPU nodes → terminated

---




### Demo stack

This `demo` folder contains a simplified copy of your production layout:

- **Docker-A**: simple status API  


All services:

- Are built with **FastAPI**
- Expose `/`, `/health`, and `/metrics`
- Export the **`fastapi_http_requests_per_minute`** metric per service

### Build images

Build each image from inside its own folder (structure similar to your main codebase):

```bash
cd demo/Docker-A && docker build -t demo-docker-a .

```

### Run containers

Example (Docker A on port 8001, B on 8002, etc.):

```bash
docker run --rm -p 8001:8000 demo-docker-a
```

Then you can hit, for example:

- `http://localhost:8001/`, `http://localhost:8001/health`, `http://localhost:8001/metrics`

You can now wire these into **Prometheus + HPA** exactly like the real services, without using any of the client's code or models.

