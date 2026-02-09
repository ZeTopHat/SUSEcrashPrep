#! /usr/bin/python3
"""
crashPrep downloads and extracts the necessary files for crash analysis of a specified kernel. It uses the kernel version to determine the appropriate URLs for downloading the debug and source RPMs, as well as the base kernel RPM if requested. The script can also extract the downloaded RPMs to prepare for crash analysis.
"""
import os
import glob
import sys
import time
import json
import re
import subprocess
import shutil
import argparse
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

# argument parsing module
parser = argparse.ArgumentParser(description='Download files for core analysis.')
parser.add_argument('kernelVersion', nargs=1, metavar='kernel', help='Kernel version to use.')
parser.add_argument('-a', '--arch', nargs=1, metavar='architecture', help='Architecture to use. (defaults to x86_64)', default=['x86_64'], dest='architecture')
parser.add_argument('-b', '--base', help='If included, will also download the kernel-default-base', action='store_true')
parser.add_argument('-e', '--extraction', help='If included, will also extract the downloaded rpm files.', action='store_true')
parser.add_argument('-f', '--flavor', nargs=1, metavar='flavor', help='Flavor to use. (defaults to default)', default=['default'], dest='flavor')
args = parser.parse_args()

# python wget module is not always installed
try:
  import wget
except ImportError:
  print("Something went wrong.. Is the wget python module installed? Try 'sudo pip install wget'.")
  quit()

# vars to later make accessible via conf file
smtserver = "collective.suse.cloud/repo/smt"
smtserverbackup = "updates.suse.de"

# starting vars
scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
jsonPath = '/tmp'
currentTime = time.time()
kernelLists = {}
osVersion = ''
osRepo3 = ''
poolKernel = False
era = "Updates"
canDownload = False

# create a new kernel_versions.json file if it doesn't exist or is older than a day old
if os.path.exists(f"{jsonPath}/kernel_versions.json"):
  lastModifiedTime = os.path.getmtime(f"{jsonPath}/kernel_versions.json")
  if (currentTime - lastModifiedTime) // (24 * 3600) >= 1:
    import collectKernelData
else:
  import collectKernelData

# simple loop to convert -default to .1
if '-default' in args.kernelVersion[0]:
  print('Converting "-default" to ".1" to match full kernel versions. If true kernel version uses .2, .3, etc the kernel may not be found.')
  args.kernelVersion[0] = re.sub("-default", ".1", args.kernelVersion[0])

# function to assemble the urls
def urlAssemble(packageType, fileName):
  """Assemble the URL for the given package type and file name based on the OS version and other parameters."""
  if packageType == "info" or packageType == "source":
    if '10' in osVersion or '11' in osVersion:
      url_primary = 'http://{0}/$RCE/{1}-Debuginfo-{2}/{3}-{4}/rpm/{4}/{5}'.format(smtserver, osRepo1, era, osRepo2, args.architecture[0], fileName)
      url_backup = 'http://{0}/$RCE/{1}-Debuginfo-{2}/{3}-{4}/rpm/{4}/{5}'.format(smtserverbackup, osRepo1, era, osRepo2, args.architecture[0], fileName)
    elif '12' in osVersion or '15' in osVersion or '16' in osVersion:
      url_primary = 'http://{0}/SUSE/{1}/{2}/{3}/{4}/{5}_debug/{4}/{6}'.format(smtserver, era, osRepo2, osRepo1, args.architecture[0], era.lower()[:-1], fileName)
      url_backup = 'http://{0}/SUSE/{1}/{2}/{3}/{4}/{5}_debug/{4}/{6}'.format(smtserverbackup, era, osRepo2, osRepo1, args.architecture[0], era.lower()[:-1], fileName)
      if 'LTSS' in osVersion:
        url_primary = 'http://{0}/SUSE/{1}/{2}/{3}{4}/{5}/{6}_debug/{5}/{7}'.format(smtserver, era, osRepo2, osRepo1, "-LTSS", args.architecture[0], era.lower()[:-1], fileName)
        url_backup = 'http://{0}/SUSE/{1}/{2}/{3}{4}/{5}/{6}_debug/{5}/{7}'.format(smtserverbackup, era, osRepo2, osRepo1, "-LTSS", args.architecture[0], era.lower()[:-1], fileName)
    else:
      print("This version is not known: " + osVersion)
      quit()
  elif packageType == "base":
    if '10' in osVersion or '11' in osVersion:
      url_primary = 'http://{0}/$RCE/{1}-{2}/{3}-{4}/rpm/{4}/{5}'.format(smtserver, osRepo3, era, osRepo2, args.architecture[0], fileName)
      url_backup = 'http://{0}/$RCE/{1}-{2}/{3}-{4}/rpm/{4}/{5}'.format(smtserverbackup, osRepo3, era, osRepo2, args.architecture[0], fileName)
      if 'LTSS' in osVersion:
        url_primary = 'http://{0}/$RCE/{1}-{2}/{3}-{4}/rpm/{4}/{5}'.format(smtserver, osRepo3, "LTSS-Updates", osRepo2, args.architecture[0], fileName,)
        url_backup = 'http://{0}/$RCE/{1}-{2}/{3}-{4}/rpm/{4}/{5}'.format(smtserverbackup, osRepo3, "LTSS-Updates", osRepo2, args.architecture[0], fileName)
    elif '12' in osVersion or '15' in osVersion or '16' in osVersion:
      url_primary = 'http://{0}/SUSE/{1}/{2}/{3}/{4}/{5}/{4}/{6}'.format(smtserver, era, osRepo2, osRepo1, args.architecture[0], era.lower()[:-1], fileName)
      url_backup = 'http://{0}/SUSE/{1}/{2}/{3}/{4}/{5}/{4}/{6}'.format(smtserverbackup, era, osRepo2, osRepo1, args.architecture[0], era.lower()[:-1], fileName)
      if 'LTSS' in osVersion:
        url_primary = 'http://{0}/SUSE/{1}/{2}/{3}{4}/{5}/{6}/{5}/{7}'.format(smtserver, era, osRepo2, osRepo1, "-LTSS", args.architecture[0], era.lower()[:-1], fileName)
        url_backup = 'http://{0}/SUSE/{1}/{2}/{3}{4}/{5}/{6}/{5}/{7}'.format(smtserverbackup, era, osRepo2, osRepo1, "-LTSS", args.architecture[0], era.lower()[:-1], fileName)
    else:
      print("This version is not known: " + osVersion)
      quit()
  else:
    print("packageType not recognized. Unable to form URL. Exiting..")
    quit()
  return(url_primary, url_backup)

