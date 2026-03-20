# Prometheus Adapter and Project Flow (Docker A on EKS)

This document explains:

- What Prometheus Adapter does in this project
- How to deploy it
- How traffic and metrics flow through Docker A
- How HPA uses custom metrics for autoscaling

## 1) Why Prometheus Adapter is needed

Your HPA (`eks_manifest/hpa.yaml`) scales `demo-model-a` using this custom metric:

- `fastapi_http_requests_per_minute`

Kubernetes HPA cannot directly query Prometheus.  
It needs the Custom Metrics API (`custom.metrics.k8s.io`), and Prometheus Adapter provides that API bridge:

- FastAPI app exports metric at `/metrics`
- Prometheus scrapes the metric
- Prometheus Adapter maps Prometheus query -> Kubernetes custom metric
- HPA reads this custom metric and scales pods

## 2) Adapter manifest added

Use:

- `eks_manifest/prometheus-adapter.yaml`

It includes:

- `Namespace` (`monitoring`)
- `ServiceAccount`, `ClusterRole`, and `ClusterRoleBinding`
- `ConfigMap` with metric rule for `fastapi_http_requests_per_minute`
- `Deployment` and `Service` for `prometheus-adapter`
- `APIService` registration for `v1beta1.custom.metrics.k8s.io`

## 3) Important assumptions

The adapter manifest assumes Prometheus is reachable at:

- `http://prometheus-server.monitoring.svc.cluster.local`

If your Prometheus service name/namespace differs, update:

- `--prometheus-url=...` in `eks_manifest/prometheus-adapter.yaml`

Also make sure Prometheus is scraping Docker A (`/metrics` endpoint), otherwise HPA will not receive values.

## 4) Deploy sequence

Apply manifests:

```bash
kubectl apply -f eks_manifest/deployments-a.yaml
kubectl apply -f eks_manifest/service.yaml
kubectl apply -f eks_manifest/prometheus-adapter.yaml
kubectl apply -f eks_manifest/hpa.yaml
```

## 5) Verification commands

### A. Check app and service

```bash
kubectl get pods -l app=demo-model-a
kubectl get svc demo-service-a
```

### B. Check adapter health

```bash
kubectl get pods -n monitoring -l app=prometheus-adapter
kubectl get apiservice v1beta1.custom.metrics.k8s.io
```

Expected `APIService` status should become `True`/`Available`.

### C. Check exposed custom metric

```bash
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1" | jq .
```

You should see `fastapi_http_requests_per_minute` in the resource list.

### D. Check HPA reads metric

```bash
kubectl describe hpa demo-model-a-hpa
```

Look for:

- metric name: `fastapi_http_requests_per_minute`
- current value changing with traffic

## 6) End-to-end project flow

1. Client request reaches `demo-service-a` (or ingress route if configured).
2. Request is served by pod(s) of deployment `demo-model-a`.
3. Docker A middleware updates Prometheus metrics.
4. `/metrics` endpoint exposes `fastapi_http_requests_per_minute`.
5. Prometheus scrapes this metric from pod/service target.
6. Prometheus Adapter runs the configured query and exposes it via `custom.metrics.k8s.io`.
7. HPA fetches per-pod metric and compares against target (`averageValue: "50"`).
8. If load is high, HPA increases replicas (up to `maxReplicas`); if low, it scales down (not below `minReplicas`).

## 7) Common issues and quick fixes

- **No external endpoint on service**: `ClusterIP` is internal-only. Use ingress or `LoadBalancer` service if public access is required.
- **HPA shows unknown metric**: adapter not running, APIService unavailable, or wrong adapter query.
- **Metric always zero**: no user traffic hitting app routes, or Prometheus not scraping `/metrics`.
- **No pod endpoint in service**: label mismatch between service selector and pod labels.

