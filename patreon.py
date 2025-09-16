#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import requests
import os.path
from urllib.parse import urlsplit
from datetime import datetime
import json
import re

def main():
    url = ''
    if not os.path.isfile('feed.xml'):
        response = requests.get(url)
        with open('feed.xml', 'wb') as f:
            f.write(response.content)
    
    with open('feed.xml', 'rb') as f:
        tree_root = ET.parse(f).getroot()
   
    fixed_names = []
   
    with open('urls.txt', 'w') as f:
        for item in tree_root.findall('channel/item'):
            title = item.find('title').text
            url = item.find('enclosure').attrib['url']
            file_ext = os.path.splitext(urlsplit(url).path)[1]
            f.write(url + '\n')           
            response = requests.head(url, allow_redirects=True)   
            
            if not 'Content-Disposition' in response.headers \
            or not 'filename' in response.headers['Content-Disposition']:
                date_str = item.find('pubDate').text
                dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
                date = dt.strftime("%Y-%m-%d")
                #print(' out="' + date + ' ' + title + file_ext + '"' + '\n')
                safe_title = title.encode('ascii', 'ignore').decode()
                # replace colons with dash for legibility
                safe_title = safe_title.replace(': ', ' - ')
                # remove disallowed characters for windows
                safe_title = re.sub(r'[<>:"/\\|?*]', '', safe_title)
                # remove leading/trailing whitespace
                safe_title = safe_title.strip()
                filename = date + '_' + safe_title + file_ext
                print("FIXED:", filename)
                f.write(' out=' + filename + '\n')
                fixed_names.append(filename)
                            
            print("DONE:", title)
            
    print("Fixed", len(fixed_names), "filenames and prepared them for aria2c")
    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
