# EventTrader – Quick Rebuild & Deploy

## 🔑 One-liner per component  
Run **on minisforum (192.168.40.73)** from `~/EventMarketDB`

| Component    | Command                           |
|--------------|-----------------------------------|
| event-trader | `./scripts/deploy.sh event-trader`|
| xbrl-worker  | `./scripts/deploy.sh xbrl-worker` |

`deploy.sh` does **git pull ➜ build + push ➜ rollout**.

---

## 🛠 Manual fallback

```bash
cd ~/EventMarketDB && git pull         # update code

# build + push (example)
docker build -f Dockerfile.event -t faisalanjum/event-trader:latest .
docker push  faisalanjum/event-trader:latest

# roll out (namespace = processing)
kubectl rollout restart deployment/event-trader      -n processing
kubectl rollout restart deployment/xbrl-worker-heavy -n processing
kubectl rollout restart deployment/xbrl-worker-medium -n processing
kubectl rollout restart deployment/xbrl-worker-light  -n processing

