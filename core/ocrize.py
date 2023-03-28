import os
import logging
import subprocess
from traceback import format_exc
from threading import Timer
import signal
from .constants import *

logger = logging.getLogger("ocr")


def ocrize_file_tesseract(
    file_path, output_path, ip_2_ocr="0.0.0.0", ocr_language="all"
):
    """
        Description :   This function calls the tesseract OCR engine to OCRize a file.

                        String path to the Input file (tif)
                        String path for the output file (including filename sans .pdf extension)
                        String ip address for ocr. 0.0.0.0 calls tesseract on the system (Defaut).
                        OCR language mode. 


        Input       :   path to PDF file (String)

        Return      :   path to OCRized PDF file (String)

        Author      :   Titus@stride
    """ 

    

    # Makes tesseract OCR  to run locally

    if ip_2_ocr == "0.0.0.0":
        # Format the input and output filenames for OCR
        path_to_ocr_input_file = '"{}"'.format(file_path)
        path_to_ocrzd_file = '"{}"'.format(output_path)
        TESS_DATA_DIR = '"{}"'.format(TESS_DATA_DIR)

        # Tesseract command calls
        command_to_call = TESS_CMD_HEAD
        command_to_call = (
            command_to_call + path_to_ocr_input_file + " " + path_to_ocrzd_file
        )

        if ocr_language == "all":
            
            command_to_call = command_to_call + TESS_PARMS

        elif ocr_language in OCR_SUPPORTED_LANGS:
            command_to_call = (
                command_to_call
                + "--tessdata-dir  "
                + TESS_DATA_DIR
                + " -l "
                + ocr_language
                + TESS_PARMS
            )
        else:

            logger.error(
                "OCR does not support the following langauage :%s", ocr_language
            )
            logger.error("Dfualting to OG ocr%s", ocr_language)
            command_to_call = command_to_call + TESS_PARMS

        command_to_call = command_to_call + " 2>/dev/null"

        # Call the command
        os.system(command_to_call)

    # Makes tesseract OCR  to run on the provided server. Auth token may need to be changed.
    else:

        # url = 'http://35.240.152.215/hocr/'
        url = "http://" + ip_2_ocr + "/hocr/"
        files = {"pdf": open(file_path, "rb")}
        headers = {"Authorization": "Token 56ba1558c96d267dff2e6e4c178fc8a92c30489f"}

        response = requests.request(
            "POST", url, files=files, headers=headers, verify=False
        )
        if not response.ok:
            print(response.content)
            print(response)
            return ""

        call_ocr_json = json.loads(response.text)
        url = "http://" + ip_2_ocr + "/hocr?jobid="
        url = (
            url
            + call_ocr_json["jobid"]
            + "&url="
            + call_ocr_json["random_string"]
            + "&name="
            + call_ocr_json["ocr_name"]
        )

        headers = {"Authorization": "Token 56ba1558c96d267dff2e6e4c178fc8a92c30489f"}

        for i in range(100):
            response_ocr_path = requests.request(
                "GET", url, headers=headers, verify=False
            )
            response_json = json.loads(response_ocr_path.text)
            print("Waiting for OCRization to complete.", json.dumps(response_json))
            print(response_json)
            if response_json["status"] not in ["queued", "started"]:
                break
            time.sleep(15)

        if not response_ocr_path.ok:
            print(response_ocr_path)
            return ""

        ocr_pdf_url = response_json["result"]
        response = requests.get(ocr_pdf_url)
        output_path = output_path + ".pdf"
        print(output_path)
        try:
            with open(output_path, "wb") as ocr:
                ocr.write(response.content)
        except:
            print("Failed to save OCRized file from the server to " + output_path)

    return output_path


def ocr_single_file(
    path_to_ocr_input_file, path_to_ocrzd_file, ocr_ip, ocr_language="all"
):

    """ helper function to ocr a single file

    Args:
        path_to_ocrzd_file (str): abs path to the output file
        ocr_ip                  : ip of the ocr file (set in constats)
        path_to_ocr_input_file (str)      : abs path to input files

    Returns:
        time_taken_ocr_file (int) time taken to ocrize a single file.

    Author:
        titus@stride    
    """
    # init timers
    time_taken_ocr_file = 0
    time_end_ocr_file = 0
    time_start_ocr_file = 0

    # Prime status logger
    logger.debug("Path to File for OCR %s", path_to_ocr_input_file)
    logger.info("Path to File OCRized %s", path_to_ocrzd_file)

    # Calls the tesseract ocr

    time_start_ocr_file = time.time()

    ocrize_file_tesseract(
        path_to_ocr_input_file, path_to_ocrzd_file, ocr_ip, ocr_language
    )

    time_end_ocr_file = time.time()
    time_taken_ocr_file = time_end_ocr_file - time_start_ocr_file
    logger.debug("Time Taken for OCRization %s", str(time_taken_ocr_file))

    return time_taken_ocr_file


