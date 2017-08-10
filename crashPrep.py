#! /usr/bin/python3
import os
import sys
import time
import json
import subprocess
import shutil
import argparse

# argument parsing module
parser = argparse.ArgumentParser(description='Download files for core analysis.')
parser.add_argument('kernelVersion', nargs=1, metavar='kernel', help='Kernel version to use.')
parser.add_argument('-a', '--arch', nargs=1, metavar='architecture', help='Architecture to use. (defaults to x86_64)', default=['x86_64'], dest='architecture')
parser.add_argument('-b', '--base', help='If included, will also download the kernel-default-base', action='store_true')
parser.add_argument('-e', '--extraction', help='If included, will also extract the downloaded rpm files.', action='store_true')
args = parser.parse_args()

try:
  import wget
except:
  print("Something went wrong.. Is the wget python module installed? Try 'sudo pip install wget'.")
  quit()

scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
currentTime = time.time()
kernelLists = {}
osVersion = ''
poolKernel = False
era = "Updates"

if os.path.exists("%s/kernel_versions.json" % scriptPath):
  lastModifiedTime = os.path.getmtime("%s/kernel_versions.json" % scriptPath)
  if (currentTime - lastModifiedTime) // (24 * 3600) >= 1:
    import collectKernelData
else:
  import collectKernelData


def urlAssemble(packageType, fileName):
  if packageType == "info" or packageType == "source":
    # urls are significantly different depending on 11 or 12
    if '10' or '11' in osVersion:
      url = 'https://nu.novell.com/repo/$RCE/%s-Debuginfo-%s/%s-%s/rpm/%s/%s' % (osRepo1, era, osRepo2, args.architecture[0], args.architecture[0], fileName)
    elif '12' in osVersion:
      url = 'http://nu.novell.com/SUSE/%s/SLE-SERVER/%s/%s/%s_debug/%s/%s' % (era, osRepo1, args.architecture[0], era.lower()[:-1], args.architecture[0], fileName)
      if 'LTSS' in osVersion:
        url = 'http://nu.novell.com/SUSE/%s/SLE-SERVER/%s%s/%s/%s_debug/%s/%s' % (era, osRepo1, "-LTSS", args.architecture[0], era.lower()[:-1], args.architecture[0], fileName)
    else:
      print("This version is not known: " + osVersion)
      quit()
  elif packageType == "base":
    # once again, major version have very different url paths
    if '10' or '11' in osVersion:
      url = 'http://nu.novell.com/repo/$RCE/%s-%s/%s-%s/rpm/%s/%s' % (osRepo3, era, osRepo2, args.architecture[0], args.architecture[0], fileName)
      if 'LTSS' in osVersion:
        url = 'http://nu.novell.com/repo/$RCE/%s-%s/%s-%s/rpm/%s/%s' % (osRepo3, "LTSS-Updates", osRepo2, args.architecture[0], args.architecture[0], fileName)
    elif '12' in osVersion:
      url = 'http://nu.novell.com/SUSE/%s/SLE-SERVER/%s/%s/%s/%s/%s' % (era, osRepo1, args.architecture[0], era.lower()[:-1], args.architecture[0], fileName)
      if 'LTSS' in osVersion:
        url = 'http://nu.novell.com/SUSE/%s/SLE-SERVER/%s%s/%s/%s/%s/%s' % (era, osRepo1, "-LTSS", args.architecture[0], era.lower()[:-1], args.architecture[0], fileName)
    else:
      print("This version is not known: " + osVersion)
      quit()
  else:
    print("packageType not recognized. Unable to form URL. Exiting..")
    quit()
  return(url)

def rpmDownload(url):
  print(url)
  try:
    fileName = wget.download(url)
    print("\n" + fileName + " successfully downloaded.")
  except:
    print("Failed to download. Is this URL accessible?: " + url)

def rpmExtraction(packageType, fileName):
  print("extracting %s for crash analysis.." % fileName)
  try:
    if packageType == "info":
      subprocess.call([scriptPath + "/rpmExtraction.sh", fileName, "./usr/lib/debug/boot/*"])
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
    print("%s rpm extracted." % fileName)         
  except:
    print("Couldn't execute rpmExtraction.sh file.")


