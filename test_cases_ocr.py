import os
import subprocess
import cv2
from cv2.ximgproc import guidedFilter
import requests

import pytest


IP_ADDRESS_LOCAL = "0.0.0.0"
IP_ADDRES_SERVER = "13.80.146.180:8889"
def check_tesseract_installation():
    """
        Description :   This function is used to check if tesseract 4 
                        and leptonica is installed.

        Input       :   -

        Return      :   Boolean flags (Tessetact , leptonica)   if they are currectly installed 

        Author      :   Titus@stride
    """

    is_tesseract_install_sucess = False
    is_leptonica_install_sucess = False
    command_to_call = "tesseract -v "

    try:
        # Call the command to tesseract to get the orientation information.
        output_from_shell = subprocess.check_output(command_to_call, shell=True)

        # Set output formatting to avoid nonsense errors
        output_from_shell = output_from_shell.decode("utf-8")
        
        # List of lines from the output
        output_from_shell_list = output_from_shell.split("\n")
        
        # Loop through list of lines in the output and 

        for line in output_from_shell_list:

            line = line.split(" ")
            # Check if tessesct is properly installed
            if line[0] == "tesseract":
                # Check if tesseract version is 4
                if line[1][0] == "4":
                    is_tesseract_install_sucess = True

            if "leptonica" in line[0] or "leptonica" in line[1]:
                is_leptonica_install_sucess = True
    except Exception as e:
        #logger.Error("Could not extract verify Tesseract and/or leptonica installation")
        #logger.Error(e)
        pass            

    return is_tesseract_install_sucess, is_leptonica_install_sucess


def check_cv2_install():

    """
        Description :   This function is used to check if
                        cv2 can be imported sucessfull.
        Input       :   -

        Return      :   Boolean flag if they are import correctly. 

        Author      :   Titus@stride
    """
    is_cv2_proper = False
    try:
        import cv2
        is_cv2_proper = True

    except Exception as e:
        #logger.Error("Could not extract verify Tesseract and/or leptonica installation")
        #logger.Error(e)
        pass 

    return is_cv2_proper

def check_cv2_opt_install():
    """
        Description :   This function is used to check if a cv2 filter in the
                        contrib package can be imported sucessfull.
        Input       :   -

        Return      :   Boolean flag if they are import correctly. 

        Author      :   Titus@stride
    """
    
    is_cv2_opt_proper = False
    try:
        from cv2.ximgproc import guidedFilter
        is_cv2_opt_proper = True

    except Exception as e:
        #logger.Error("Could not extract verify Tesseract and/or leptonica installation")
        #logger.Error(e)
        pass 

    return is_cv2_opt_proper            

def ocrize_file_tesseract(file_path, output_path, ip_2_ocr="0.0.0.0"):
    """
        Description :   This function calls the tesseract OCR engine to OCRize a file.

                        String path to the Input file (tif)
                        String path for the output file (including filename sans .pdf extension)
                        String ip address for ocr. 0.0.0.0 calls tesseract on the system (Defaut).

        Input       :   path to PDF file (String)

        Return      :   path to OCRized PDF file (String)

        Author      :   Titus@stride
    """

    # Makes tesseract OCR  to run locally
    if ip_2_ocr == "0.0.0.0":
        try:
            # Format the input and output filenames for OCR
            path_to_temp_pdf = '"{}"'.format(file_path)
            path_to_ocrzd_file = '"{}"'.format(output_path)

            # Tesseract command calls
            command_to_call = "tesseract "
            command_to_call = command_to_call + path_to_temp_pdf + " " + path_to_ocrzd_file
            command_to_call = command_to_call + " --psm 1 --oem 1 pdf"
            command_to_call = command_to_call + " 2>/dev/null"
        
            print (command_to_call)
            # Call the command
            os.system(command_to_call)
        except Exception as e:
            print (e)
            print ('Tesseract Error')    

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
            logger.error(response.content)
            logger.error(response)
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
            logger.info("Waiting for OCRization to complete.", json.dumps(response_json))
            logger.info(response_json)
            if response_json["status"] not in ["queued", "started"]:
                break
            time.sleep(15)

        if not response_ocr_path.ok:
            logger.info(response_ocr_path)
            return ""

        ocr_pdf_url = response_json["result"]
        response = requests.get(ocr_pdf_url)
        output_path = output_path + ".pdf"
        logger.info(output_path)
        try:
            with open(output_path, "wb") as ocr:
                ocr.write(response.content)
        except Exception as e:
            print("Failed to save OCRized file from the server to " + output_path)

    return output_path


