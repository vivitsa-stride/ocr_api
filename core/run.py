"""Utilities which do the heavy lifting. Meant to be executed
via RQ jobs.
"""
from datetime import datetime
import time
import logging
import os
import shutil

from rq import Queue
from rq.job import cancel_job
from redis import Redis

from .models import Document
from .constants import PATH_TO_TEMP_PDFS_OCRized, PDF_MODIFIER
from ocr.settings import redis_host, redis_port, redis_db

from .ocrize import init_ocr_tesseract
from .prepare_document_for_ocr import process_and_ocr_file, pdf_pages_to_pdf, detect_language
from django.utils.timezone import utc

redis_conn = Redis(host=redis_host, port=redis_port, db=redis_db)
ocr_queue = Queue("ocr", connection=redis_conn, default_timeout=3600)

logger = logging.getLogger("ocr")

from IPython import embed

def perform_ocr_image_files(
    doc_id,
    file_path,
    ocr_path,
    preprocess=False,
    preprocess_options={},
    ocr_language="all",
):
    """OCRize image files

    Args:
        doc_id (int): primary key of the Document object
        file_path (str): file path of the input file to OCRize
        ocr_path (str): file path of the OCRized files
        preprocess (bool, optional): Defaults to False. Enable pre-processing
        preprocess_options (dict, optional): Defaults to {}. Set
            pre-processing flags
    """

    doc = Document.objects.get(id=doc_id)
    doc.processing_started = datetime.utcnow().replace(tzinfo=utc)
    doc.status = "processing"
    doc.save()
    is_image_input = True

    timeout = 20

    success, err = init_ocr_tesseract(file_path, ocr_path, timeout,  ocr_language, is_image_input)
    
    if not success:
        doc.status = "failed"
    else:
        doc.status = "completed"
    doc.processing_completed = datetime.utcnow().replace(tzinfo=utc)
    doc.save()


def perform_ocr_container_files(
    doc_id,
    file_path,
    ocr_path,
    folder_path,
    ocr_language="all",
    preprocess=False,
    pdf_splice=False,
    preprocess_options={},
):
    """OCRize container files like PDF to TIFF

    Args:
        doc_id (int): primary key of the Document object
        file_path (str): file path of the input file to OCRize
        ocr_path (str): file path of the OCRized files
        folder_path (str): folder to create temporary files
        preprocess (bool, optional): Defaults to False. Enable pre-processing
        preprocess_options (dict, optional): Defaults to {}. Set
            pre-processing flags
    """
    doc = Document.objects.get(id=doc_id)
    doc.processing_started = datetime.utcnow().replace(tzinfo=utc)
    doc.status = "processing"
    doc.save()

    is_image_input = False

    # Split the files into its parts
    if not preprocess:
        logger.info("ocring started for for doc %d" % doc_id)
        logger.info("document lang %s" % ocr_language)
        _, path_to_pdf_pages = process_and_ocr_file(
            file_path,
            folder_path,
            is_preprocess_enable_flag=False,
            deskew_flag=False,
            rotate_flag=False,
            denoise_flag=False,
            enable_filers_flag=False,
            enable_superres=False,
            is_pdf_splice_enabled=pdf_splice,
            is_ocr_enabled=False,
            ocr_ip="0.0.0.0",
            ocr_language=ocr_language,
        )

    else:
        logger.info("pre-processing started for for doc %d" % doc_id)
        _, path_to_pdf_pages = process_and_ocr_file(
            file_path,
            folder_path,
            is_preprocess_enable_flag=True,
            deskew_flag=preprocess_options.get("deskew", True),
            rotate_flag=preprocess_options.get("rotate", True),
            denoise_flag=preprocess_options.get("denoise", True),
            enable_filers_flag=preprocess_options.get("enable_filers", True),
            enable_superres=preprocess_options.get("enable_superres", True),
            luminfix_flag=preprocess_options.get("luminfix_flag", True),
            is_pdf_splice_enabled=pdf_splice,
            is_ocr_enabled=False,
            ocr_ip="0.0.0.0",
            ocr_language=ocr_language,
        )
        logger.info("pre-processing complete for for doc %d" % doc_id)
    doc.status = "ocr"
    doc.save()
    return path_to_pdf_pages

def perform_ocr(
    path_to_pdf_pages,
    doc_id,
    ocr_path,
    folder_path,
    ocr_language="all",
    pdf_splice=False,   
):
    logger.error(path_to_pdf_pages)
    doc = Document.objects.get(id=int(doc_id))
    if pdf_splice:
        timeout = 15
    else:
        timeout = 1500

    if ocr_language=="all":
        ocr_language = detect_language(path_to_pdf_pages)[0]
    logger.info(f"detected language: {ocr_language}")
    # Create Directory Structre for processing
    ocrized_pdfs_folder = os.path.join(folder_path, PATH_TO_TEMP_PDFS_OCRized)
    if not os.path.exists(ocrized_pdfs_folder):
        os.makedirs(ocrized_pdfs_folder)
    all_jobs = []
    try:
        for image_file_path in path_to_pdf_pages:
            image_file_name = os.path.basename(image_file_path)

            output_filename = image_file_name[:-4] + PDF_MODIFIER
            path_to_output_pdf = os.path.join(ocrized_pdfs_folder, output_filename)
            logger.error(path_to_output_pdf)
            logger.error(output_filename)
        init_ocr_tesseract(image_file_path, path_to_output_pdf, timeout, ocr_language, False)

        logger.info("Waiting for OCR jobs to complete for doc %s" % doc_id)
        while not all(map(lambda j: j.get_status() in ["finished", "failed"], all_jobs)):
            time.sleep(3)
            logger.debug("Waiting for OCR jobs to complete for doc %s" % doc_id)
        # Once jobs completed
        if any(map(lambda j: j.get_status() == "failed", all_jobs)):
            success = False
        else:
            if not pdf_splice:
                # copy temp folder to OCR
                shutil.copy(path_to_output_pdf, ocr_path)
                success = os.path.exists(ocr_path)
            else:
                # stitch back individual files

                # embed()
                logger.debug("Starting PDF merge %s" % doc_id)
                success = pdf_pages_to_pdf(ocr_path, ocrized_pdfs_folder)


        logger.info("Ocrization is %s doc %s" % (success, doc_id))

        if not success:
            doc.status = "failed"
        else:
            doc.status = "completed"
        
        doc.processing_completed = datetime.utcnow().replace(tzinfo=utc)
        doc.save()
        logger.info("-----------------------------------------------------")
    except Exception as e:
        doc.status = "failed"
        doc.save()
        logger.info("Ocrization has failed for doc %s" % (doc_id))
        logger.error(e)
