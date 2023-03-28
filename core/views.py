# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.contrib.auth import authenticate, login, logout
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseServerError,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .permissions import DocumentAccessPermission

import os, re
import random
import string
import json
import subprocess
import time
import uuid
from traceback import *

from slugify import slugify
from rq import Queue, Connection
from rq.job import Job
from redis import Redis
import redis

from ocr.settings import ARCHIVE_DIR, DEBUG, redis_host, redis_port, redis_db, IP
from ocr import settings

# from ocrize import init_ocr_tesseract
# from prepare_document_for_ocr import process_and_ocr_file, pdf_pages_to_pdf
from .run import perform_ocr_image_files, perform_ocr_container_files, perform_ocr
from .models import Document

from .constants import *

# Global Variables

redis_conn = Redis(host=redis_host, port=redis_port, db=redis_db)
default_queue = Queue(connection=redis_conn, default_timeout=3600)
ocr_pre_queue = Queue("ocr_preprocess", connection=redis_conn, default_timeout=3600)
ocr_queue = Queue("ocr", connection=redis_conn, default_timeout=3600)


# Create your views here.
class Login(TemplateView):
    def get(self, request):
        if request.user.is_authenticated():
            return redirect("/")
        else:
            return render(request, "login.html")

    def post(self, request):
        uname = request.POST["username"]
        pwd = request.POST["password"]
        user = authenticate(username=uname, password=pwd)
        if user is not None:
            login(request, user)
            return HttpResponse("Authentication Successful")
        else:
            return HttpResponseForbidden("Authentication Failed")


class Home(TemplateView):
    def get(self, request):
        if request.user.is_authenticated():
            return render(request, "index.html")
        else:
            # 302 error is a login eror
            return redirect("/login")


class OCR(APIView):
    """Handles uploading of files from the UI.
    """

    # init
    pdf_language = "all"

    authentication_classes = (SessionAuthentication,)

    def post(self, request):
        # Init variable
        pdf_language = "all"

        preprocessing = json.loads(request.POST.get('preprocessing'))
        preprocess = json.loads(request.POST.get('preprocessing'))
        # Get filename
        pdf_splice = preprocessing
        preprocess_options = {
                                "preprocess": preprocessing,
                                "deskew": preprocessing,
                                "rotate": preprocessing,
                                "denoise": preprocessing,
                                "enable_filers": preprocessing,
                                "enable_superres": preprocessing,
                                "enable_superres": preprocessing,
                                "luminfix_flag": True,
                                "pdf_splice": preprocessing,
                                "lang": preprocessing}
        # try:
        #     preprocess = preprocessing
        #     pdf_language = "all"

        #     preprocess_options = {}
        #     for index, key in enumerate(request.POST):
        #         if key in ["lang"]:
        #             continue
        #         preprocess_options[key] = bool(int(request.POST[key]))
        #         print(key, bool(int(request.POST[key])))
        #     print(preprocess_options)
        # except Exception:
        #     return HttpResponseBadRequest("Invalid input data")

        try:
            file = request.FILES["file"]
        except Exception:
            return HttpResponseBadRequest("Document must be uploaded with key `file`")
        input_file_name = file.name
        input_file_extention = input_file_name.split(".")[-1]

        file_name = slugify(input_file_name).split('pdf')[0] + '.' + input_file_extention
        ocr_name = slugify(input_file_name).split('pdf')[0] + "_ocr.pdf"

        # Check if file extention is supported by the Stride OCR
        if input_file_extention.lower() not in CONTAINER_FILES + IMAGE_FILES:
            return HttpResponseBadRequest("Not a suported file format")

        # Create archive directory
        random_string = "".join(random.choice(string.ascii_uppercase) for _ in range(8))
        folder_path = os.path.join(ARCHIVE_DIR, random_string)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        file_path = os.path.join(folder_path, file_name)
        ocr_path = os.path.join(folder_path, ocr_name)
        # Move input file to archive folder
        with open(file_path, "wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        doc = Document(
            folder_name=random_string,
            input_file_name=file_name,
            output_file_name=ocr_name,
            user=request.user,
        )
        doc.save()
        # If container format Pass it to the preprocessing script
        # eg - pdf, tif
        if input_file_extention.lower() in CONTAINER_FILES:
            print(doc.id, file_path, ocr_path, folder_path, pdf_language, preprocess, pdf_splice, preprocess_options)
            ocr_pre_queue.enqueue(
                perform_ocr_container_files,
                args=(
                    doc.id,
                    file_path,
                    ocr_path,
                    folder_path,
                    pdf_language,
                    preprocess,
                    pdf_splice,
                    preprocess_options,
                ), job_id =doc.id
            )

            job = Job.fetch(id='my_id', connection=redis)

        else:
            ocr_queue.enqueue(
                perform_ocr_image_files,
                args=(doc.id, file_path, ocr_path, pdf_language),
            )

        ret_data = {"doc_id": doc.id, "status": doc.status}

        return JsonResponse(ret_data)


    def get(self, request):
        doc_id = request.GET.get("doc_id", "")
        if doc_id == "":
            return HttpResponseBadRequest("No valid doc_id found")

        doc = Document.objects.get(id=doc_id)
        self.check_object_permissions(request, doc)

        if doc.status in ["queued", "processing", "failed"]:
            return_value = {"status": doc.status, "result": {}}
        else:
            secs = (doc.processing_completed - doc.processing_started).seconds
            url = "/file/" + doc.folder_name + "/" + doc.output_file_name
            return_value = {
                "status": doc.status,
                "result": {"time_taken": secs, "output_url": url},
            }
        return JsonResponse(return_value)


