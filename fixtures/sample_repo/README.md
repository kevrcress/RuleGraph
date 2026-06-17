# fixtures/sample_repo — Synthetic Test Data

This is synthetic sample data, not production code. It exists solely to provide
a cheap, repeatable way to exercise RuleGraph's ingest pipeline, conflict
detection, and terminology normalization without cloning a real repository.

## What's here

| File | Service | Planted signal |
|------|---------|----------------|
| `payment/validators.py` | payment-service | CVV check, fraud threshold |
| `payment/refund_processor.py` | payment-service | **30-day refund window** |
| `orders/workflow.py` | orders-service | Order approval, 24-hour cancellation |
| `orders/discount.py` | orders-service | Promo code stacking, **45-day price-adjustment window** |
| `inventory/monitor.py` | inventory-service | Reorder threshold, backorder display |

The **30-day vs 45-day window conflict** is deliberate. Both files reference the
same domain concept (customer refund/adjustment window) with different values,
which should reliably trigger a conflict detection hit in RuleGraph.

## Ingest sequence

Run each directory separately with a distinct `--source` label so RuleGraph
creates cross-service graph edges:

```bash
python scripts/ingest_repo.py --path fixtures/sample_repo/payment   --source payment-service   --login admin@test.com Test1234!
python scripts/ingest_repo.py --path fixtures/sample_repo/orders     --source orders-service    --login admin@test.com Test1234!
python scripts/ingest_repo.py --path fixtures/sample_repo/inventory  --source inventory-service --login admin@test.com Test1234!
```

After all three runs, open the Conflicts page in the UI — you should see at
least one conflict between `payment-service` and `orders-service` around the
refund/adjustment window.
