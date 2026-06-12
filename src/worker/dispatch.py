import logging
from queue import Queue
from threading import Event

from src.db import construct_engine
from src.services.ingestor import ingest
from src.services.llm_service import query

from .job_type import JobType


class Worker:
	def __init__(self, engine):
		self.engine = engine
		self.jobs: Queue[tuple[JobType, int]] = Queue()
		self.stop_signal = Event()

	def submit(self, job_type: JobType, payload: int):
		self.jobs.put((job_type, payload))

	def work(self):
		while not self.stop_signal.is_set():
			job_type, payload = self.jobs.get()
			
			try:
				if job_type == JobType.INGEST_DOCUMENT:
					ingest(payload, self.engine)
				elif job_type == JobType.QUERY_RAG:
					query(payload, self.engine)
				else:
					logging.warning(f"Unsupported job type '{job_type}'")
			
			except Exception:
				logging.exception(f"Job '{job_type}' failed")
			finally:
				self.jobs.task_done()


_worker: Worker | None = None

def set_worker(worker: Worker):
	global _worker
	_worker = worker


def enqueue_document(document_id: int):
	if _worker is not None:
		_worker.submit(JobType.INGEST_DOCUMENT, document_id)
		return
	ingest(document_id, construct_engine()) # fallback

def enqueue_query(job_id: int):
	if _worker is not None:
		_worker.submit(JobType.QUERY_RAG, job_id)
		return
	query(job_id, construct_engine()) # fallback