def tmpCleanup():
    """Remove temporary files created during the script execution."""
    extensions = ['*.tmp']
    for ext in extensions:
        for tmpfile in glob.glob(ext):
            try:
                os.remove(tmpfile)
                #print(f"\nCleaned up temporary file: {tmpfile}")
            except Exception as e:
                print(f"\nCould not remove {tmpfile}: {e}")

# function to download the rpms
def rpmDownload(url_primary, url_backup):
  """Attempt to download the RPM from the primary URL, and if it fails, try the backup URL."""
  global canDownload
  try:
      print(f"\n {url_primary}")
      fileName = wget.download(url_primary)
      print(f" {fileName} successfully downloaded.")
      canDownload = True
  except KeyboardInterrupt:
        tmpCleanup()
        sys.exit(1)
  except Exception as e:
      print(f" Error: {e}. {smtserver} failed.")
      print("\nChecking backup repo...")
      try:
          print(f" {url_backup}")
          fileName = wget.download(url_backup)
          print(f" {fileName} successfully downloaded.")
          canDownload = True
      except KeyboardInterrupt:
        tmpCleanup()
        sys.exit(1)
      except Exception as e2:
          print(f" Error: {e2}. {smtserverbackup} failed too.\n Is this URL accessible? {url_primary}")
          canDownload = False

# function to extract the RPM.
def rpmExtraction(packageType, fileName):
    """Extract the specified RPM file for crash analysis."""
    print(f"extracting {fileName} for crash analysis..")
    abs_rpm_path = os.path.abspath(fileName)
    tmp_dir = tempfile.mkdtemp(dir=".", prefix="extract_tmp_")

    try:
        # Determine the extraction pattern
        if '16' in osVersion:
            if packageType == "base":
                pattern = "./usr/lib/modules/*/vmlinux.xz"
            elif packageType == "info":
                pattern = "./usr/lib/debug/usr/lib/modules/*"
            else:
                pattern = "./usr/*"
        else:
            pattern = "./boot/*" if packageType == "base" else "./usr/*"

        abs_script_path = os.path.abspath(f"{scriptPath}/rpmExtraction.sh")

        subprocess.check_call([abs_script_path, abs_rpm_path, pattern], cwd=tmp_dir)

        shutil.rmtree(tmp_dir)
        return f"Successfully extracted {fileName}"
    except Exception as e:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        raise RuntimeError(f"Failed to extract {fileName}: {e}") from e



# spitting kernel, flavor, arch, output.
try:
  print("Registered the kernel as: " + args.kernelVersion[0])
except:
  print("Did you provide a kernel?")
print("Registered the flavor as: " + args.flavor[0])
print("Registered the architecture as: " + args.architecture[0])

# load json file
with open(f'{jsonPath}/kernel_versions.json', 'r', encoding='utf-8') as document:
  kernelLists = json.load(document)

# Match kernel to json and snag OS version
for name, kList in kernelLists.items():
  if args.kernelVersion[0] in kList:
      osVersion = name

# exit if kernel is not found
if osVersion == '':
  print("Could not find specified kernel in the kernel_versions.json file.")
  quit()
else:
  print("Registered the OS version as: " + osVersion)