def merge_ocrized_files(path_to_pdf_file, pdfs_ocr_folder):

    """ helper function to merge ocrized pdf files to a single pdf output file

    Args:
        path_to_pdf_file (str): path to the original pdf file

                                
        pdfs_ocr_folder (str) : abs path to ocrized pdf files

    Returns:
       -
        
    output:
        PDF file with the same name as input file but with _ocrized.pdf    
    Author:
        titus@stride    
    """

    # format processing variables
    _, input_file_extention, _ = extract_file_details_from_path(path_to_pdf_file)

    # init timers
    time_taken_pdf_merge = 0
    time_end_pdf_merge = 0
    time_taken_pdf_merge = 0

    # init flags
    is_pdf_merge_sucess = False

    # Prime logger
    logger.info("PDF Pages -> PDF Starting")

    # Format Output File
    path_to_ocrzd_file = path_to_pdf_file.replace(
        "." + input_file_extention, PDF_MODIFIER_OCR
    )

    # start Timer
    time_start_pdf_merge = time.time()

    # call the function
    is_pdf_merge_sucess = pdf_pages_to_pdf(path_to_ocrzd_file, pdfs_ocr_folder)

    # End Timer
    time_end_pdf_merge = time.time()
    time_taken_pdf_merge = time_end_pdf_merge - time_start_pdf_merge

    # Prime Logger
    logger.debug("Time Taken for PDF Merge %s", str(time_taken_pdf_merge))
    logger.info("PDF->Parts Conversion Complete: %s", str(is_pdf_merge_sucess))


def ocrize_files_in_folder(
    path_to_pdf_file,
    path_to_ocr_input_file,
    path_to_ocrzd_file,
    images_folder,
    pdfs_ocr_folder,
    ocr_language="all",
):
    """ helper function to merge ocrized pdf files to a single pdf output file

    Args:
        path_to_pdf_file (str): abs path to the original pdf file
        path_to_ocrzd_file (str): abs path to the output pdf file
        path_to_ocr_input_file (str): abs path to the directory where processed pdf pages  are stored
        pdfs_ocr_folder (str): abs path to the folder where the ocrized files are to be stored
        images_folder(str): abs path to the folder where the processed image files are stored
        ocr_language(str): OCR language mode. 
    Returns:
       -
        
    output:
        PDF file with the same name as input file but with _ocrized.pdf    
    Author:
        titus@stride    
    """

    # Init timers
    time_taken_ocr_file = 0
    time_taken_ocr_single_file = 0
    time_taken_ocr_avg_file = 0

    # Get list of processed | Extracted Images

    temp_image_names, temp_image_numnber = getDirList_sorted_int(
        images_folder, PNG_MODIFIER
    )

    logger.debug("Total number of image pages: %s", str(temp_image_numnber))

    # OCRize Each file
    for temp_image in temp_image_names:

        # Format I/O
        path_to_ocr_input_file = temp_image
        temp_pdf_name = os.path.basename(path_to_ocr_input_file)
        path_to_ocrzd_file = os.path.join(pdfs_ocr_folder, temp_pdf_name)

        # Prime logger
        logger.debug("Path to File for conversion %s", path_to_pdf_file)
        logger.debug("Path to Final File after OCRization %s", path_to_ocrzd_file)

        try:

            # OCRize a single file
            time_taken_ocr_single_file = ocr_single_file(
                path_to_ocr_input_file, path_to_ocrzd_file, ocr_ip, ocr_language
            )

            # tally time taken to ocr files so far
            time_taken_ocr_file = time_taken_ocr_file + time_taken_ocr_single_file

        except Exception as e:
            logger.error("OCRization of file failed")
            logger.debug(e)
            logger.debug("Path to File for conversion %s", path_to_pdf_file)
            logger.debug("Path to Final File after OCRization %s", path_to_ocrzd_file)

    # Format timers
    time_taken_ocr_avg_file = (time_taken_ocr_file) / temp_image_numnber
    time_taken_ocr_file = (time_taken_ocr_file) / temp_image_numnber

    # Prime Logger
    logger.debug("Time Taken for avg OCRization %s", str(time_taken_ocr_avg_file))
    logger.debug("Time Taken for total  OCRization %s", str(time_taken_ocr_file))


