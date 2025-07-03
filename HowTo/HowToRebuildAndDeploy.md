# EventTrader – Quick Rebuild & Deploy

## 🔑 One-liner per component  
Run **on minisforum (192.168.40.73)** from `~/EventMarketDB`

| Component    | Command                               |
|--------------|---------------------------------------|
| event-trader | `./scripts/deploy.sh event-trader`    |
| xbrl-worker  | `./scripts/deploy.sh xbrl-worker`     |

`deploy.sh` performs **git pull ➜ build & push ➜ rollout**.

---

## 🛠 Manual fallback

```bash
# ➊ update code
cd ~/EventMarketDB && git pull

# ➋ build + push (example: event-trader)
docker build -f Dockerfile.event -t faisalanjum/event-trader:latest .
docker push  faisalanjum/event-trader:latest

# ➌ roll out (namespace = processing)
kubectl rollout restart deployment/event-trader        -n processing
kubectl rollout restart deployment/xbrl-worker-heavy   -n processing
kubectl rollout restart deployment/xbrl-worker-medium  -n processing
kubectl rollout restart deployment/xbrl-worker-light   -n processing
```                                                            # ➊ close code-block

## 🛠 Helper scripts

| Script                       | Action               |

|------------------------------|-----------------------|

| `scripts/build_push.sh <c>`  | Build + push image    |

| `scripts/rollout.sh   <c>`   | Restart deployments   |

| `scripts/deploy.sh   <c>`    | **All** of the above  |
scripts/deploy.sh <c>	All of the above

## 🚧 Troubleshooting

| Issue | Quick check / fix |

|-------|-------------------|

| New image not picked up | `kubectl describe pod <pod> | grep -i image` |

| Build fails (lib missing) | add OS pkg in Dockerfile (`apt-get install …`) |

| Pod CrashLoopBackOff | `kubectl logs <pod>` |

| Push denied | `docker login` → re-run push |
