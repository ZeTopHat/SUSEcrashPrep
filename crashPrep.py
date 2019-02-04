#! /usr/bin/python3
import os
import sys
import time
import json
import re
import subprocess
import shutil
import argparse

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
except:
  print("Something went wrong.. Is the wget python module installed? Try 'sudo pip install wget'.")
  quit()

# vars to later make accessible via conf file
smtserver = "smt.lab.novell.com"

# starting vars
scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
currentTime = time.time()
kernelLists = {}
osVersion = ''
poolKernel = False
era = "Updates"
canDownload = False

# create a new kernel_versions.json file if it doesn't exist or is older than a day old
if os.path.exists("{0}/kernel_versions.json".format(scriptPath)):
  lastModifiedTime = os.path.getmtime("{0}/kernel_versions.json".format(scriptPath))
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
  if packageType == "info" or packageType == "source":
    if '10' in osVersion or '11' in osVersion:
      url = 'http://{0}/repo/$RCE/{1}-Debuginfo-{2}/{3}-{4}/rpm/{4}/{5}'.format(smtserver, osRepo1, era, osRepo2, args.architecture[0], fileName)
    elif '12' in osVersion or '15' in osVersion:
      url = 'http://{0}/SUSE/{1}/{2}/{3}/{4}/{5}_debug/{4}/{6}'.format(smtserver, era, osRepo2, osRepo1, args.architecture[0], era.lower()[:-1], fileName)
      if 'LTSS' in osVersion:
        url = 'http://{0}/SUSE/{1}/{2}/{3}{4}/{5}/{6}_debug/{5}/{7}'.format(smtserver, era, osRepo2, osRepo1, "-LTSS", args.architecture[0], era.lower()[:-1], fileName)
    else:
      print("This version is not known: " + osVersion)
      quit()
  elif packageType == "base":
    if '10' in osVersion or '11' in osVersion:
      url = 'http://{0}/repo/$RCE/{1}-{2}/{3}-{4}/rpm/{4}/{5}'.format(smtserver, osRepo3, era, osRepo2, args.architecture[0], fileName)
      if 'LTSS' in osVersion:
        url = 'http://{0}/repo/$RCE/{1}-{2}/{3}-{4}/rpm/{4}/{5}'.format(smtserver, osRepo3, "LTSS-Updates", osRepo2, args.architecture[0], fileName, smtserver)
    elif '12' in osVersion or '15' in osVersion:
      url = 'http://{0}/SUSE/{1}/{2}/{3}/{4}/{5}/{4}/{6}'.format(smtserver, era, osRepo2, osRepo1, args.architecture[0], era.lower()[:-1], fileName)
      if 'LTSS' in osVersion:
        url = 'http://{0}/SUSE/{1}/{2}/{3}{4}/{5}/{6}/{5}/{7}'.format(smtserver, era, osRepo2, osRepo1, "-LTSS", args.architecture[0], era.lower()[:-1], fileName)
    else:
      print("This version is not known: " + osVersion)
      quit()
  else:
    print("packageType not recognized. Unable to form URL. Exiting..")
    quit()
  return(url)

# function to download the rpms
def rpmDownload(url):
  print(url)
  global canDownload 
  try:
    fileName = wget.download(url)
    print("\n" + fileName + " successfully downloaded.")
    canDownload = True
  except:
    print("Failed to download. Is this URL accessible?: " + url)
    canDownload = False

# function to extract the RPM.
def rpmExtraction(packageType, fileName):
  print("extracting {0} for crash analysis..".format(fileName))
  try:
    if packageType == "info":
      subprocess.call([scriptPath + "/rpmExtraction.sh", fileName, "./usr/*"])
      shutil.rmtree("./usr")
    elif packageType == "source":
      subprocess.call([scriptPath + "/rpmExtraction.sh", fileName, "./usr/*"])
      shutil.rmtree("./usr")
    elif packageType == "base":
      subprocess.call([scriptPath + "/rpmExtraction.sh", fileName, "./boot/*"])
      shutil.rmtree("./boot")
    else:
      print("packageType not recognized. exiting..")
      quit()
    print("{0} rpm extracted.".format(fileName))         
  except:
    print("Couldn't execute rpmExtraction.sh file.")

# spitting kernel, flavor, arch, output.
try:
  print("Registered the kernel as: " + args.kernelVersion[0])
except:
  print("Did you provide a kernel?")
print("Registered the flavor as: " + args.flavor[0])
print("Registered the architecture as: " + args.architecture[0])

# load json file
with open('{0}/kernel_versions.json'.format(scriptPath), 'r') as document:
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
  elif '12' in osVersion or '15' in osVersion:
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
    print("Download may fail. {0} doesn't have a pool repository for {1}".format(smtserver, osVersion))
elif '11' in osVersion:
  osRepo2 = 'sle-11'
  version = '11'
elif '12' in osVersion:
  osRepo2 = 'SLE-SERVER'
  version = '12'
  novellstyle = False
elif '15' in osVersion:
  osRepo2 = 'SLE-Module-Basesystem'
  version = '15'
  novellstyle = False
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
else:
    subversion = ''

# use above info to set the URL variables
if novellstyle:
  osRepo1 = 'SLE{0}{1}'.format(version, subversion)
  osRepo3 = 'SLES{0}{1}'.format(version, subversion)
else:
  osRepo1 = '{0}{1}'.format(version, subversion)

for packageType in ["info", "source"]:
  # create file name
  debugFilename = "kernel-{0}-debug{1}-{2}.{3}.rpm".format(args.flavor[0], packageType, args.kernelVersion[0], args.architecture[0])
  if os.path.exists(debugFilename):
    print(debugFilename + " already exists.")
  else:
    # Assemble the URL
    url = urlAssemble(packageType, debugFilename)

    # Don't attempt a download of source package for SLE 10
    if '10' in osVersion and packageType == "source":
      print(osVersion + " doesn't have a separate debugsource package.")
    else:
      # Download RPM
      rpmDownload(url)
      # Extract the RPM if the -e flag is set and the download was successful 
      if args.extraction and canDownload:
        rpmExtraction(packageType, debugFilename)

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
    url = urlAssemble("base", baseFilename)
    rpmDownload(url)

    # Extract the RPM if the -e flag is set and the download was successful
    if args.extraction and canDownload:
      rpmExtraction("base", baseFilename)

