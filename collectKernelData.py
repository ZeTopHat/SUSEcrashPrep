#! /usr/bin/python3
"""
collectKernelData.py is a script designed to scrape kernel version information from a specified URL, extract the relevant data using regular expressions, and save the collected kernel version data into a JSON file.
"""
import urllib.request
import urllib.error
import json
import re
import os
import sys

scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
JSONPATH = '/tmp/'
URL = "https://ziu.nue.suse.com/dm/TID.php?tid=000019587"
kernelLists = {}

try:
    req = urllib.request.Request(
        URL,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',  # Realistic User-Agent
            # 'Referer': 'https://www.suse.com/'  # Uncomment if needed, replace with actual referer
        }
    )

    with urllib.request.urlopen(req) as response:
        rawData = response.read().decode('utf-8')
        print("Successfully retrieved data.")
        #print(rawData)  # Uncomment for full content (can be very long!)

        itemsList = re.findall(
            r"(?:(?:[0-9]+)(?:\.))+(?:(?:[0-9]+)(?:\-)(?:[0-9]+))(?:(?:\.)?(?:[0-9]+)?)+|>SLE[S]?(?:\s)?[0-9]+(?:\.)?(?:\sSP[0-9])?(?:\s\-\sLTSS)?(?:[a-zA-Z0-9\-]+)?",
            rawData
        )
        #print("itemsList:", itemsList)  # debug to check if regex is working

        for number, item in enumerate(itemsList):
            itemsList[number] = re.sub(">", "", item)

        for item in itemsList:
            if "S" in item:
                key = item
                kernelLists[item] = []
            else:
                try:
                    kernelLists[key].append(item)
                except KeyError:  # Catch the specific error
                    print(f"KeyError: Key '{key}' not found.  itemsList may not be properly structured. Check the regex or the website structure.")
                    print("Dumping kernelLists for inspection:", kernelLists)
                    quit()
                except Exception as e:
                    print(f"An unexpected error occurred: {e} for {URL}")
                    quit()

        output_path = os.path.join(JSONPATH, 'kernel_versions.json')
        try:
            with open(output_path, 'w', encoding='utf-8') as document:
                json.dump(kernelLists, document, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Something went wrong.. Unable to write a kernel_versions.json file: {e}")
            quit()

        print("Json data collected.")

except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.reason} for {URL}")
    print("Headers sent:")
    for key, value in req.headers.items():
        print(f"{key}: {value}")
    quit()
except urllib.error.URLError as e:
    print(f"URL Error: {e.reason} for {URL}")
    quit()
except Exception as e:
    print(f"An unexpected error occurred: {e} for {URL}")
    quit()
