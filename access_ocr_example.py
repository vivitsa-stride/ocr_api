# This code snippet give you an easy way to interface with
# Stride's OCR engine via code

import requests
import logging


# Dev Logger
logger = logging.getLogger("__name__")
#   Logging level
logger.setLevel(logging.DEBUG)


#   Set logger formatting
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")


#   Log file handler
fine_handler = logging.FileHandler("preprocessing_and_OCR_report.log")
fine_handler.setFormatter(formatter)


#   STDout Handler
st_hndle = logging.StreamHandler()
st_hndle.setFormatter(formatter)

#   Set Handlers
logger.addHandler(fine_handler)
#   Uncomment for stdout
logger.addHandler(st_hndle)


def ocrize_pdf(file_path):
    """ Runs Stride OCR on the pdf in case of scanned documents """
    LOGGER.info("OCR started for file : %s" % file_path)

    url = OCR_SERVER + "/api/ocr/"
    files = {"file": open(file_path, "rb")}
    headers = {"Authorization": "Token " + OCR_TOKEN}

    response = requests.post(url, files=files, headers=headers, verify=False)
    if not response.ok:
        LOGGER.warn("OCR failed for file : %s" % file_path)
        return None

    call_ocr_json = json.loads(response.text)

    url = OCR_SERVER + "/api/ocr/?doc_id=" + str(call_ocr_json["doc_id"])

    LOGGER.info("Polling for file : %s" % file_path)
    fail = False
    for _ in range(150):
        response_ocr_path = requests.get(url, headers=headers, verify=False)
        if not response_ocr_path.ok:
            fail = True
            break
        response_json = json.loads(response_ocr_path.text)
        if response_json["status"] == "failed":
            fail = True
            break
        elif response_json["status"] == "completed":
            break
        time.sleep(10)

    if fail:
        LOGGER.warn("OCR failed for file : %s" % file_path)
        return None

    ocr_pdf_url = response_json["result"]["output_url"]
    ocr_pdf_file_name = ocr_pdf_url.split("/")[-1]

    folder_path = os.path.dirname(file_path)
    ocr_pdf_path = os.path.join(folder_path, ocr_pdf_file_name)

    response = requests.get(OCR_SERVER + ocr_pdf_url, headers=headers, verify=False)

    with open(ocr_pdf_path, "wb") as ocr:
        ocr.write(response.content)
    LOGGER.warn("OCR completed successfully for file : %s" % file_path)
    return ocr_pdf_path
