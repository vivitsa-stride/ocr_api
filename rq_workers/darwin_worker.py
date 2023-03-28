from rq.worker import Worker
from rq.worker import WorkerStatus, JobStatus
from threading import Thread
from datetime import datetime


class DarwinWorker(Worker):
    """Custom RQ worker which does not use os.fork
Solves worker crash with macOS high sierra and upwards when models
are pre loaded.

    Args:
        Worker ([rq.worker.Worker]): Sub classes rq worker implementation
    """

    def execute_job(self, job, queue):
        """Spawns a work horse to perform the actual work and passes it a job.
        The worker will wait for the work horse and make sure it executes
        within the given timeout bounds, or will end the work horse with
        SIGALRM.
        """
        self.set_state(WorkerStatus.BUSY)
        try:
            self.perform_job(job, queue)
        except Exception:
            self.handle_unexpected_failure(job)
        self.set_state(WorkerStatus.IDLE)

    def handle_unexpected_failure(self, job):
        job_status = job.get_status()
        if job_status is None:  # Job completed and its ttl has expired
            return
        if job_status not in [JobStatus.FINISHED, JobStatus.FAILED]:

            if not job.ended_at:
                job.ended_at = datetime.utcnow()

            self.handle_job_failure(job=job)

            # Unhandled failure: move the job to the failed queue
            self.log.warning((
                'Moving job to {0!r} queue '
                '(work-horse terminated unexpectedly; waitpid returned {1})'
            ).format(self.failed_queue.name, ret_val))
            self.failed_queue.quarantine(
                job,
                exc_info=(
                    "Work-horse process was terminated unexpectedly "
                    "(waitpid returned {0})"
                ).format(ret_val)
            )
