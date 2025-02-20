#! /usr/bin/python3
import urllib.request
import urllib.error
import json
import re
import os
import sys
import time

scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
jsonPath = '/tmp/'
url = "https://www.suse.com/support/kb/doc/?id=000019587"
kernelLists = {}

try:
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',  # Realistic User-Agent
            # 'Referer': 'https://www.suse.com/'  # Uncomment if needed, replace with actual referer
        }
    )

    with urllib.request.urlopen(req) as response:
        rawData = response.read().decode('utf-8')
        print("Successfully retrieved data.")
        # print(rawData)  # Uncomment for full content (can be very long!)

        itemsList = re.findall(
            r"(?:(?:[0-9]+)(?:\.))+(?:(?:[0-9]+)(?:\-)(?:[0-9]+))(?:(?:\.)?(?:[0-9]+)?)+|>SLE[S]?(?:\s)?[0-9]+(?:\sSP[0-9])?(?:\s\-\sLTSS)?(?:[a-zA-Z0-9\-]+)?",
            rawData
        )
        # print("itemsList:", itemsList)  # debug to check if regex is working

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
                    print(f"An unexpected error occurred: {e} for {url}")
                    quit()

        with open('%s/kernel_versions.json' % jsonPath, 'w') as document:
            try:
                document.write(json.dumps(kernelLists))
            except Exception as e:
                print(f"Something went wrong.. Unable to write a kernel_versions.json file: {e}")
                quit()

        print("Json data collected.")

except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.reason} for {url}")
    print("Headers sent:")
    for key, value in req.headers.items():
        print(f"{key}: {value}")
    quit()
except urllib.error.URLError as e:
    print(f"URL Error: {e.reason} for {url}")
    quit()
except Exception as e:
    print(f"An unexpected error occurred: {e} for {url}")
    quit()
