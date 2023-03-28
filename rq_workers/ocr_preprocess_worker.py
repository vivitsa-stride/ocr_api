import sys
import os
import django
import platform
import logging
import traceback
from darwin_worker import DarwinWorker

from redis import Redis
from rq import Connection, Worker
#from rq.handlers import move_to_failed_queue

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CUR_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ocr.settings")
django.setup()

# Preload libraries
from ocr import settings

redis_conn = Redis(host=settings.redis_host, port=settings.redis_port,
                   db=settings.redis_db)
LOGGER = logging.getLogger('ocr')


def my_handler(job, exc_type, exc_value, traceback_obj):
    """Custom error handler for cluster queue

    Args:
        job (:obj:`rq.job.Job`): RQ Job object which failed
        exc_type (:obj:`Exception`): Exception type
        exc_value (:obj:`string`): Exception in string
        traceback_obj (:obj:`traceback.TracebackException`): traceback object

    Returns:
        bool: Return True so that exception handlers will be chained
    """
    traceback_message = "".join(traceback.format_tb(traceback_obj))
    LOGGER.error("%s failed for args %s unexpectedly with error %s-%s"
                 % (job.func_name, str(job.args), exc_type, traceback_message))
    # if job.func_name == 'extraction.tasks.unstructured.extract_datapoints' or\
    #         job.func_name == 'extraction.tasks.structured.extract_datapoints':
    #     process_id, set_id = job.args
    #     extraction_set = ExtractionDocumentSet.objects.get(id=set_id)
    #     extraction_set.status = "failed"
    #     extraction_set.save()
    # elif job.func_name == 'extraction.tasks.unstructured.build_model' or\
    #         job.func_name == 'extraction.tasks.structured.build_sdfe_model':
    #     process_id, model_id, profile_id = job.args
    #     model = Model.objects.get(id=model_id)
    #     model.status = 'failed'
    #     model.save()

    # return True to continue to the next exceptoion handler
    return True


# Provide queue names to listen to as arguments to this script,
# similar to rq worker
with Connection(redis_conn):
    qs = ['ocr_preprocess']

    if platform.system() == 'Darwin':
        w = DarwinWorker(
            qs, exception_handlers=[my_handler])
    else:
        w = Worker(qs, exception_handlers=[my_handler])
    w.work()
