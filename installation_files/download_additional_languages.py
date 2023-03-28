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

    for lang_input in lang:
        link_data = 'https://github.com/tesseract-ocr/tessdata_fast/raw/master/'+lang[lang_input]+'.traineddata'
        print(link_data)
        file_path = "./installation_files/add_langs/"
        download_file(link_data, file_path, 50)