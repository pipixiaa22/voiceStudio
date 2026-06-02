"""Redis-backed video job worker.

Usage:
    uv run python -m server.workers.video_worker

Environment variables:
    REDIS_URL               – required for queue mode
    REDIS_KEY_PREFIX        – key prefix (default: video-script)
    VIDEO_WORKER_CONCURRENCY – max concurrent jobs (default: 1)
"""

import os
import sys
import threading
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def run_worker():
    from server.services.redis_client import get_redis, redis_key
    from server.services.video_job import get_job, _process_job

    r = get_redis()
    if r is None:
        logger.error('Redis not available. Set REDIS_URL to use queue mode.')
        sys.exit(1)

    concurrency = int(os.environ.get('VIDEO_WORKER_CONCURRENCY', '1'))
    queue_key = redis_key('queue', 'video_jobs')
    active_key = redis_key('queue', 'video_jobs', 'active')

    logger.info('Video worker started (concurrency=%d, queue=%s)', concurrency, queue_key)

    # Import Flask app for app context
    from server.app import create_app
    app = create_app()

    sem = threading.Semaphore(concurrency)
    active_count = 0

    def process_one(job_id: str):
        nonlocal active_count
        try:
            with app.app_context():
                job = get_job(job_id)
                if not job:
                    logger.warning('Job %s not found, skipping', job_id)
                    return
                logger.info('Processing job %s (%s)', job_id, job.title)
                r.hset(active_key, job_id, str(time.time()))
                _process_job(job_id, app)
        except Exception:
            logger.exception('Worker error for job %s', job_id)
        finally:
            r.hdel(active_key, job_id)
            sem.release()
            active_count -= 1

    while True:
        sem.acquire()
        active_count += 1
        try:
            # Block up to 5 seconds for a new job
            result = r.brpop(queue_key, timeout=5)
            if result is None:
                sem.release()
                active_count -= 1
                continue
            job_id = result[1].decode('utf-8') if isinstance(result[1], bytes) else result[1]
            t = threading.Thread(target=process_one, args=(job_id,), daemon=True)
            t.start()
        except Exception:
            sem.release()
            active_count -= 1
            logger.exception('Worker loop error')
            time.sleep(1)


if __name__ == '__main__':
    run_worker()
