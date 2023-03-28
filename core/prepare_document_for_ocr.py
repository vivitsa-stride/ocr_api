# -*- coding: utf-8 -*-
# Script that prepares documents for stride's OCR.
# Usecase :- Bradesco , Smart OCR
# Author : Titus
# Organization: Stride.AI

# Imports
from __future__ import print_function, division

# built in imports
import glob
import json
import logging
from itertools import repeat
import os
import shutil
from concurrent.futures import ProcessPoolExecutor
import subprocess
import sys
import time
from collections import Counter
import pdfrw


# External Imports
import cv2
import numpy as np
from cv2.ximgproc import guidedFilter

import imutils
from wand.image import Color, Image

from PyPDF2 import PdfFileReader, PdfFileWriter, PdfFileMerger



from .ocrize import *

# Global Variables
from .constants import *
from .script_to_languages_mapping import mappings

# from .core import *
# from core.ocrize import *
# from core.constants import *

# Global Flags | Limits
# This limits CV Threads to use 4 cores. [Match Tesseract and parrallelize]
dt = cv2.setNumThreads(4)

# Set logger configuration
# logger = logging.getLogger('ocr_preprocess')

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

# Debug function for profiling performance
# from pyinstrument import Profiler



def pdf_pages_to_pdf_legacy(path_to_output_pdf, path_to_pdf_pages):
    """
        Input      :    (String) Path to the output PDF file to be merged.
                        (String ) Path to the folder containing the pdfs to be merged.

        Output     :    Single PDF files for each page in the input pdf.

        Return     :    True if successful.
                        False if unsucessful. 

        Descrption :    This function reads a string folder name (abs) and merges the 
                        pdfs in that folder to a single pdf specified by an output pdf file path.
                        PyPDF2 Version

        Author     :    titus@stride
    """

    # Init vars
    temp_pdf_names = ""
    temp_pdf_number = 0

    is_pdf_merge_sucessful = True

    # Get list of pdf files in folder
    temp_pdf_names, temp_pdf_number = getDirList_sorted_int(
        path_to_pdf_pages, PDF_MODIFIER
    )

    logger.debug(path_to_output_pdf)

    # Format output PDF
    if PDF_MODIFIER not in path_to_output_pdf:
        path_to_output_pdf = path_to_output_pdf + PDF_MODIFIER

    # Initilize PDF merge
    merger = PdfFileMerger()

    # Loop through pdf pages and prepare to merge
    for filename in temp_pdf_names:

        # logger.debug(filename)
        try:

            merger.append(PdfFileReader(filename, "r"))

        except Exception as e:
            logger.error("PDF page Merge not sucessfull")
            logger.debug(filename)
            logger.debug(e)
            is_pdf_merge_sucessful = False

    # Write the PDF
    try:

        merger.write(path_to_output_pdf)

    except Exception as e:
        logger.error("PDF merge Generation not sucessfull")
        logger.debug(e)
        is_pdf_merge_sucessful = False

    return is_pdf_merge_sucessful




def pdf_pages_to_pdf(path_to_output_pdf, path_to_pdf_pages):
    """
        Input      :    (String) Path to the output PDF file to be merged.
                        (String ) Path to the folder containing the pdfs to be merged.

        Output     :    Single PDF files for each page in the input pdf.

        Return     :    True if successful.
                        False if unsucessful. 

        Descrption :    This function reads a string folder name (abs) and merges the 
                        pdfs in that folder to a single pdf specified by an output pdf file path.
                        Pdfrw version. Faster, eliminates eof errors.

        Author     :    titus@stride
    """

    # Init vars
    temp_pdf_names = ""
    temp_pdf_number = 0

    is_pdf_merge_sucessful = True

    # Get list of pdf files in folder
    temp_pdf_names, temp_pdf_number = getDirList_sorted_int(
        path_to_pdf_pages, PDF_MODIFIER
    )
    
    logger.debug(path_to_output_pdf)

    # Format output PDF
    if PDF_MODIFIER not in path_to_output_pdf:
        path_to_output_pdf = path_to_output_pdf + PDF_MODIFIER

    # Initilize PDF merge
    #merger = PdfFileMerger()

    # Open output pdf file writer
    pdf_output = pdfrw.PdfWriter()



    # Loop through pdf pages and prepare to merge
    for filename in temp_pdf_names:

        # logger.debug(filename)
        try:

            #merger.append(PdfFileReader(filename, "r"))
            # Read pdf page
            pdf_page = pdfrw.PdfReader(filename)

            # Append pdf page to pdf
            pdf_output.addpage(pdf_page.pages[0])

        except Exception as e:
            logger.error("PDF page Merge not sucessfull")
            logger.debug(filename)
            logger.debug(e)
            is_pdf_merge_sucessful = False

    # Write the PDF
    try:

        pdf_output.write(path_to_output_pdf)

    except Exception as e:
        logger.error("PDF merge Generation not sucessfull")
        logger.debug(e)
        is_pdf_merge_sucessful = False
    
    logger.debug(path_to_output_pdf)
    logger.debug(path_to_pdf_pages)

    return is_pdf_merge_sucessful



def pdf_to_pdf_pages(path_to_pdf_file, path_to_output_files):
    """
        Input       :   (String) Path to the PDF file to be split.
                        (String) Path for the output pdf files.

        Output     :    Single PDF files for each page in the input pdf.

        Return     :    True if successful.
                        False if unsucessful. 

        Descrption :    This function reads a list of string pdf file names and
                        converts it seperate pdf document pages.
                        in a seperate folder.
        Author     :    titus@stride
    """

    # init vars
    pdf_filename = ""


    is_pdf_extraction_sucessful = True

    # Extract Filename
    pdf_filename = os.path.splitext(os.path.basename(path_to_pdf_file))[0]

    # output file path

    output_file_dir = path_to_output_files

    # Read the PDF file
    
    pdf_file = PdfFileReader(path_to_pdf_file)

    logger.debug(pdf_filename)
    logger.debug(output_file_dir)

    # Extract each page as seperate pdf
    for page in range(pdf_file.getNumPages()):
        try:
            # Prep PDF writer object
            pdf_writer = PdfFileWriter()
            pdf_writer.addPage(pdf_file.getPage(page))

            # Format output PDF name 
            output_filename = "{}.pdf".format(page)

            output_file_path = os.path.join(output_file_dir, output_filename)

            # Write the PDF file
            with open(output_file_path, "wb") as out:
                pdf_writer.write(out)

        except Exception as e:
            logger.error("PDF page extraction not sucessfull")
            logger.debug(page)
            logger.debug(e)
            is_pdf_extraction_sucessful = False

    return is_pdf_extraction_sucessful


def getDirList_sorted_int(inp_folder, fld_format, is_int_filenames=False):
    """
        Description :   This function is used to determine the number of files.
                            of a partifuclar format are present in the query folder.

        Input       :   String filename , 
                        String format of type of file to look for
                        Flag to denote filenames are integers
                            (Optional| Default = True)

        Return      :   List of string files (abs paths) of that format in the document.
                        Number of files in that folder.

        Author      :   Titus@stride
    """

    # Format Query
    folder_files_im = inp_folder + "*" + fld_format

    # Get number of files
    filelist_im = glob.glob(folder_files_im)
    num_files_im = len(filelist_im)

    # Sort the file names in alphabetical order

    # Sort int and string file names seperately
    if is_int_filenames == True:
        filelist_im.sort(key=lambda fname: int(os.path.basename(fname.split(".")[0])))
    else:
        filelist_im.sort()

    return filelist_im, num_files_im


