#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import requests
import os.path
from urllib.parse import urlsplit
from datetime import datetime
import json
import re
import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        prog="Patreon RSS link extractor",
        description="Compile download links in a list for aria2c"
    )
    parser.add_argument('rss_url')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-m', '--rename-missing', action='store_const', const='missing', dest='rename')
    group.add_argument('-a', '--rename-all', action='store_const', const='all', dest='rename')
    group.add_argument('-s', '--skip-rename', action='store_const', const='skip', dest='rename')
    parser.set_defaults(rename='missing')
    return parser.parse_args()


def get_url(f, item):
    return item.find('enclosure').attrib['url']  

    
def get_title(f, item):
    return item.find('title').text

   
def write_new_names(f, item):
    date_str = item.find('pubDate').text
    dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
    date = dt.strftime("%Y-%m-%d")
    #print(' out="' + date + ' ' + title + file_ext + '"' + '\n')
    safe_title = sanitize(get_title(f, item))
    file_ext = os.path.splitext(urlsplit(get_url(f, item)).path)[1]
    filename = '[' + date + '] ' + safe_title + file_ext
    f.write(' out=' + filename + '\n')
    return filename
    
    
def sanitize(title):
    safe = title.encode('ascii', 'ignore').decode()
    # replace colons with dash for legibility
    safe = safe.replace(': ', ' - ')
    # remove disallowed characters for windows
    safe = re.sub(r'[<>:"/\\|?*]', '', safe)
    # remove leading/trailing whitespace
    return safe.strip()
    

def main():
    args = parse_args()
    
    if not os.path.isfile('feed.xml'):
        response = requests.get(args.rss_url)
        with open('feed.xml', 'wb') as f:
            f.write(response.content)
    
    with open('feed.xml', 'rb') as f:
        tree_root = ET.parse(f).getroot()
   
    fixed_names = []
   
    with open('urls.txt', 'w') as f:
        for item in tree_root.findall('channel/item'):
            title = get_title(f, item)
            url = get_url(f, item)
            f.write(url + '\n')        
            
            response = requests.head(url, allow_redirects=True)  
            missing_filename = (
                'Content-Disposition' not in response.headers
                or 'filename' not in response.headers['Content-Disposition']
            )
            
            # If no filename in header, make one (to avoid "1.mp3")
            if (args.rename == 'missing' and missing_filename) or args.rename == 'all':
                filename = write_new_names(f, item)                             
                fixed_names.append(filename)
                print("_FIXED:_", filename)
                           
            print("DONE:", title)
            
    print("Fixed", len(fixed_names), "filenames and prepared them for aria2c")
    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
