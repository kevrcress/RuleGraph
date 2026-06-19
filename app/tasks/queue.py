"""Shared arq queue configuration.

Holds constants that BOTH the web process (enqueue sites) and the worker process
(``WorkerSettings``) need. Kept separate from ``app.tasks.worker`` so the FastAPI
routers don't import the worker entrypoint — importing ``worker`` executes its module
body (RedisSettings, cron registration, job imports), which the web layer must not do
just to read a queue name. See PR-review IV-004.
"""

# The worker consumes from this queue and every enqueue site must target it via
# ``_queue_name``. Without this, ``enqueue_job`` defaults to arq's ``arq:queue`` and
# jobs are never consumed by this worker.
INGEST_QUEUE_NAME = "rulegraph:tasks"
