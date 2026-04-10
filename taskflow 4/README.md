# ⚡ TaskFlow — Agile Task Management

A full-stack agile task management web app built with Flask, containerised with Docker, and deployed with Kubernetes.

---

## 🚀 Quick Start (Local Development)

```bash
git clone https://github.com/YOUR_USERNAME/taskflow.git
cd taskflow
pip install -r requirements.txt
python app.py
# → http://localhost:5000
# → Demo: demo@taskflow.com / demo123
```

---

## 🐳 Docker

### Single container
```bash
docker build -t taskflow:latest .
docker run -d -p 5000:5000 -v taskflow-data:/app/instance \
  -e SECRET_KEY="your-secret" --name taskflow taskflow:latest
```

### Docker Compose (app + nginx)
```bash
docker compose up --build        # build and start
docker compose up -d             # background
docker compose logs -f taskflow  # follow logs
docker compose down              # stop
docker compose down -v           # stop + wipe DB
```
Open http://localhost (nginx on port 80)

---

## ☸️ Kubernetes

```bash
# 1. Update image name in k8s/03-deployment.yaml
# 2. Create secret
kubectl create secret generic taskflow-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" -n taskflow

# 3. Deploy everything
kubectl apply -f k8s/

# 4. Watch pods
kubectl get pods -n taskflow -w
```

### Useful commands
```bash
kubectl get all -n taskflow
kubectl logs -f deployment/taskflow-deployment -n taskflow
kubectl exec -it deployment/taskflow-deployment -n taskflow -- /bin/sh
kubectl rollout undo deployment/taskflow-deployment -n taskflow
kubectl delete namespace taskflow
```

---

## 🔄 CI/CD Pipeline

Push to `main` triggers:
1. **Test** — pytest runs all tests
2. **Build** — Docker image built & pushed to GHCR
3. **Deploy** — kubectl rolls out new image to K8s

### Required GitHub Secret
`Settings → Secrets → KUBECONFIG` = `cat ~/.kube/config | base64`

---

## 📁 Structure

```
taskflow/
├── app.py                    # Flask application
├── tests.py                  # Pytest suite
├── requirements.txt
├── Dockerfile                # Multi-stage build
├── docker-compose.yml        # Local dev stack
├── nginx.conf                # Reverse proxy
├── .github/workflows/
│   └── ci-cd.yml             # GitHub Actions pipeline
├── k8s/
│   ├── 00-namespace.yaml
│   ├── 01-config.yaml        # ConfigMap + Secret
│   ├── 02-pvc.yaml           # Persistent storage
│   ├── 03-deployment.yaml    # App pods
│   ├── 04-service.yaml       # Internal service
│   ├── 05-ingress.yaml       # External routing
│   └── 06-hpa.yaml           # Auto-scaling
└── templates/
```
