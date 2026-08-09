# JSONL example

```bash
evalrepro snapshot jsonl examples/jsonl/baseline.jsonl --name quickstart -o /tmp/base.json
evalrepro snapshot jsonl examples/jsonl/candidate-order-drift.jsonl --name quickstart -o /tmp/order.json
evalrepro snapshot jsonl examples/jsonl/candidate-semantic-drift.jsonl --name quickstart -o /tmp/semantic.json

evalrepro compare /tmp/base.json /tmp/order.json      # order_drift
evalrepro compare /tmp/base.json /tmp/semantic.json   # semantic_drift
```