def upscale_text_image(
    path_to_gray_image, binerized_image, scale=0.33, is_denoise=True
):
    """
        Description :   This function upscales an image by the scale factor.

        Input       :   path to the classifer (String), 
                        image feature vector (numpy array)
                        Flag-  check to see if image is to be denoised . Default/recommended = True 

        Return      :   Class of the image feature vetor
        Author      :   Titus@stride   

    """
    # Extract soft edges from a binerized image using a guided filter
    #  with the gray image as the guide.
    src_image = binerized_image
    guide_image = path_to_gray_image

    if is_denoise  == True:
        filtered_image = guidedFilter(guide_image, src_image, 2, 0.01)
    else:
        filtered_image = src_image

    scale_limit = 30000

    # Scale the width and the height
    width, height = src_image.shape
    if not width >= scale_limit or not height >= scale_limit:
        width_scaled = int(width + (width * scale))
        height_height = int(height + (height * scale))

        if not width_scaled >= scale_limit or not height_height >= scale_limit:
            # upscale the image with the new dimentuons using bicubic interpolation.
            resized_image = cv2.resize(
                filtered_image, (height, width), interpolation=cv2.INTER_CUBIC
            )
        else:
            width_scaled = int(width + (width * 2))
            height_height = int(height + (height * 2))

            if not width_scaled >= scale_limit or not height_height >= scale_limit:
                # upscale the image with the new dimentuons using bicubic interpolation.
                resized_image = cv2.resize(
                    filtered_image, (height, width), interpolation=cv2.INTER_CUBIC
                )
            else:
                width_scaled = int(width + (width))
                height_height = int(height + (height))
                if not width_scaled >= scale_limit or not height_height >= scale_limit:
                    resized_image = cv2.resize(
                        filtered_image, (height, width), interpolation=cv2.INTER_CUBIC
                    )
                else:
                    resized_image = filtered_image
                # Dev note : Add 0.5 variats
    else:
        resized_image = filtered_image

    return resized_image


def read_single_image(path_to_image):
    """
        Description :   This function reads a single image
                        pased on its input path.

                        Primary loader - opencv
                        backup loader  - pillow

        Input       :   String path to image file

        Return      :   Image file -> numpy array

        Author      :   Titus@stride
    """
    # Load image using OpenCV and
    # expand image dimensions to have shape: [1, None, None, 3]
    # i.e. a single-column array, where each item in the column
    # has the pixel RGB value.
    try:
        image = cv2.imread(path_to_image)
        non_zero_count = np.count_nonzero(image)

        # Backup image loader-> Pillow. checks if image is blank/empty.
        if non_zero_count == 0:
            logger.warning("Switching to Backend Image Loader")
            
            image = Image.open(path_to_image)
            image = np.asarray(image).copy()
    except Exception as e:
        logger.error("Image File annot be read")
        logger.error("e")
    return image
def display_image(out_image):

    scale_percent = 30  # percent of original size
    width = int(out_image.shape[1] * scale_percent / 100)
    height = int(out_image.shape[0] * scale_percent / 100)
    dim = (width, height)
    resized = cv2.resize(out_image, dim, interpolation=cv2.INTER_AREA)
    # resized = out_image
    cv2.imshow("image", resized)
    k = cv2.waitKey(5000)
    if k == 27:  # If escape was pressed exit
        cv2.destroyAllWindows()


def convert_bgr_2_grayscale_image(orig_image):
    """
        Description :   This function converts an image to grayscale
                        Primary loader - opencv
                        backup loader  - pillow

        Input       :   CV2 Image file

        Return      :   CV2 Image file

        Author      :   Titus@stride
    """
    # Convert Rgb Image to grayscale
    im_gray = cv2.cvtColor(orig_image, cv2.COLOR_BGR2GRAY)

    return im_gray


def enchance_image_text(input_image):
    """
        Description :  Enhance image text
                        

        Input       :   CV2 Image file

        Return      :   CV2 Image file

        Author      :   Titus@stride
    """
    # Define kernal for Morph opening operation
    kernel = np.ones((1, 2), np.uint8)

    # Perform the opening operation
    converted_image = cv2.morphologyEx(input_image, cv2.MORPH_OPEN, kernel)

    return converted_image