def ocr_processed_files(
    path_to_pdf_file,
    is_pdf_splice_enabled,
    path_to_ocr_input_file,
    path_to_ocrzd_file,
    images_folder,
    pdfs_ocr_folder,
    ocr_language="all",
):
    """ Processes files before and after calling the ocr.
        Can handles single files, multi files in folder for supported pdf and
        image files

    Args:
        is_pdf_splice_enabled (bool): Set flag to merge output of all files in a folder
                                        to a single pdf
        path_to_ocr_input_file (str)      : abs path to input files(s)
        ocr_language(str): OCR language mode. 

    Returns:
        is_ocrization_sucessful (bool) Flag returns true if the function ran sucessfully

    Author:
        titus@stride    
    """
    # format output files
    is_ocrization_sucessful = True

    # OCRize the Input file
    time_taken_ocr_file = 0

    try:

        if is_pdf_splice_enabled is False:
            logger.debug("PDF Splice Disabled")
            _ = ocr_single_file(
                path_to_ocr_input_file, path_to_ocrzd_file, ocr_ip, ocr_language
            )

        # Add fallback thing after for when splice or anything failes

        elif is_pdf_splice_enabled is True:
            logger.debug("PDF Splice Enabled")
            logger.debug("PDF IMAGE PAGES -> OCRIZED PDF PAGES : Started")

            ocrize_files_in_folder(
                path_to_pdf_file,
                path_to_ocr_input_file,
                path_to_ocrzd_file,
                images_folder,
                pdfs_ocr_folder,
                ocr_language,
            )

            merge_ocrized_files(path_to_pdf_file, pdfs_ocr_folder)

    except Exception as e:
        logger.error("OCRization of file failed")
        logger.debug(e)
        is_ocrization_sucessful = False

    return is_ocrization_sucessful


def call_command(cmd_tesseact, timeout_sec):
    print (timeout_sec) 
    timeout_sec =  int(timeout_sec)
    logger.debug(cmd_tesseact)

    proc = subprocess.Popen(
        cmd_tesseact,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        preexec_fn=os.setsid,
    )

    def kill_proc():
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

    timer = Timer(timeout_sec, kill_proc)
    timer.start()
    stdout, stderr = proc.communicate()
    timer.cancel()
    return stdout, stderr


def init_ocr_tesseract(file_path, ocr_path, timeout=15, language_mode="all", is_image_input = False):

    """
        Description :   This function calls tesseract and ocrizes and returns a single pdf file
                            for an input file in the following formats :
                            (TIF, JPG, JPEG, PDF)

        Input       :   Path to the input file       (String)
                        Path path to the output file (String) 
                        Upper bound  time in minutes to spend on each file (int)
                        Language of the ocr backend model (string)
                        Flag to denote image input (Bool)


        Return      :   flag that denotes process sucess   (Bool)

        Author      :   Titus@stride
    """
    # Output to avoid schema errors
    ocr_file_noext = ocr_path.replace(".pdf", "")
    cmd_tesseact = ""
    
    # Tessercat Parameters ( python is not importing constants properly)
    # Dev
    TESS_DATA_DIR = "/usr/share/tesseract-ocr/5/tessdata/"

    # Prod
    # TESS_DATA_DIR = "/home/stride/.local/share/tessdata"
    TESS_CMD_HEAD = "tesseract "
    TESS_PARMS = " --psm 1 --oem 1 pdf"
    TESS_PARMS = TESS_PARMS + " -c tessedit_do_invert=0"
    TESS_PARMS_OPT = " --dpi 300"
    TESS_DATA_DIR_CMD =  " --tessdata-dir  "


    if is_image_input == False:
        TESS_PARMS = TESS_PARMS_OPT + TESS_PARMS    

    # formatting I/O paths to avoid string errors.
    file_path = '"{}"'.format(file_path)
    ocr_file_noext = '"{}"'.format(ocr_file_noext)
    TESS_DATA_DIR = '"{}"'.format(TESS_DATA_DIR)

    # command calls for tesseact and permissions

    if language_mode == "all":
        cmd_tesseact = (
            TESS_CMD_HEAD + file_path + " " + ocr_file_noext + TESS_PARMS
        )
    language_mode = language_mode.split('+')
    check =  all(item in OCR_SUPPORTED_LANGS.keys() for item in language_mode)
    language_tess_final = ' -l '
    if check:

        # get langauge code for tess from iso dict
        for language in language_mode:
            language_tess = OCR_SUPPORTED_LANGS.get(language)
            # if langauge not in dict. default to normal ocr
            if language_tess == None:
                language_tess = ""
            elif language_tess_final==' -l ':
                language_tess_final =language_tess_final + language_tess
            else:
                language_tess_final =language_tess_final + '+' + language_tess
        cmd_tesseact = (
            TESS_CMD_HEAD
            + file_path
            + " "
            + ocr_file_noext
            + TESS_DATA_DIR_CMD
            + TESS_DATA_DIR
            + language_tess_final
            + TESS_PARMS
        )
    # print(cmd_tesseact)

    count = 0
    while count < 3:
        stdout, stderr = call_command(cmd_tesseact, timeout)
        
        if os.path.exists(ocr_path):
            logger.debug("OCR successful: " + ocr_path)
            break
        count += 1
    # print(stdout, stderr)
    if os.path.exists(ocr_path):
        return True, None
    logger.error("Failed to OCRize: %s - %s" % (stdout, stderr))
    return False, None

if __name__ == "__main__":

    file_path = "./test_files/t1.tif"
    ocr_path =  "./test_files/t1_ocr"
    init_ocr_tesseract(file_path, ocr_path, timeout=15, language_mode="all", is_image_input = False)

    pass