def run_tesseract_test(input_type, ip_address):
    """
        Description :   This function is used to check if
                        tesseract can run locally (PNG -> PDF).

        Input       :   Input type (String) - "png", "tif",
                        IP address of the OCR server



        Return      :   Boolean flag if it runs correctly. 

        Author      :   Titus@stride
    """

    is_test_sucessful  = False

    if input_type    == "png":
        input_file  =  '3.png'
        output_file =  '3_OCRIZED'
    elif input_type  == "tif":
        input_file  = 't1.tif'
        output_file = 't1_OCRIZED'

    elif input_type  == "pdf":
        input_file  = 'test_1.pdf'
        output_file = 'test_1_OCRIZED'        



    try:
        cwd = os.getcwd()
        input_file_path = os.path.join(cwd,'test_files', input_file )
        output_file_path = os.path.join(cwd,'test_files',output_file )

        output_file = ocrize_file_tesseract(input_file_path, output_file_path, ip_address)

        print (output_file, ":outputfilepath")
        is_test_sucessful = True

    except Exception as e:
        #logger.Error("Could not verify Tesseract Installation")
        #logger.Error(e)
        print (e)
        pass 

    return is_test_sucessful    
 
def test_tesseract_and_leptonica():
    """
    Description : runs the test for checking tesseract and leptonica install
    """
    assert all(check_tesseract_installation())
    
    # if is_tesseract_install_sucess == True:
    #     if is_leptonica_install_sucess  == True:
    #         assert True
    #     else:
    #         assert False
    # else:
    #     assert False                

def test_cv2_install():
    """
    Description : Runs the test for checking cv2 imports
    """
    assert check_cv2_install()


def test_cv2_opt_install():
    """
    Description : Runs the test for checking cv2 optional packages
    """
    assert check_cv2_opt_install()
           

# All tests must start with test_
def test_tesseract_install_png():
    """
    Description : Runs the test for checking if tessesact works properly (local, PNG -> PDF)
    """
    is_tesseract_pdf_local_working  = False
    is_tesseract_pdf_remote_working = False

    file_type = "png"

    # Local Test
    ip_address = IP_ADDRESS_LOCAL
    assert run_tesseract_test(file_type, ip_address) is True

    # Remote Test
    ip_address = IP_ADDRES_SERVER
    assert  run_tesseract_test(file_type, ip_address) is True



def test_tesseract_install_tif():
    """
    Description : Runs the test for checking if tessesact works properly (local, PNG -> PDF)
    """

    is_tesseract_pdf_local_working  = False
    is_tesseract_pdf_remote_working = False
    
    file_type = "tif"

    # Local Test
    ip_address = IP_ADDRESS_LOCAL
    assert  run_tesseract_test(file_type, ip_address) is True

    # Remote Test
    ip_address = IP_ADDRES_SERVER
    assert  run_tesseract_test(file_type, ip_address) is True

# All tests must start with test_
def test_tesseract_intall_pdf():
    """
    Description : Runs the test for checking if tessesact works properly (local, PDF -> PDF)
    """
    is_tesseract_pdf_local_working  = False
    is_tesseract_pdf_remote_working = False

    file_type = "pdf"

    # Local Test
    ip_address = IP_ADDRESS_LOCAL
    assert run_tesseract_test(file_type, ip_address) is True

    # Remote Test
    ip_address = IP_ADDRES_SERVER
    assert  run_tesseract_test(file_type, ip_address) is True