def aggressive_noise_removal(original_image):
    """
        Description :   This function Attemps to denoise the image using 
                        a lossy bineraziatio - otsu after blurring it using a 
                        gaussian filter

        Input       :   CV2 Image

        Return      :   CV2 Image

        Author      :   Titus@stride
    """
    # Otsu's thresholding after blurring
    processed_image = blur_image(original_image)
    _, processed_image = cv2.threshold(
        processed_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return processed_image


def denoise_and_upscale_single_image(
    image_file_name, is_incude_agg_denoise=True, is_include_superres=True
):
    """
        Input      :   String file name of the image to be converted
                       Flag to include aggressive denoising. Default - True
                       Flag to enable superresolution : Recommended / Default : True

        Output     :   Filtered, denoised and upscaled image.
        Returns    :   Nothng

        Descrption :    This function reads a string image filename
                        and fixes, noise, improves text quality and upscales the image.
        Author     :   titus@stride
    """

    # Read single image
    current_image = read_single_image(image_file_name)

    # Convert the image to grayscale
    grayscale_image = convert_bgr_2_grayscale_image(current_image)

    # Denosie image by filtering processes
    current_image = attempt_denoise_image(grayscale_image)

    # Improve the text quality of the image
    cleaned_image = enchance_image_text(current_image)

    # Lossy Noise removal using filtering techniques
    if is_incude_agg_denoise == True:

        binary_image = aggressive_noise_removal(cleaned_image)
        binary_image = background_negation(binary_image)

    else:
        binary_image = cleaned_image

    # Super Resolution
    if is_include_superres == True:
        uprez_image = upscale_text_image(
            cleaned_image, binary_image, 2.00, is_incude_agg_denoise
        )

        final_image = uprez_image
    else:
        final_image = binary_image

    # Save the image
    cv2.imwrite(image_file_name, final_image)


def check_rotation(image_name):
    """
        Input      :   String path to image

        Returns     :   String Angle at witch image is to be rotated to fix orientation
                        Boolean flag - to check if the file has been processed


        Descrption :    This function reads a string filename, and returns the angle at which to fix 
                        its orientation (if needed).
        Author     :   titus@stride
    """

    # Init defalt outputs
    rotate_processed = True
    output_rotate_command = ""
    rotate_status = "0"

    # Create an input for invoking the needed function
    command_to_call = "tesseract --psm 0 "
    path_to_image = '"{}"'.format(image_name)
    command_to_call = command_to_call + path_to_image
    command_to_call = command_to_call + " -"
    command_to_call = command_to_call + " 2>/dev/null"

    try:

        # Call the command to tesseact to get the orientation information.
        output_rotate_command = subprocess.check_output(command_to_call, shell=True)
        output_rotate_command = output_rotate_command.decode("utf-8")

        # Format output
        rotate_status = output_rotate_command.split("\n")

        for line_rs in rotate_status:
            rotate_status = line_rs.split(" ")
            if rotate_status[0] == "Rotate:":
                rotate_status = rotate_status[1]
                break

    except Exception as e:
        # Rotation command did not process sucessfully
        # can happen if there is not enough text for tesseract
        logger.error("Rotation Check failed")
        logger.error(e)
        rotate_processed = False
        rotate_status = "0"

    return rotate_status, rotate_processed


def rotate_image_by_angle(image_path, angle_to_rotate):
    """
        Description :   This function rotates an image by the angle provided

        Input       :   String path to an image,
                        Integer angle to rotate the image

        Return      :   Boolean flag denoting the success/failure of the operation

        Output      :  Image rotate at the specified angle

        Author      :   Titus@stride
    """

    rotated_image_sucessful = True

    try:
        # Read Single Image
        current_image = read_single_image(image_path)

        # Convert the image to grayscale
        grayscale_image = convert_bgr_2_grayscale_image(current_image)

        # Rotate the image by the current angle
        current_image = imutils.rotate_bound(grayscale_image, angle=angle_to_rotate)

        final_image = current_image
        # Save the image
        cv2.imwrite(image_path, final_image)
        rotated_image_sucessful = True

    except:
        rotated_image_sucessful = False

    return rotated_image_sucessful

def luminfix_image_file(image_name):
    """
        Input       :   String path to image

        Returns     :  Boolean flag - to check if the file has been processed 

        Output      : luminosity fixed Image


        Descrption  :   This function reads a string filename, and changes up the white/black balence to handle
                        variations in lumination

        Author      :   titus@stride
    """

    # Init defalt outputs
    deskew_processed = True
    output_deskew_command = ""

    # Create an input for invoking the needed function
    command_to_call = "convert "

    output_filename = image_name
    # output_filename = output_filename.replace(".png","_X.png")
    path_to_image = '"{}"'.format(image_name)
    path_to_image_output = '"{}"'.format(output_filename)
    # Dev command
    # path_to_image_output = path_to_image_output.replace(".png","_X.png")
    command_to_call = (
        command_to_call + path_to_image + " -level 0,75% " + path_to_image_output
    )
    command_to_call = command_to_call + " 2>/dev/null"

    try:
        # Call the command to fix skew
        subprocess.call(command_to_call, shell=True)

    except Exception as e:
        # Deskew command did not process sucessfully
        logger.error("Deskew Operation failed")
        logger.error(e)
        deskew_processed = False

    return deskew_processed


def deskew_image_file(image_name):
    """
        Input       :   String path to image

        Returns     :  Boolean flag - to check if the file has been processed 

        Output      : Deskewed Image


        Descrption  :   This function reads a string filename, and corrects images that are skewed (if correction needed)
        Author      :   titus@stride
    """

    # Init defalt outputs
    deskew_processed = True
    output_deskew_command = ""

    # Create an input for invoking the needed function
    command_to_call = "convert "

    output_filename = image_name
    # output_filename = output_filename.replace(".png","_X.png")
    path_to_image = '"{}"'.format(image_name)
    path_to_image_output = '"{}"'.format(output_filename)
    # Dev command
    # path_to_image_output = path_to_image_output.replace(".png","_X.png")
    command_to_call = (
        command_to_call + path_to_image + " -deskew 40 " + path_to_image_output
    )
    command_to_call = command_to_call + " 2>/dev/null"

    try:
        # Call the command to fix skew
        subprocess.call(command_to_call, shell=True)

    except Exception as e:
        # Deskew command did not process sucessfully
        logger.error("Deskew Operation failed")
        logger.error(e)
        deskew_processed = False

    return deskew_processed


def fix_and_enhance_images(
    file_name,
    is_fix_rotation=True,
    is_lumin_fix = True,
    is_fix_agg_noise=True,
    is_fix_skew=True,
    is_filters_enabled=True,
    is_superess_enabled=True,
):
    """
        Input      :   List of String- image filenames
                       Flag to fix rotation issues. Default - True
                       Flag to fix skew issues. Default - True
                       Flag to fix agressive noise. Recommended/ Default - True
                       lag to enable filtering|superresolution process: Recommended / Default : True
                       Flag to enable superresolution : Recommended / Default : True

        Output     :   processed Images
        Returns    :   Nothng

        Descrption :    This function reads a list of string image filenames
                        and processes them to fix issues.
        Author     :   titus@stride
    """

    processed_all = True
    is_rotation_completed = True

    # init timers
    time_taken_fix_rotation = 0
    time_end_fix_rotation = 0
    time_start_fix_rotation = 0
    time_taken_deskew= 0
    time_end_deskew= 0
    time_start_deskew= 0
    time_taken_filtering= 0
    time_end_filtering= 0
    time_start_filtering= 0

    # Correct Document Rotation
    if is_fix_rotation == True:
        logger.info("Fixing Rotation: Started")
        time_start_fix_rotation = time.time()
        try:
            fix_rotation(file_name)
        except:
            logger.error("Image Page cannot be Rotated")
            logger.error(file_name)
            logger.debug(e)
            processed_all = False

        time_end_fix_rotation = time.time()
        time_taken_fix_rotation = time_end_fix_rotation - time_start_fix_rotation

        logger.debug("Time Taken for fixing Rotation %s", str(time_taken_fix_rotation))
        logger.debug("Fixing Rotation operation status is: Completed")
        logger.info("Fixing Rotation: Completed")

    # Deskew Image
    if is_fix_skew == True:
        logger.info("Fixing Orientation: Started")

        time_start_deskew = time.time()
        try:
            # fix skewed image
            correctly_deskewed = deskew_image_file(file_name)

        except Exception as e:
            logger.error("Image Page cannot be DeSkewed")
            logger.error(file_name)
            logger.debug(e)
            processed_all = False

        time_end_deskew = time.time()
        time_taken_deskew = time_end_deskew - time_start_deskew
        logger.debug("Time Taken for deskew %s", str(time_taken_deskew))

        logger.info("Fixing Orientation: Completed")

    # fix lumination issues Image
    if is_lumin_fix == True:
        logger.info("Fixing Lumination : Started")

        time_start_deskew = time.time()

        try:
            # fix Lumination issues
            correctly_deskewed = luminfix_image_file(file_name)

        except Exception as e:
            logger.error("Image Page cannot be fixed for lumination consistancy")
            logger.error(file_name)
            logger.debug(e)
            processed_all = False

        time_end_deskew = time.time()
        time_taken_deskew = time_end_deskew - time_start_deskew
        logger.debug("Time Taken for lumination fixes is %s", str(time_taken_deskew))

        logger.info("Fixing lumination: Completed")


    # Filter files
    if is_filters_enabled == True:
        logger.info("Running Filtering Operations : Started")
        time_start_filtering = time.time()

        #for file_name in folder_file_names:

        try:
            # Denoise and upscale single image
            denoise_and_upscale_single_image(file_name, is_fix_agg_noise, is_superess_enabled)
        except Exception as e:
            logger.error("Image Page cannot be filtered/upscaled")
            logger.error(file_name)
            logger.debug(e)
            processed_all = False

        time_end_filtering = time.time()
        time_taken_filtering = time_end_filtering - time_start_filtering
        logger.debug(
            "Time Taken for Filtering Operations %s", str(time_taken_filtering)
        )

        logger.info("Running Filtering Operations : Completed")

    return processed_all


def fix_rotated_images(folder_file_names):
    """

        Descrption  :   This function fixes rotated images.

        Input       :   List of String image file paths


        Returns     :  Boolean flag - to check if the file has been processed sucessfully

        Output      : Human readable rotated documents (0 degrees)


        Author      :   titus@stride

    """

    processed_all = True
    # Read image-> gray scale-> fix rotation LR -> Check inv
    #file_inversion_by_page = []
    file_rotation_by_page = []

    # Fix Rotation
    """with ProcessPoolExecutor(max_workers=10) as exe:
            exe.map(fix_horizontal_rotation, folder_file_names)"""
    
    for file_name in folder_file_names:
        file_rotation_by_page, processed_all_first_pass = fix_rotation(
        file_name
    )

    """if processed_all_first_pass == False:
        processed_all = False"""

    return processed_all


def calculate_vertical_orientation(folder_file_names, file_rotation_by_page):
    """

        Descrption  :   This function calculates the origentation of the document based on the orientation of the text

        Input       :   List of String image file paths
                        List of file orietnatiosn from the first pass


        Returns     :  Boolean flag - to check if the file has been processed sucessfully
                       List of Orientation of documents by page.
        Author      :   titus@stride

    """
    i = 0
    fix_vertical_rotation = True
    file_inversion_by_page = []
    for file_name in folder_file_names:

        try:
            rotation_class = file_rotation_by_page[i]

            # If previous check classified it as Normal or inverted, pass along the same
            if rotation_class == "N":
                file_inversion_by_page.append("N")
            elif rotation_class == "I":
                file_inversion_by_page.append("I")

            # If there was a L | R rotation fix, check again.
            else:

                # Get the rotation angle of the image
                rotate_angle, r_st = check_rotation(file_name)

                # 0 --> Normal
                if rotate_angle == "0":
                    file_inversion_by_page.append("N")

                    # Dev - Append skew info here

                # 1 --> Inverted
                elif rotate_angle == "180":
                    file_inversion_by_page.append("I")

                    # Dev - Append skew info here

                # Leave the rest as normal
                else:
                    file_inversion_by_page.append("N")

        except Exception as e:
            logger.error("Rotating the  image file failed")
            logger.error(e)
            
            fix_vertical_rotation = False

        i += 1
    return file_inversion_by_page, fix_vertical_rotation


def fix_rotation(file_name):
    """

        Descrption  :   This function fixe text rotated by 180 or 270 degress

        Input       :   List of String image file paths



        Returns     :  Boolean flag - to check if the file has been processed sucessfully
                       List of Orientation of documents by page.

        Output      :  Horizontally oriented (180 or 270) document pages fixed.

        Author      :   titus@stride

    """
    fix_horizontal_rotaiton = True
    LR_Flag = 0
    """for file_name in folder_file_names:
        LR_Flag = 0"""
    try:

        # Get the rotation angle of the image
        rotate_angle, r_st = check_rotation(file_name)

        if r_st == True:

            # 0 --> Normal
            if rotate_angle == "0":
                pass
            elif rotate_angle == "180":
                rotated_image_process = rotate_image_by_angle(file_name, 180)

                # Dev - Append skew info here - 0

            # 2 --> Left Oriented, Fix and append.
            elif rotate_angle == "270":
                rotated_image_process = rotate_image_by_angle(file_name, -90)
                LR_Flag = 1

                # Dev - Append skew info here - 0

            # 2 --> Right Oriented, Fix and append.
            elif rotate_angle == "90":
                rotated_image_process = rotate_image_by_angle(file_name, 90)
                LR_Flag = 1

                # Dev - Append skew info here - 0
        if LR_Flag:
            rotate_angle, r_st = check_rotation(file_name)
            if rotate_angle == "0":
                pass
            elif rotate_angle == "180":
                rotated_image_process = rotate_image_by_angle(file_name, 180)

    except Exception as e:
        logger.error("Rotating the  image file failed")
        logger.error(e)

        
        fix_horizontal_rotaiton = False
        pass

    return fix_horizontal_rotaiton


def document_2_image_pages(
    path_to_input_pdf_file, images_folder_path, pdfs_folder, is_split_pdf_pages=True
):
    """
        Input      :    List String-PDF filenames

        Output     :    Images of pdf pages.
        Return     :    True if successful
                        False if unsucessful 

        Descrption :    This function reads a list of string pdf file names and
                        converts it to a 300 dpi image per page
                        in a seperate folder.
        Author     :    titus@stride
    """

    # Initialize output variables.
    is_pdf_to_pdf_pages_successful = False

    # Prepare output filepath

    input_file_name, input_file_extention, input_file_path = extract_file_details_from_path(
        path_to_input_pdf_file
    )
    input_extention_lower = input_file_extention.lower() 

    # input_file_name = os.path.basename(path_to_input_pdf_file)
    # input_file_path = os.path.dirname(path_to_input_pdf_file)
    # input_extention_lower = input_file_name.split(".")[-1]
    output_pdf_name = input_file_name.replace(" ", "_")
    

    # Prepare output file
    path_to_output_pdf = pdfs_folder[:-5]
    path_to_output_pdf = os.path.join(path_to_output_pdf, output_pdf_name)

    # Copy file to temp folder
    try:
        shutil.copyfile(path_to_input_pdf_file, path_to_output_pdf)
        logger.debug("Input File Copied successfuly to temp temp folder")
    except Exception as e:
        logger.error("Input File Failed to be successfuly copied to the temp folder")
        logger.error(e)

    # Code block that handles PDF -> PDF Pages - > Images
    if is_split_pdf_pages == True:

        # Handle PDF Files
        if input_extention_lower== PDF_TEXT:

            logger.debug("Input File -> Split Pages Is Enabled")

            # Extract pdf Pages from new pdf
            is_pdf_to_pdf_pages_successful = pdf_to_pdf_pages(

                path_to_output_pdf, pdfs_folder
            )

            if is_pdf_to_pdf_pages_successful:

                logger.info("Extrating Single PDF-> Multiple PDFs -> Multiple Pages")

                try:
                    # Get list of pdf files
                    temp_pdf_lists, temp_pdf_number = getDirList_sorted_int(
                        pdfs_folder, PDF_MODIFIER
                    )

                    # Remove original file from list of parts
                    if path_to_output_pdf in temp_pdf_lists:
                        temp_pdf_lists.remove(path_to_output_pdf)

                    # for each image Extract an image page
                    with ProcessPoolExecutor(max_workers=min(os.cpu_count(),len(temp_pdf_lists))) as exe:
                        exe.map(extract_image_from_pdf_cmd, temp_pdf_lists, repeat(images_folder_path), repeat(is_split_pdf_pages))
                        exe.shutdown()

                except Exception as e:
                    logger.error("PDF cannot be extracted.")
                    logger.debug(e)
                    logger.error("Trying backend -> Single Parse Extraction")

        # Handles TIF files
        elif input_extention_lower == TIF_TEXT:

            logger.info("Extrating Single TIF-> Multiple Pages")
            temp_pdf = path_to_output_pdf
            temp_pdf_name = os.path.basename(temp_pdf)
            temp_pdf_name = temp_pdf_name.replace(PDF_MODIFIER, "")

            convert_filename = "." + PNG_TEXT
            convert_filename = convert_filename.replace(" ", "_")
            convert_file_path = os.path.join(images_folder_path, convert_filename)

            try:

                extract_image_from_tif(
                    path_to_output_pdf, images_folder_path, is_split_pdf_pages
                )

            except Exception as e:
                logger.error("PDF cannot be extracted.")
                logger.debug(e)
                return False

    # if extraction unsucessfull or Flag for extract file is set
    # OR if page wise processing is disabled
    #  PDF | TIF -> Image Pages or Image pages

    elif is_pdf_to_pdf_pages_successful is False or is_split_pdf_pages is False:

        logger.debug("Split pages off")
        if input_extention_lower== PDF_TEXT:

            logger.info("Extrating Single PDF-> Multiple Pages")

            # Format Output names
            temp_pdf = path_to_output_pdf
            temp_pdf_name = os.path.basename(temp_pdf)
            temp_pdf_name = temp_pdf_name.replace(PDF_MODIFIER, "")

            convert_filename = "." + PNG_TEXT
            convert_filename = convert_filename.replace(" ", "_")
            convert_file_path = os.path.join(images_folder_path, convert_filename)

            try:

                extract_image_from_pdf_cmd(
                    path_to_output_pdf, images_folder_path, is_split_pdf_pages
                )

            except Exception as e:
                logger.error("PDF cannot be extracted.")
                logger.debug(e)
                return False    

        elif input_extention_lower == TIF_TEXT:

            logger.info("Extrating Single TIF-> Multiple Pages")
            temp_pdf = path_to_output_pdf
            temp_pdf_name = os.path.basename(temp_pdf)
            temp_pdf_name = temp_pdf_name.replace(PDF_MODIFIER, "")

            convert_filename = "." + PNG_TEXT
            convert_filename = convert_filename.replace(" ", "_")
            convert_file_path = os.path.join(images_folder_path, convert_filename)

            try:
                extract_image_from_pdf_cmd(
                    path_to_output_pdf, images_folder_path, is_split_pdf_pages
                )
                # Try this if above fails
                # extract_image_from_tif(
                #     path_to_output_pdf, images_folder_path, is_split_pdf_pages
                # )

            except Exception as e:
                logger.error("TIF cannot be extracted.")
                logger.debug(e)
                return False        


    # PDF processed properly

    return True


def extract_image_from_tif(temp_pdf_path, images_folder_path, is_file_split=True):
    """
        Input      :    String - abs path to TIF 
                        String - path to Images folder
                        Flag   - Page level processing True/False (True - Default) 

        Output     :    Images pages extracted from a tif file
        

        Descrption :    This function reads a string TIF file path and
                        converts it to a 300 dpi image per page
                        in the provided folder.

        Author     :    titus@stride

        DEV note   : Merge into extract_image_from_pdf function 
    """

    # Format output filename
    # Extract Filename

    temp_pdf_name = os.path.splitext(os.path.basename(temp_pdf_path))[0]

    convert_filename = temp_pdf_name + "." + PNG_TEXT
    convert_file_path = os.path.join(images_folder_path, convert_filename)

    logger.debug("current PDF pshr")
    logger.debug(temp_pdf_name)
    logger.debug(convert_file_path)

    # DPI limited to 300 to maximize quality: extraction time ratio.
    # 600 works best but adds significant overhead to documents with 100 + pages
    with Image(filename=temp_pdf_path, resolution=300) as img:
        # Set white background.

        img.alpha_channel = False
        img.background_color = Color("White")

        if "rgb" not in img.colorspace:
            img.transform_colorspace("srgb")

        with img.convert(PNG_TEXT) as converted:

            converted.alpha_channel = False
            converted.background_color = Color("White")
            converted.save(filename=convert_file_path)

    # Get List of files
    temp_image_names, temp_image_number = getDirList_sorted_int(
        images_folder_path, PNG_MODIFIER, False
    )
    # IF split files Rename them
    if is_file_split == False:

        for temp_image in temp_image_names:

            # Format new output filename
            image_src = temp_image
            image_dst = temp_image.replace(temp_pdf_name + "-", "")

            # Rename the file
            os.rename(image_src, image_dst)

    elif is_file_split == True:

        for temp_image in temp_image_names:
            
            # extract filename and directory
            temp_image_name, _, temp_image_path = extract_file_details_from_path(temp_image)
            # Extract outpiut filename
            # eg file-1-1.png -> 1.png
            temp_dst_name = temp_image_name[-5:]

            # Format new output filename
            image_src = temp_image
            image_dst = os.path.join(temp_image_path, temp_dst_name)

            # Rename the file
            os.rename(image_src, image_dst)


def extract_image_from_pdf_cmd(
    temp_pdf_path, images_folder_path, is_file_split=False, extract_image_from_pdf=True
):

    """
        Input      :    
                        String - abs path to PDF 
                        String - path to Images folder
                        Flag   - Page level processing True/False (True - Default) 

        Output     :    Images pages extracted from a tif file
        

        Descrption :    This function reads a string TIF file path and
                        converts it to a 300 dpi image per page.
                        in the provided folder.

        Author     :    titus@stride
        
    """

    # Format output filename
    # Extract Filename

    temp_pdf_name = os.path.splitext(os.path.basename(temp_pdf_path))[0]

    convert_filename = temp_pdf_name + "." + PNG_TEXT
    convert_file_path = os.path.join(images_folder_path, convert_filename)

    pdf_name = temp_pdf_path[0:-4]
    logger.debug("current PDF page")
    logger.debug(temp_pdf_name)
    # logger.debug(convert_file_path)

    input_file_name, input_file_extention, input_file_path = extract_file_details_from_path(
        convert_file_path
    )
    with open(temp_pdf_path, "rb") as f:
        pdf = PdfFileReader(f)
        page_limit = pdf.numPages
    i = range(0,page_limit)
    logger.info(f"max_workers={min(os.cpu_count(), page_limit)}")
    
    with ProcessPoolExecutor(max_workers=min(os.cpu_count(),page_limit)) as exe:
        exe.map(pdf_to_image, repeat(convert_file_path),repeat(is_file_split),repeat(temp_pdf_name),repeat(temp_pdf_path), i,repeat(images_folder_path))
        exe.shutdown()

    # with Image(filename=temp_pdf_path, resolution=600) as img:
    #     # Set white background.

    #     img.alpha_channel = False
    #     img.background_color = Color("White")

    #     if "rgb" not in img.colorspace:
    #         img.transform_colorspace("srgb")

    #     with img.convert(PNG_TEXT) as converted:

    #         converted.alpha_channel = False
    #         converted.background_color = Color("White")
    #         converted.save(filename=convert_file_path)

    # IF split files Rename them
    if is_file_split == False:
        # Get List of files
        temp_image_names, temp_image_number = getDirList_sorted_int(
            images_folder_path, PNG_MODIFIER, False
        )

        for temp_image in temp_image_names:

            # Format new output filename
            image_src = temp_image
            image_dst = temp_image.replace(temp_pdf_name + "-", "")

            # Rename the file
            os.rename(image_src, image_dst)

def pdf_to_image(convert_file_path, is_file_split, temp_pdf_name, temp_pdf_path, i, images_folder_path):
    try:
        image_output = convert_file_path[0:-4]

        command_to_call = "convert "
        path_to_pdf_inpuut = '"{}"'.format(temp_pdf_path)

        if is_file_split == False:

            output_image_name = temp_pdf_name + "-" + str(i) + ".png"
            image_output = os.path.join(images_folder_path, output_image_name)

            path_to_pdf_inpuut = path_to_pdf_inpuut + "[" + str(i) + "]"
            logger.debug(image_output)

        elif is_file_split == True:
            image_output = os.path.join(images_folder_path, temp_pdf_name + ".png")
            logger.debug(image_output)
            logger.debug(images_folder_path)

            # image_output = convert_file_path[0:-4]+".png"

        path_to_image_output = '"{}"'.format(image_output)

        command_to_call = (
            command_to_call
            + "-density 300 "
            + path_to_pdf_inpuut
            + " -quality 100 -alpha remove "
            + path_to_image_output
        )

        # Call the command to convert
        print (command_to_call)
        output_pdf_2_image = subprocess.check_output(command_to_call, shell=True)
        output_pdf_2_image = output_pdf_2_image.decode("utf-8")
        logger.debug(f"output_pdf_2_image {output_pdf_2_image}")
    except:
        logger.info("EOF reached |or| page cannot be converted")
        logger.debug(f"Page number: {str(i)}")

def extract_image_from_pdf(temp_pdf_path, images_folder_path, is_file_split=True):

    """
        Input      :    String - abs path to PDF 
                        String - path to Images folder
                        Flag   - Page level processing True/False (True - Default) 

        Output     :    Images pages extracted from a tif file
        

        Descrption :    This function reads a string TIF file path and
                        converts it to a 300 dpi image per page.
                        in the provided folder.

        Author     :    titus@stride
        
    """

    # Format output filename
    # Extract Filename

    temp_pdf_name = os.path.splitext(os.path.basename(temp_pdf_path))[0]

    convert_filename = temp_pdf_name + "." + PNG_TEXT
    convert_file_path = os.path.join(images_folder_path, convert_filename)

    logger.debug("current PDF pshr")
    logger.debug(temp_pdf_name)
    logger.debug(convert_file_path)

    with Image(filename=temp_pdf_path, resolution=600) as img:
        # Set white background.

        img.alpha_channel = False
        img.background_color = Color("White")

        if "rgb" not in img.colorspace:
            img.transform_colorspace("srgb")

        with img.convert(PNG_TEXT) as converted:

            converted.alpha_channel = False
            converted.background_color = Color("White")
            converted.save(filename=convert_file_path)

    # IF split files Rename them
    if is_file_split == False:
        # Get List of files
        temp_image_names, temp_image_number = getDirList_sorted_int(
            images_folder_path, PNG_MODIFIER, False
        )

        for temp_image in temp_image_names:

            # Format new output filename
            image_src = temp_image
            image_dst = temp_image.replace(temp_pdf_name + "-", "")

            # Rename the file
            os.rename(image_src, image_dst)


def images_to_tif(pdf_file, image_files):
    """gathers up images in a folder and generates a tif file with the same name as the provided 
        input pdf file

        Input       :   String path to image files, 
                        String output filename

        Returns     :  Boolean flag - to check if the file has been processed 
                        String path to the image file.

        Output      :  Single tif image file which consists of all the other files.


        
        Author      :   titus@stride
    """

    # Init defalt outputs
    image_files_processed = True
    output_merge_command = ""
    path_to_tif_image = ""

    input_file_name = os.path.basename(pdf_file)
    output_image_name = input_file_name.replace(PDF_MODIFIER, TIFF_MODIFIER)
    output_image_name = output_image_name.replace(PDF_MODIFIER, TIFF_MODIFIER)
    output_image_name = output_image_name.replace(TIFF_MODIFIER_CAPS, TIFF_MODIFIER)
    output_image_name = output_image_name.replace(" ", "_")
    path_to_image_output = os.path.join(image_files, output_image_name)

    # Create an input for invoking the needed function

    path_to_images_inpuut = os.path.join(image_files, PNG_WILD_MODIFIER)
    command_to_call = "convert "
    # path_to_images_inpuut = '"{}"'.format(path_to_images_inpuut)
    path_to_image_output = '"{}"'.format(path_to_image_output)
    path_to_sorted_input = "$(ls " + path_to_images_inpuut + " | sort -V)"
    
    # Dev command

    command_to_call = (
        command_to_call
        + path_to_sorted_input
        + " -quality 100 -density 300 -alpha remove "
        + path_to_image_output
    )
    command_to_call = command_to_call + " 2>/dev/null"

    logger.debug(path_to_sorted_input)
    logger.debug(command_to_call
    )

    try:

        # Call the command to tesseact to get the orientation information.
        # output_merge_command =

        subprocess.call(command_to_call, shell=True)

    except Exception as e:
        # Deskew command did not process sucessfully
        logger.error("Images->TIF Operation failed")
        logger.error(e)
        image_files_processed = False

    return image_files_processed, path_to_image_output


def attempt_denoise_image(orig_image):
    """
        Description :   This function Attemps to denoise the image using 
                        standard image filtering means.

        Input       :   CV2 Image

        Return      :   CV2 Image

        Author      :   Titus@stride
    """

    # Apply N1 means denoising
    denoised_image = cv2.fastNlMeansDenoising(orig_image, None, 20, 7, 21)

    return denoised_image


def blur_image(orig_image):
    """
        Input      :   c2 Image file

        Output     :   blurred cv2  Image file
        Descrption :   adds gausain blur to an image
        Author     :   titus@stride
    """
    blurred_image = cv2.GaussianBlur(orig_image, (5, 5), 0)

    return blurred_image

def threshold_image_otsu(orig_image):

    """
        Input      :   c2 Image file

        Output     :   Thresholded cv2  Image file
        Descrption :   adds gausain blur followed by thesholding via otsu
        Author     :   titus@stride
    """

    gaussianb_image = cv2.GaussianBlur(orig_image, (1, 1), 0)
    _, output_image = cv2.threshold(gaussianb_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return output_image

def background_negation(original_image):

    """
        Input      :   c2 Image file

        Output     :   cv2  Image file with no background
        Descrption :   removes the background from document images.

        Author     :   titus@stride
    """

    try:
        try:
            processed_image = convert_bgr_2_grayscale_image(original_image)
        except:
            processed_image = original_image
            pass 
        # Blur the image twice   
        processed_image = blur_image(processed_image)
        processed_image = blur_image(processed_image)

        # Enhance the text layer
        processed_image = enchance_image_text(processed_image)

        # Binerize the image using otsu
        processed_image = threshold_image_otsu(processed_image)

    except Exception as e:
        print(e)

    return processed_image


def extract_file_details_from_path(path_to_pdf_file):
    """ extracts filename, file extention and dir path to file from an abs path

    Args:
        path_to_ocr_input_file (str)      : abs path to input files

    Returns:
        file name (str)
        file extention (str)
        file directory (str)

    Author:
        titus@stride    
    """
    # Prepare Output filename
    input_file_name = os.path.basename(path_to_pdf_file)
    input_file_path = os.path.dirname(path_to_pdf_file)
    input_file_extention = input_file_name.split(".")[-1]

    return input_file_name, input_file_extention, input_file_path


def create_processing_dirs(path_from_platform):
    """ creates temp folders for image and pdf processing

    Args:
        path_from_platform (str)      : abs path to the working directory

    Returns:
        images_folder (str)   : path to where temp images will be stored
        pdfs_folder (str)     : path to where temp pdfs will be stored
        pdfs_ocr_folder (str) : path to where temp OCRized pds will be stored

    Author:
        titus@stride    
    """
    # define Directory Structre for processing
    images_folder = os.path.join(path_from_platform, PATH_TO_TEMP_IMAGES)
    pdfs_folder = os.path.join(path_from_platform, PATH_TO_TEMP_PDFS)
    pdfs_ocr_folder = os.path.join(path_from_platform, PATH_TO_TEMP_PDFS_OCRized)

    #   Create Images folder
    if not os.path.exists(images_folder):
        os.makedirs(images_folder)

    #   Create PDFs Folder
    if not os.path.exists(pdfs_ocr_folder):
        os.makedirs(pdfs_ocr_folder)

    return images_folder, pdfs_folder, pdfs_ocr_folder


def copy_input_image_for_processing(
    path_to_image_file, image_name, path_to_output_folder
):
    """ helper function to process the first stage of processing image files for OCRization
        aka copies files to the processing folder for now

    Args:
        path_to_image_file (str)      : abs path to the input file
        image_name (str)      : basename of the input file
        path_to_output_folder (str)      : abs path to the output folder

    Returns:
        path_to_output_image (str)   : abs path to the output file    

    Author:
        titus@stride    
    """

    # init output
    path_to_output_image = []

    # Format Output File
    path_to_output_image_name = path_to_image_file.replace(" ", "_")

    path_to_output_image = os.path.join(path_to_output_folder, image_name)
    try:
        # Copy the file
        shutil.copyfile(path_to_image_file, path_to_output_image)
        logger.debug("Image File Copied successfuly to temp folder")

    except Exception as e:
        logger.debug(e)
        logger.debug(path_to_image_file)
        logger.debug(path_to_output_image)
        logger.error("Image File NOT Copied successfuly to temp folder")

    return path_to_output_image


def fix_and_enhance_image_files_helper(
    images_folder,
    image_extention,
    is_preprocess_enable_flag,
    rotate_flag,
    luminfix_flag,
    denoise_flag,
    deskew_flag,
    enable_filers_flag,
    enable_superres,
):
    """ helper function to handle second stage processing (filtering, enhancement,etc)
         for  image file(s) in the images folder.

    Args:
        images_folder (str)           : abs path to the input folder containing image files
        image_extention (str)         : format of the input images in the image file.
        is_preprocess_enable_flag (bool)   : Flag set to process input files
        deskew_flag (bool)   :                 Flag to fix skew issues - Recommended / Default : True
        rotate_flag (bool)   :                 Flag to fix rotation issues: Default : False
        luminfix_flag(bool)  :                  Flag to fix lumination inconsistancies: Default : False
        denoise_flag (bool)   :                 Flag to denoise the image: Recommended / Default : True
        enable_filers_flag (bool)   :                 Flag to enable filtering|superresolution process: Recommended / Default : Truee
        enable_superres (bool)   :                 Flag to enable superresolution : Recommended / Default : True

    Returns:
        is_image_processing_complete(bool)  : True If file(s) have been processed sucessfully.

    Author:
        titus@stride    
    """
    # format vars
    is_image_processing_complete = False
    temp_image_names = ""
    temp_image_number = 0

    if "pdf" in image_extention.lower():
        temp_extention = "png"
    elif "tif" in image_extention.lower():
        temp_extention = "png"    
    else:
        temp_extention = image_extention    

    # Get list of images
    temp_image_names, temp_image_number = getDirList_sorted_int(
        images_folder, temp_extention, False
    )
    
    # Process the images if the flag is set.

    if is_preprocess_enable_flag:
        # Process the images return from the directory query.
        logger.info("Preprocessing Flag Enabled")
        time_start_image_preprocessing = time.time()
        pages = len(temp_image_names)
        with ProcessPoolExecutor(max_workers=min(os.cpu_count(),pages)) as exe:
            processing_status = exe.map(fix_and_enhance_images,
            temp_image_names,
            repeat(rotate_flag),
            repeat(luminfix_flag),
            repeat(denoise_flag),
            repeat(deskew_flag),
            repeat(enable_filers_flag),
            repeat(enable_superres))
            exe.shutdown()
        time_end_image_preprocessing = time.time()
        time_taken_image_preprocessing = (
            time_end_image_preprocessing - time_start_image_preprocessing
        )
        logger.debug(
            "Time Taken for Image Preprocessing %s", str(time_taken_image_preprocessing)
        )
        if(False in processing_status):
            is_image_processing_complete = False

    else:

        is_image_processing_complete = True

    return is_image_processing_complete


def process_and_ocr_file(
    path_to_pdf_file,
    path_from_platform,
    is_preprocess_enable_flag=True,
    deskew_flag=True,
    rotate_flag=True,
    luminfix_flag=True,
    denoise_flag=True,
    enable_filers_flag=True,
    enable_superres=True,
    is_pdf_splice_enabled=True,
    is_ocr_enabled=True,
    ocr_ip="35.240.152.215",
    ocr_language ="all"
):
    """
        Description :   This function calls the nessesary preprocessing scripts
                        and ocrizies the file.

                        Flag to enablee preproceessing operations: Default : True
                        Flag to fix skew issues - Recommended / Default : True
                        Flag to fix rotation issues: Default : False
                        Flag to denoise the image: Recommended / Default : True
                        Flag to enable filtering|superresolution process: Recommended / Default : Truee
                        Flag to enable superresolution : Recommended / Default : True
                        Flag to enable splitting pdf by page for processing : Recommended / Default : True
                        Flag to enable the OCR process : Recommended / Default : True
                        String ip address for ocr. 0.0.0.0 calls tesseract on the system.

        Input       :   path to PDF file (String)

        Return      :   path to ocrzd file(s) (String)
                        list of processed image(s) (list of String)

        Author      :   Titus@stride

    """
    # Get current working directory.
    cwd = os.getcwd()

    # Initialize  variables.

    appoved_exts = ["jpg", "gif", "jpeg", "png"]
    appoved_exts = ["jpg", "gif", "png"]

    # init flags
    is_conversion_successful = False
    is_image_input = False
    is_image_processing_complete = False
    is_image_2pdf_converted = False
    is_ocrization_successful = False

    # init temp working folders
    images_folder    = cwd
    pdfs_folder      = cwd
    pdfs_ocr_folder  = cwd

    # Init temp strings
    input_file_name       = ""
    input_file_extention  = "" 
    input_file_path       = ""
    input_extention_lower = ""
    path_to_ocr_input_file= ""


    # Temp timer inits
    time_start_pdf_to_images = 0
    time_end_pdf_to_images = 0
    time_taken_pdf_to_images = 0
    time_end_images_to_tif = 0
    time_taken_images_to_tif= 0

    time_start_images_to_tif = 0

    # Output formatting
    path_to_ocrzd_file       = "" 
    list_of_processed_images = []


    # Prepare temp processing folders
    images_folder, pdfs_folder, pdfs_ocr_folder = create_processing_dirs(
        path_from_platform
    )

    # Prepare Output filename
    input_file_name, input_file_extention, input_file_path = extract_file_details_from_path(
        path_to_pdf_file
    )

    # Set lowercase output Extention
    input_extention_lower = input_file_extention.lower()

    path_to_ocrzd_file = path_to_pdf_file.replace(
        "." + input_file_extention, PDF_MODIFIER_OCR
    )

    # # Debug loggers for init info
    logger.debug("==============================================")
    logger.debug("Path to File for conversion %s", path_to_pdf_file)
    logger.debug("Path to Final File after OCRization %s", path_to_ocrzd_file)
    logger.debug("Path to PDF Parts folder %s", pdfs_folder)
    logger.debug("PP flag Status %s", is_preprocess_enable_flag)
    logger.debug("Deskew flag Status  %s", deskew_flag)
    logger.debug("Rotation flag Status  %s", rotate_flag)
    logger.debug("Luminosity fix flag Status  %s", luminfix_flag)
    logger.debug("Denoise flag Status  %s", denoise_flag)
    logger.debug("Enable Filters flag Status  %s", enable_filers_flag)
    logger.debug("Enable Superres flag  Status   %s", enable_superres)
    logger.debug("PDF splice Status %s", is_pdf_splice_enabled)
    logger.debug("==============================================")


    # If PDF or TIF file do the following
    if input_extention_lower == PDF_TEXT or input_extention_lower == TIF_TEXT:

        logger.debug("Input file is either PDF or TIF")

        if input_extention_lower == PDF_TEXT :
            # Convert Input PDF to image (one per page)
            time_start_pdf_to_images = time.time()
        
            is_conversion_successful = document_2_image_pages(
                path_to_pdf_file, images_folder, pdfs_folder, is_pdf_splice_enabled
            )
        elif input_extention_lower == TIF_TEXT:
            is_conversion_successful = document_2_image_pages(
                path_to_pdf_file, images_folder, pdfs_folder, True
            )

        time_end_pdf_to_images = time.time()
        time_taken_pdf_to_images = time_end_pdf_to_images - time_start_pdf_to_images

        logger.info("Document ->Parts Conversion Complete: %s", str(is_conversion_successful))
        logger.debug(
            "Time Taken for Document ->Parts Conversion %s", str(time_taken_pdf_to_images)
        )

    # If image input file
    elif input_extention_lower in appoved_exts:

        # Set variables and falgs
        is_image_input = True

        # Copy the file to the Images subfolder
        path_to_ocr_input_file = copy_input_image_for_processing(
            path_to_pdf_file, input_file_name, images_folder
        )

    # IF not Image or PDF file

    else:
        logger.error("Filetype Not supported for OCR")

    # Process file
    # If the conversion was sucessfull processes the extracted images
    if is_conversion_successful == True or is_image_input == True:

        # Process image files
        is_image_processing_complete = fix_and_enhance_image_files_helper(
            images_folder,
            input_extention_lower,
            is_preprocess_enable_flag,
            rotate_flag,
            luminfix_flag,
            denoise_flag,
            deskew_flag,
            enable_filers_flag,
            enable_superres,
        )
        logger.info("Parts Processing Complete: %s", str(is_image_processing_complete))


        if is_pdf_splice_enabled is False and is_image_input is False:

            # Converted the processed images to a single PDF
            path_to_ocr_input_file = os.path.join(images_folder, input_file_name)

            # format Input - > PDF - > TIF change
            path_to_ocr_input_file = path_to_ocr_input_file.replace(
                "." + input_file_extention, TIFF_MODIFIER
            )

            time_start_images_to_tif = time.time()

            is_image_2pdf_converted, path_to_tif_image = images_to_tif(
                path_to_ocr_input_file, images_folder
            )

            time_end_images_to_tif = time.time()
            time_taken_images_to_tif = time_end_images_to_tif - time_start_images_to_tif
            logger.debug("Time Taken for Images -> TIF %s", str(time_taken_images_to_tif))

            logger.info(
                "Parts-> Single Conversion Complete: %s", str(is_image_2pdf_converted)
            )

            path_to_ocr_input_file = path_to_tif_image.replace('"', "")


        # Send files to the Stride OCR at the IP addresss specififed in constants if enabled.
        if is_ocr_enabled is True:
            pass

        # IF OCR is disabled output the appropriate output based on flags        
        elif is_ocr_enabled is False:
            # Maybe add a  redundant type check
            pass

            list_of_processed_images = return_processed_images(is_pdf_splice_enabled, images_folder, path_to_ocr_input_file)

    # If the conversion was unsucessfull, send empty stuff
    elif is_conversion_successful is False and is_image_input is False:
        logger.error("Image-> PDF Conversion Failed")
        path_to_ocrzd_file = path_to_pdf_file

    return path_to_ocrzd_file, list_of_processed_images

def return_processed_images(is_pdf_splice_enabled, images_folder, path_to_ocr_input_file):
    """ helper function to return processed image(s).

    Args:
        path_to_ocr_input_file (str)            : abs path to the input file (copied to temp folder)
        images_folder                     : folder of images
        is_pdf_splice_enabled (bool)      : if pdf->pdf pages has been enabled

    Returns:
        path_to_output_files (str)        : list of file(s) [abs paths in str]

    Author:
        titus@stride    
    """

    # init variables
    path_to_output_files = []
    temp_image_names     = []
    temp_image_number   = 0


    # if page level processing is enabled return the list of
    # processed Image PNG pages.
    if is_pdf_splice_enabled is True:

        # Get list of processed | Extracted Images


        temp_image_names, temp_image_number = getDirList_sorted_int(
            images_folder, PNG_MODIFIER
        )

        # Retuns list of OCRized extracted image paths.
        path_to_output_files = temp_image_names

    # if page level processing is disabled return the processed
    # TIF file
    elif is_pdf_splice_enabled is False:

        path_to_output_files = [path_to_ocr_input_file]

    return path_to_output_files

def detect_language(tiff_path):
    """
        Input      :   String path to combined tiff image

        Returns     :   language detected in the image 
                        


        Descrption :    This function reads a string filename, and returns the language detected in the document
        Author     :   mohit@stride
    """

    # Init defalt outputs
    script_processed = True
    output_rotate_command = ""
    script_status = "0"
    lang_name = "all"
    # Create an input for invoking the needed function
    command_to_call = "tesseract --psm 0 -l osd "
    path_to_image = '"{}"'.format(tiff_path)
    command_to_call = command_to_call + path_to_image
    command_to_call = command_to_call + " -"
    command_to_call = command_to_call + " 2>/dev/null"
    logger.info(f"Script command called: {command_to_call}")

    try:

        # Call the command to tesseact to get the orientation information.
        output_rotate_command = subprocess.check_output(command_to_call, shell=True)
        output_rotate_command = output_rotate_command.decode("utf-8")

        # Format output
        rotate_status = output_rotate_command.split("\n")

        for line_rs in rotate_status:
            script_line = line_rs.split(" ")
            if script_line[0] == "Script:":
                script_name = script_line[1]
                if script_name in mappings:
                    lang_name = mappings[script_name]
                break

    except Exception as e:
        # Rotation command did not process sucessfully
        # can happen if there is not enough text for tesseract
        logger.error("Script checking failed")
        logger.error(e)
        script_processed = False
        rotate_status = "0"

    return lang_name, script_processed



if __name__ == "__main__":

    platform_path = "."
    cwd = os.getcwd()
    path_to_files = os.path.join(cwd, "test_files")

    # path_to_files = cwd
    list_of_pdfs = os.listdir(path_to_files)

    list_of_pdfs.sort()
    for pdf_file in list_of_pdfs:

        # if pdf_file == "G & S.pdf":
        # if pdf_file == "3.png":
        # if  pdf_file == "t1.pdf":
        if  pdf_file == "t1.tif":

            print(pdf_file)
            temp_path = os.path.join(cwd, "temp")
            if not os.path.exists(temp_path):
                os.makedirs(temp_path)

            if os.path.exists(temp_path):
                shutil.rmtree(temp_path, ignore_errors=True)
                print("temp fodler found and removedremoved")

            path_to_pdf = os.path.join(path_to_files, pdf_file)

            path_to_ocrzd_file = path_to_pdf.replace(PDF_MODIFIER, PDF_MODIFIER_OCR)

            print("Starting Process")
            print(path_to_ocrzd_file)
            print("Filename", pdf_file)
            print("Path to Files:", path_to_files)
            print("Path to PDF:", path_to_pdf)
            print("Path to OCRzd:", path_to_ocrzd_file)

            print("=======================================")
            # if not os.path.exists(path_to_ocrzd_file):

            start_time = time.time()
            """
            def process_and_ocr_file(
                path_to_pdf_file,
                path_from_platform,
                is_preprocess_enable_flag=True,
                deskew_flag=True,
                rotate_flag=True,
                luminfix_flag=True,
                denoise_flag=True,
                enable_filers_flag=True,
                enable_superres=True,
                is_pdf_splice_enabled=True,
                is_ocr_enabled = True,
                ocr_ip="35.240.152.215",
            )
            """
            
            _ = process_and_ocr_file(
                path_to_pdf,
                cwd,
                True,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
                "0.0.0.0"
                "all"
            )

            end_time = time.time()
            tots_time = end_time - start_time
            tots_time = tots_time / 60
            print("Total time taken: ", tots_time)
            print("=======================================")
