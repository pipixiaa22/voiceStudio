import json
import uuid
from server.models import db, VideoJob


def create_job(title: str, request: dict) -> VideoJob:
    job = VideoJob(
        job_id=f'video-job-{uuid.uuid4().hex[:12]}',
        title=title,
        status='queued',
        request_json=json.dumps(request, ensure_ascii=False),
    )
    db.session.add(job)
    db.session.commit()
    return job


def get_job(job_id: str) -> VideoJob | None:
    return VideoJob.query.filter_by(job_id=job_id).first()


def update_job_progress(job_id: str, progress: float, stage: str, message: str = ''):
    job = get_job(job_id)
    if not job:
        return
    job.status = stage if stage in ('planning', 'synthesizing_voice', 'mixing_audio', 'rendering', 'rendering_video', 'packaging') else job.status
    job.progress = progress
    job.stage = stage
    job.message = message
    db.session.commit()


def update_job_completed(job_id: str, output_path: str, manifest_json: str = '{}'):
    job = get_job(job_id)
    if not job:
        return
    job.status = 'completed'
    job.progress = 1.0
    job.output_path = output_path
    job.manifest_json = manifest_json
    job.message = '视频生成完成'
    db.session.commit()


def update_job_failed(job_id: str, error_message: str):
    job = get_job(job_id)
    if not job:
        return
    job.status = 'failed'
    job.error_message = error_message
    job.message = f'生成失败: {error_message}'
    db.session.commit()


def list_jobs(limit: int = 20) -> list[VideoJob]:
    return VideoJob.query.order_by(VideoJob.created_at.desc()).limit(limit).all()