class OcrAPI(APIView):
    """Handles OCR API requests
    """

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, DocumentAccessPermission)

    def post(self, request):

        # Init variable
        pdf_language = "all"

        # Get filename
        try:
            preprocess = bool(int(request.POST.get("preprocess", "0")))
            pdf_splice = bool(int(request.POST.get("pdf_splice", "0")))
            pdf_language = request.POST.get("lang", "all")

            preprocess_options = {}
            for index, key in enumerate(request.POST):
                if key in ["lang"]:
                    continue
                preprocess_options[key] = bool(int(request.POST[key]))
                print (key,bool(int(request.POST[key])) )
            print (preprocess_options)
        except Exception:

            return HttpResponseBadRequest("Invalid input data")
        try:
            file = request.FILES["file"]
        except Exception:
            return HttpResponseBadRequest("Document must be uploaded with key `file`")
        input_file_name = file.name
        input_file_extention = input_file_name.split(".")[-1]

        file_name = slugify(input_file_name).split('pdf')[0] + '.' + input_file_extention
        ocr_name = slugify(input_file_name).split('pdf')[0] + "_ocr.pdf"

        # Check if file extention is supported by the Stride OCR
        if input_file_extention.lower() not in CONTAINER_FILES + IMAGE_FILES:
            return HttpResponseBadRequest("Not a suported file format")

        # Create archive directory
        random_string = "".join(random.choice(string.ascii_uppercase) for _ in range(8))
        folder_path = os.path.join(ARCHIVE_DIR, random_string)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        file_path = os.path.join(folder_path, file_name)
        ocr_path = os.path.join(folder_path, ocr_name)
        # Move input file to archive folder
        with open(file_path, "wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        doc = Document(
            folder_name=random_string,
            input_file_name=file_name,
            output_file_name=ocr_name,
            user=request.user,
        )
        doc.save()
        # If container format Pass it to the preprocessing script
        # eg - pdf, tif
        if input_file_extention.lower() in CONTAINER_FILES:
            """job = Job.create(
                perform_ocr_container_files,
                args=(
                    doc.id,
                    file_path,
                    ocr_path,
                    folder_path,
                    pdf_language,
                    preprocess,
                    pdf_splice,
                    preprocess_options,
                ),
            )"""
            

            job = ocr_pre_queue.enqueue(
                perform_ocr_container_files,
                args=(
                    doc.id,
                    file_path,
                    ocr_path,
                    folder_path,
                    pdf_language,
                    preprocess,
                    pdf_splice,
                    preprocess_options,
                ),job_id=str(doc.id)
            )
            ret_data = {"doc_id": doc.id, "status": doc.status, "job":"", "folder":folder_path, 
                        "file_name":input_file_name}
            return JsonResponse(ret_data)
        
        else:
            job = ocr_queue.enqueue(
                perform_ocr_image_files,
                args=(doc.id, file_path, ocr_path, pdf_language),
            )
            ret_data = {"doc_id": doc.id, "status": doc.status}
            return JsonResponse(ret_data)

    def get(self, request):
        
        # Init variable
        pdf_language = "all"

        # Get filename
        try:
            preprocess = bool(int(request.data.get("preprocess", "0")))

            pdf_splice = bool(int(request.data.get("deskew", "0")))
            pdf_splice = bool(int(request.data.get("rotate", "0")))
            pdf_splice = bool(int(request.data.get("denoise", "0")))
            pdf_splice = bool(int(request.data.get("enable_filers", "0")))
            pdf_splice = bool(int(request.data.get("enable_superres", "0")))

            pdf_splice = bool(int(request.data.get("pdf_splice", "0")))
            pdf_language = request.data.get("lang", "all")

            preprocess_options = {}
            for index, key in enumerate(request.GET):
                if key in ["lang"]:
                    continue
                preprocess_options[key] = bool(int(request.GET[key]))
                print (key,bool(int(request.GET[key])) )
        except Exception:

            return HttpResponseBadRequest("Invalid input data")
        input_file_name = request.data.get("file_name","")
        input_file_extention = input_file_name.split(".")[-1]

        file_name = slugify(input_file_name).split('pdf')[0] + '.' + input_file_extention
        ocr_name = slugify(input_file_name).split('pdf')[0] + "_ocr.pdf"
        
        # Create archive directory
        folder_path = request.data.get("folder","")
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        file_path = os.path.join(folder_path, file_name)
        ocr_path = os.path.join(folder_path, ocr_name)
        doc_id = request.GET.get("doc_id", "")
        if doc_id == "":
            return HttpResponseBadRequest()
        doc = Document.objects.get(id=doc_id)
        self.check_object_permissions(request, doc)
        if doc.status in ["queued", "processing", "failed","ocr_process"]:
            return_value = {"status": doc.status, "result": {}}
        elif doc.status == "ocr":
            with Connection():
                job = Job().fetch(doc_id, connection=redis_conn)
            path_to_pdf_pages = job.result
            doc.status="ocr_process"
            doc.save()
            ocr_queue.enqueue(perform_ocr, args = ( path_to_pdf_pages,
                        doc_id,
                        ocr_path,
                        folder_path,
                        pdf_language,
                        pdf_splice,))
            return_value = {"status": doc.status, "result": {}}
        else:
            
            secs = (doc.processing_completed - doc.processing_started).seconds
            url = "/file/" + doc.folder_name + "/" + doc.output_file_name
            print(url)
            
            return_value = {
                "status": doc.status,
                "result": {"time_taken": secs, "output_url": url},
            }
            
        return JsonResponse(return_value)