# set poolKernel to true if it is the first kernel in the list for that Version of SLES
if kernelLists.get(osVersion)[0] == args.kernelVersion[0]:
  if not 'LTSS' in osVersion:
    print("This is a pool kernel!")
    poolKernel = True

# If it's a pool kernel set era of kernel based on version
if poolKernel:
  if '10' in osVersion or '11' in osVersion:
    era = "Pool"
  elif '12' in osVersion or '15' in osVersion or '16' in osVersion:
    era = "Products"
  else:
    print("I don't recognize this OS version: " + osVersion)
    quit()

# specify if it's an LTSS kernel
if 'LTSS' in osVersion:
    print("This is an LTSS kernel!")

# setup URL path variables based on version and subversion
version = ''
subversion = ''
novellstyle = True
if '10' in osVersion:
  osRepo2 = 'sles-10'
  version = '10'
  # warn about missing pool repos for SLES 10
  if poolKernel:
    print(f"Download may fail. {smtserver} doesn't have a pool repository for {osVersion}")
elif '11' in osVersion:
  osRepo2 = 'sle-11'
  version = '11'
elif '12' in osVersion:
  osRepo2 = 'SLE-SERVER'
  version = '12'
  novellstyle = False
elif '15' in osVersion:
  version = '15'
  novellstyle = False
  if 'LTSS' in osVersion:
    osRepo2 = 'SLE-Product-SLES'
  else:
    osRepo2 = 'SLE-Module-Basesystem'
elif '16' in osVersion:
  version = '16'
  novellstyle = False
  osRepo2 = 'SLE-Product-SLES'
  era = "Products" # All kernels are released in Products
else:
  print("This version is not known: " + osVersion)
  quit()

if 'SP1' in osVersion:
    subversion = '-SP1'
elif 'SP2' in osVersion:
    subversion = '-SP2'
elif 'SP3' in osVersion:
    subversion = '-SP3'
elif 'SP4' in osVersion:
    subversion = '-SP4'
elif 'SP5' in osVersion:
    subversion = '-SP5'
elif 'SP6' in osVersion:
    subversion = '-SP6'
elif 'SP7' in osVersion:
    subversion = '-SP7'
elif '.0' in osVersion:
    subversion = '.0'
elif '.1' in osVersion:
    subversion = '.1'
elif '.2' in osVersion:
    subversion = '.2'
elif '.3' in osVersion:
    subversion = '.3'
elif '.4' in osVersion:
    subversion = '.4'
elif '.5' in osVersion:
    subversion = '.5'
elif '.6' in osVersion:
    subversion = '.6'
else:
    subversion = ''

# use above info to set the URL variables
if novellstyle:
  osRepo1 = 'SLE{0}{1}'.format(version, subversion)
  osRepo3 = 'SLES{0}{1}'.format(version, subversion)
else:
  osRepo1 = '{0}{1}'.format(version, subversion)


# --- Execution ---
tasks = []
with ThreadPoolExecutor(max_workers=3) as executor:

    # Schedule info and source extractions
    for packageType in ["info", "source"]:
        # create file name
        debugFilename = "kernel-{0}-debug{1}-{2}.{3}.rpm".format(args.flavor[0], packageType, args.kernelVersion[0], args.architecture[0])
        if os.path.exists(debugFilename):
            print(debugFilename + " already exists.")
        else:
            # Assemble the URL
            url, url2 = urlAssemble(packageType, debugFilename)

            # Don't attempt a download of source package for SLE 10
            if '10' in osVersion and packageType == "source":
                print(osVersion + " doesn't have a separate debugsource package.")
            else:
                # Download RPM
                rpmDownload(url, url2)
            # Extract the RPM if the -e flag is set and the download was successful
            if args.extraction and canDownload:
                tasks.append(executor.submit(rpmExtraction, packageType, debugFilename))

    # Schedule base extraction
    # if -b flag, download (and extract) kernel-{flavor}{-base}
    if args.base:
        if '11' in osVersion:
            baseFilename = "kernel-{0}-base-{1}.{2}.rpm".format(args.flavor[0], args.kernelVersion[0], args.architecture[0])
        else:
            baseFilename = "kernel-{0}-{1}.{2}.rpm".format(args.flavor[0], args.kernelVersion[0], args.architecture[0])
            # assemble url and download if the file doesn't exist.
        if os.path.exists(baseFilename):
            print(baseFilename + " already exists.")
        else:
            url, url2 = urlAssemble("base", baseFilename)
            rpmDownload(url, url2)

        # Extract the RPM if the -e flag is set and the download was successful
        if args.extraction and canDownload:
            tasks.append(executor.submit(rpmExtraction, "base", baseFilename))


    # Track progress
    if tasks:
        for future in as_completed(tasks):
            try:
                result = future.result()
            except Exception as e:
                print(f"\n[ERROR] {e}")

print("All extractions done.")
