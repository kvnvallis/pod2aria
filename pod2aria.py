#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import requests
from requests.exceptions import RequestException
import os.path
from urllib.parse import urlsplit
from datetime import datetime
import json
import re
import argparse
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        prog="Pod2Aria",
        description="Compile download links from a podcast rss feed into a list for aria2c. Optionally construct filenames from episode title and publication date. Useful for patreon feeds where the filename is obscured and sometimes downloads as 1.mp3"
    )
    parser.add_argument('feed',
        help="A url for the rss feed, or a local xml file")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-m', '--rename-missing', action='store_const', const='missing', dest='rename',
        help="(Patreon) Construct new filenames missing from header")
    group.add_argument('-a', '--rename-all', action='store_const', const='all', dest='rename',
        help="Construct new filenames for every file")
    group.add_argument('-s', '--skip-rename', action='store_const', const='skip', dest='rename',
        help="Keep all original filenames")
    parser.add_argument('-o', '--output-file', default='urls.txt', help="file for saving the final list of urls")
    parser.add_argument('-t', '--podcast', help="Include name of podcast in every renamed file")
    parser.set_defaults(rename='skip')
    return parser.parse_args()


def get_url(item):
    return item.find('enclosure').attrib['url']


def get_title(item):
    return item.find('title').text


def write_new_names(f, item, podname=None):
    filename = ''
    if podname:
        filename = sanitize(podname) + ' '
    date_str = item.find('pubDate').text
    dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
    date = dt.strftime("%Y-%m-%d")
    safe_title = sanitize(get_title(item))
    file_ext = os.path.splitext(urlsplit(get_url(item)).path)[1]
    filename = filename + f'[{date}] {safe_title}{file_ext}'
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


def xml_from_url(path):
    response = requests.get(path)
    tree_root = ET.fromstring(response.content)
    return tree_root


def xml_from_file(path):
    with open(path, 'rb') as f:
        tree_root = ET.parse(f).getroot()
    return tree_root


def main():
    args = parse_args()

    if (args.feed.startswith("http://")
    or args.feed.startswith("https://")):
        try:
            tree_root = xml_from_url(args.feed)
        except (RequestException, ET.ParseError):
            print("Error: Failed to get an rss feed from the provided url")
            sys.exit(1)
    elif os.path.isfile(args.feed):
        try:
            tree_root = xml_from_file(args.feed)
        except ET.ParseError:
            print("Error: Failed to parse rss feed from", args.feed)
            sys.exit(1)
    else:
        print("Error: RSS feed is not a valid url or existing file")
        sys.exit(1)

    with open(args.output_file, 'w') as f:
        for item in tree_root.findall('channel/item'):
            title = get_title(item)
            url = get_url(item)
            f.write(url + '\n')

            if args.rename == 'missing':
                try:
                    response = requests.head(url, allow_redirects=True)
                except RequestException:
                    print(f'Warning: No response for title "{title}"')
                    # if there is no response, that means you can't check for a missing filename in the header. So skip the check, and assume the filename is missing
                    missing_filename = True
                    response = None

                if response != None:
                    missing_filename = (
                        'Content-Disposition' not in response.headers
                        or 'filename' not in response.headers['Content-Disposition']
                    )

            # If no filename in header, make one (to avoid "1.mp3")
            if (args.rename == 'missing' and missing_filename) or args.rename == 'all':
                filename = write_new_names(f, item, args.podcast)
                new_names.append(filename)
                print("_RENAMED:_", filename)

            print("DONE:", title)

    print("Download your files with:")
    print('\t' + f'aria2c -i "{args.output_file}"')


# store outside of main() so they can be accessed after a keyboard interrupt
new_names = []

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted by user')
    except OSError as e:
        print(f"Failed to open a file - {e}")
    finally:
        print("New filenames created:", len(new_names))