class Poll(TemplateView):

    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated, DocumentAccessPermission)

    def get(self, request):
        doc_id = request.GET.get("doc_id", "")
        if doc_id == "":
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        doc = Document.objects.get(id=doc_id)
        self.check_object_permissions(request, doc)
        if doc.status in ["queued", "processing", "failed"]:
            return_value = {"status": doc.status, "result": {}}
        elif doc.status == "ocr":
            job = request.GET.get("job","")
            path_to_pdf_pages = job.return_value
            perform_ocr( path_to_pdf_pages,
                        doc_id,
                        request.GET.get("ocr_path",""),
                        request.GET.get("folder_path",""),
                        request.GET.get("ocr_language",""),
                        request.GET.get("pdf_splice",""))
            if(doc.status=="failed"):
                return_value = {"status": doc.status, "result": {}}
            else:
                secs = (doc.processing_completed - doc.processing_started).seconds
                url = "/file/" + doc.folder_name + "/" + doc.output_file_name
                return_value = {
                    "status": doc.status,
                    "result": {"time_taken": secs, "output_url": url},
                }
        else:
            secs = (doc.processing_completed - doc.processing_started).seconds
            url = "/file/" + doc.folder_name + "/" + doc.output_file_name
            return_value = {
                "status": doc.status,
                "result": {"time_taken": secs, "output_url": url},
            }
        return JsonResponse(return_value)


class Logout(TemplateView):
    def get(self, request):
        logout(request)
        return redirect("/login")


class CheckLogin(View):
    def get(self, request):
        if request.user.is_authenticated:
            return JsonResponse({"user_authenticated": True})
        else:
            return JsonResponse({"user_authenticated": False})


class RetrieveFiles(APIView):
    authentication_classes = (SessionAuthentication, TokenAuthentication)
    permission_classes = (IsAuthenticated, DocumentAccessPermission)

    def get(self, request):
        response = HttpResponse()
        path = request.path.split("/")[2:]
        new_path = "/".join(path)
        file_name = path[-1]
        folder_name = path[-2]
        doc = Document.objects.get(folder_name=folder_name)
        self.check_object_permissions(request, doc)
        response["Content-Disposition"] = "attachment; filename={0}".format(file_name)
        if settings.DEBUG:
            file_path = os.path.join(settings.ARCHIVE_DIR, *path)
            response.content = open(file_path, "rb").read()
        else:
            response["X-Accel-Redirect"] = "/protected/" + new_path
        return response