try:
  print("Registered the kernel as: " + args.kernelVersion[0])
except:
  print("Did you provide a kernel?")

print("Registered the architecture as: " + args.architecture[0])

with open('%s/kernel_versions.json' % scriptPath, 'r') as document:
  kernelLists = json.load(document)

for name, kList in kernelLists.items():
  if args.kernelVersion[0] in kList:
    osVersion = name

if osVersion == '':
  print("Could not find specified kernel in the kernel_versions.json file.")
  quit()
else:  
  print("Registered the OS version as: " + osVersion)

if kernelLists.get(osVersion)[0] == args.kernelVersion[0]:
  if not 'LTSS' in osVersion:
    print("This is a pool kernel!")
    poolKernel = True

if poolKernel:
  if '10' or '11' in osVersion:
    era = "Pool"
  elif '12' in osVersion:
    era = "Products"
  else:
    print("I don't recognize this OS version: " + osVersion)
    quit()

if 'LTSS' in osVersion:
  print("This is an LTSS kernel!")

# setup the proper URL paths for the various OS versions
if '10' in osVersion:
  osRepo2='sles-10'
  if 'SP1' in osVersion:
    osRepo1='SLE10-SP1'
    osRepo3='SLES10-SP1'
  elif 'SP2' in osVersion:
    osRepo1='SLE10-SP2'
    osRepo3='SLES10-SP2'
  elif 'SP3' in osVersion:
    osRepo1='SLE10-SP3'
    osRepo3='SLES10-SP3'
  elif 'SP4' in osVersion:
    osRepo1='SLE10-SP4'
    osRepo3='SLES10-SP4'
  else:
    osRepo1='SLE10'
    osRepo3='SLES10'
elif '11' in osVersion:
  osRepo2='sle-11'
  if 'SP1' in osVersion:
    osRepo1='SLE11-SP1'
    osRepo3='SLES11-SP1'
  elif 'SP2' in osVersion:
    osRepo1='SLE11-SP2'
    osRepo3='SLES11-SP2'
  elif 'SP3' in osVersion:
    osRepo1='SLE11-SP3'
    osRepo3='SLES11-SP3'
  elif 'SP4' in osVersion:
    osRepo1='SLE11-SP4'
    osRepo3='SLES11-SP4'
  else:
    osRepo1='SLE11'
    osRepo3='SLES11'
elif '12' in osVersion:
  if 'SP1' in osVersion:
    osRepo1='12-SP1'
  elif 'SP2' in osVersion:
    osRepo1='12-SP2'
  elif 'SP3' in osVersion:
    osRepo1='12-SP3'
  elif 'SP4' in osVersion:
    osRepo1='12-SP4'
  else:
    osRepo1='12'
else:
  print("This version is not known: " + osVersion)
  quit()


# loop through the info and source packages to download
for packageType in ["info", "source"]:
  debugFilename = "kernel-default-debug%s-%s.%s.rpm" % (packageType, args.kernelVersion[0], args.architecture[0])
  if os.path.exists(debugFilename):
    print(debugFilename + " already exists.")
  else:
    url = urlAssemble(packageType, debugFilename)

    if '10' in osVersion and packageType == "source":
      print(osVersion + " doesn't have a separate debugsource package.")
    else:
      rpmDownload(url)

      if args.extraction:
        rpmExtraction(packageType, debugFilename)

if args.base:
  if '10' in osVersion:
    baseFilename = "kernel-default-%s.%s.rpm" % (args.kernelVersion[0], args.architecture[0])
  else:
    baseFilename = "kernel-default-base-%s.%s.rpm" % (args.kernelVersion[0], args.architecture[0])
  if os.path.exists(baseFilename):
    print(baseFilename + " already exists.")
  else:
    url = urlAssemble("base", baseFilename)
    rpmDownload(url)

    if args.extraction:
      rpmExtraction("base", baseFilename)


