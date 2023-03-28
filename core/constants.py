QUEUE_STATUS = (
    ("queued", "queued"),
    ("processing", "processing"),
    ("failed", "failed"),
    ("completed", "completed"),
)

PNG_MODIFIER = ".png"
PNG_TEXT = "png"
PNG_WILD_MODIFIER = "*.png"
PDF_MODIFIER = ".pdf"
PDF_TEXT = "pdf"
TIFF_MODIFIER = ".tif"
TIFF_MODIFIER_CAPS = ".TIF"
TIF_TEXT = "tif"
PDF_MODIFIER_OCR = "_OCRized"
PATH_TO_TEMP_IMAGES = "temp/images/"
PATH_TO_TEMP_PDFS = "temp/pdfs/"
PATH_TO_TEMP_PDFS_OCRized = "temp/pdfs/OCR/"
PATH_TO_TEMP_FOLDER = "temp/"

CONTAINER_FILES = ["tif", "pdf"]
IMAGE_FILES = ["png", "jpg", "jpeg"]

PDF_PAGE_LIMIT = 500

OCR_SUPPORTED_LANGS = {
    "en": "eng",
    "ar": "ara",
    "ch": "chi_sim",
    "da": "dan",
    "nl": "nld",
    "de": "deu",
    "fr": "fra",
    "is": "isl",
    "no": "nor",
    "pl": "pol",
    "it": "ita",
    "es": "spa",
    "pt": "por",
    "lat": "lat"
}

ocr_ip = "0.0.0.0"

# Dev
TESS_DATA_DIR = "/usr/share/tesseract-ocr/5/tessdata/"

# Prod
# TESS_DATA_DIR = "/home/stride/.local/share/tessdata"



# Tessercat Parameters

TESS_CMD_HEAD = "tesseract "
TESS_PARMS = " --psm 1 --oem 1 pdf"
TESS_PARMS_OPT = " --dpi 300"
TESS_DATA_DIR_CMD =  " --tessdata-dir  "

