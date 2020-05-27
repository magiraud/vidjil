

import requests
import glob
import sys
import os.path
try:
    from urllib.parse import *
except:
    from urlparse import urlparse    
import re
from collections import defaultdict

DEFAULT_FILES = glob.glob('../site/*/*.html')

BASE_PATH = '../site/'

REGEX_HREF = re.compile('href="(.*?)"')
REGEX_ID = re.compile('id="(.*?)"')

STATUS = {
    None: '? ',
    False: 'KO',
    True: 'ok'
}

USER_AGENT = {'User-Agent': 'Mozilla/5.0'}

stats = defaultdict(int)
failed = []

def check_url(url, ids=[], dirname=''):

    # Internal links
    if url.startswith('#'):
        return (not url[1:]) or (url[1:] in ids)


    # Relative links
    if not url.startswith('http'):
        # Anchors in relative links - TODO
        if '#' in url:
            return None
        ff = os.path.join(BASE_PATH if url.startswith('/') else dirname, url)
        return os.path.exists(ff)

    # External http(s) links
    try:
        req = requests.get(url, headers = USER_AGENT)
        return (req.status_code < 400)
    except:
        return False
    

def check_file(f):
    print('<-- ', f)
    dirname = os.path.dirname(f)
    content = ''.join(open(f).readlines())

    ids = REGEX_ID.findall(content)

    for url in REGEX_HREF.findall(content):
        ok = check_url(url, ids, dirname)
        print(STATUS[ok] + '    ' + url)
        globals()['stats'][ok] += 1
        if ok == False:
            failed.append(url)
    print()


def print_stats():
    print('==== Summary')
    for k, v in STATUS.items():
        print('  %s : %3d' % (v, globals()['stats'][k]))

    if globals()['stats'][False]:
        print('==== Failed')
        for f in failed:
            print('  ' + f)
    
if __name__ == '__main__':

    files = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_FILES

    for f in files:
        check_file(f)
    print_stats()

    if globals()['stats'][False]:
        sys.exit(1)
