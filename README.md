# Stride Demo OCR

## Current Version 
3.0

## API usage instructions

https://strideai.atlassian.net/wiki/spaces/DO/pages/5079580/OCR+API+Integration

## Installation instructions for dependenceies

## Install python depenecies
```
pip install -r ./installation_files/requirements.txt
pip install -r ./installation_files/pdfrw-0.4-py2.py3-none-any.whl
```

### Instructions to install Tesseract 5.x:

For installing tesseract on Ubuntu 18.X run the following

- Ubuntu
```
Ubuntu
sudo add-apt-repository ppa:alex-p/tesseract-ocr-devel
sudo apt-get update
sudo apt install tesseract-ocr
sudo apt install libtesseract-dev
```


Verify tesseract Installation is up to date by running the following:

*tesseract -v*
Output should look similar to below:
```
tesseract 5.0.0-alpha-820-ge20f
 leptonica-1.78.0
  libgif 5.1.4 : libjpeg 8d (libjpeg-turbo 1.5.2) : libpng 1.6.34 : libtiff 4.0.9 : zlib 1.2.11 : libwebp 0.6.1 : libopenjp2 2.3.0
 Found AVX512BW
 Found AVX512F
 Found AVX2
 Found AVX
 Found FMA
 Found SSE
 Found OpenMP 201511
 Found libarchive 3.2.2 zlib/1.2.11 liblzma/5.2.2 bz2lib/1.0.6 liblz4/1.7.1

```

Please make sure that the tesseract is using 4.x+.Not  3.X. If so, redo installation steps or consult the link in below.

The same applies for leptonica. This has to be 1.78.0 +


Additional supported OS installation isntructions can be found below:
```
https://github.com/tesseract-ocr/tesseract/wiki
```

Download additional tessercat langauges using the script below
```
import requests

lang = {
    'en': 'eng',
    'ar': 'ara',
    'da': 'dan',
    'nl': 'nld',
    'de': 'deu',
    'fr': 'fra',
    'is': 'isl',
    'no': 'nor',
    'pl': 'pol',
    'it': 'ita',
    'es': 'spa',
    'pt': 'por'
}

def download_file(link, file_path, connection_timeout=10):
    try:
        r = requests.get(link, stream = True, timeout=(connection_timeout, 90), verify=False)
        for chunk in r.iter_content(32):
            file_path.write(chunk)
    except:
        try:
            r = requests.get(link, timeout=(
                connection_timeout, 90), verify=False)
            with open(file_path, 'wb+') as destination:
                destination.write(r.content)

        except:
            pass


if __name__ == '__main__':
    lang_input  = input("enter the language code -  ")

    if lang_input in lang:
        link_data = 'https://github.com/tesseract-ocr/tessdata_fast/raw/master/'+lang[lang_input]+'.traineddata'
        print(link_data)
        file_path = "/home/sneha/Documents/Stride/Titus/language_documents/download"
        download_file(link_data, file_path, 50)
```
The language files have to be in the path for your envorinment (dev or demo) which is defined in `constants.py`

- RedHat

Install tesseract 5 from

https://build.opensuse.org/project/show/home:Alexander_Pozdnyakov:tesseract5


### ImageMagick Installation Instructions

Install 'Imagemagick' by running  the following : 
```
apt-get install imagemagick
```
Ensure that Imagemaick has the apporpriate permissions for processing pdf files by doing the following:
You may need sudo permission.
```
nano /etc/Imagemagick-6/policy.xml
```

Add or edit the following entry
```
<policy domain="coder" rights="read|write" pattern="PDF" />
```

## Instructions for using Stride OCR as a Devoloper

### Server Setup for DEV


```
git clone https://github.com/strideai/demo-ocr/
cd demo_ocr
python manage.py runserver 0.0.0.0:8889
```


Change path to langauge files in `constants.py`
comment out the path that does not apply.



http://ip:8889 will allow you to access the landing page for the stride OCR.

Ensure that the port is open (talk to DevOps) as well.


### Install and start redis-server

```
 sudo apt-get update
 sudo apt-get upgrade
 sudo apt-get install redis-server
 sudo service redis-server restart
```


### Start the Redis Queues

There are 2 RQs per document. One for the OCR and one for preprocessing.
Be sure to make sure that there are 2x docments running per document you want to run in parallel.

Each OCR worker requires 4 cores. So change the number of workers depending on this.
eg:- 16 cores - upto 4 workers

This is important as not having sufficent cores will lead to performance degradation.

```
supervisord -c supervisor_ocr.conf

```

To see RQ status:
```
supervisorctl -c supervisor_ocr.conf status
```

To stop the RQ:
```
supervisorctl -c supervisor_ocr.conf stop all
```

IF you get any backoff or fatal errors on the status command,
then run the following and run the first two commands

```
supervisorctl -c supervisor_ocr.conf stutdown
```

RQ dashboard
```
rq-dashboard -D1
```

If you want to change the number of workers,

change numprocs in the supervisor.conf file. Then do the following

```
 supervisorctl -c supervisor_ocr.conf update

```


### Test OCR Install
Change up IP_ADDRESS_SERVER in the file below to the ip address in the pervious section
eg :- "x.x.x.x:8889"

```
python -m pytest test_cases_ocr.py -vv
```


if you need to debug or have string output,
```
python -m pytest test_cases_ocr.py -s
```
### Access the OCR

access_ocr_example.py has a function you can use to interact with the server. 
If Token doesnt work, talk to DevOps.

## Instructions Deploying the Stride OCR


# Solutions for commonly encountered errors.
Q: Compling tesseract from souce or if Tesseract fails to work

Ans: copy *pdf.ttf* in installation_files to */usr/local/share/tessdata/*

Q. Image Magick or "convert " Doesnt work? 

Ans: Modify policy.xml like outlined in the intsallation instructions

Q.cannot find ximgproc error on new production error?

Ans: Uninstall opencv-python and retain opencv-contrib. Ensure only opencv-contrib in installed. 

Q: When running python mange.py runserver you get the following error - "from .cv2 import *ImportError: libSM.so.6:" 

Ans: sudo apt-get install libsm6 libxrender1 libfontconfig1

Q: When running supervisord -c supervisor_ocr.conf you get "Command 'supervisord' not found, but can be installed with: "

Ans: sudo apt-get install supervisor

Q. Question not covered here?

Ans : look at https://github.com/tesseract-ocr/tesseract/wiki/FAQ or https://github.com/tesseract-ocr/tesseract/wiki/FAQ-Old



## Running RQ workers
Use the supervisor_ocr.conf file to start the woerks.

Alternatively, you can start the worker directly using the command `python rq_workers/ocr_worker.py` from the project root directory.
Do the same for the ocr_preprocess worker as well.

