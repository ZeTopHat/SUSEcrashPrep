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

try:
  import wget
except:
  print("Something went wrong.. Is the wget python module installed? Try 'sudo pip install wget'.")
  quit()

# vars to later make accessible via conf file
smtserver = "smt.lab.novell.com"

scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
currentTime = time.time()
kernelLists = {}
osVersion = ''
poolKernel = False
era = "Updates"
canDownload = False

if os.path.exists("{0}/kernel_versions.json".format(scriptPath)):
  lastModifiedTime = os.path.getmtime("{0}/kernel_versions.json".format(scriptPath))
  if (currentTime - lastModifiedTime) // (24 * 3600) >= 1:
    import collectKernelData
else:
  import collectKernelData

if '-default' in args.kernelVersion[0]:
  print('Converting "-default" to ".1" to match full kernel versions. If true kernel version uses .2, .3, etc the kernel may not be found.')
  args.kernelVersion[0] = re.sub("-default", ".1", args.kernelVersion[0])

def urlAssemble(packageType, fileName):
  if packageType == "info" or packageType == "source":
    # urls are significantly different depending on 11 or 12
    if '10' in osVersion or '11' in osVersion:
      url = 'http://{5}/repo/$RCE/{0}-Debuginfo-{1}/{2}-{3}/rpm/{3}/{4}'.format(osRepo1, era, osRepo2, args.architecture[0], fileName, smtserver)
    elif '12' in osVersion or '15' in osVersion:
      url = 'http://{5}/SUSE/{0}/{6}/{1}/{2}/{3}_debug/{2}/{4}'.format(era, osRepo1, args.architecture[0], era.lower()[:-1], fileName, smtserver, osRepo2)
      if 'LTSS' in osVersion:
        url = 'http://{6}/SUSE/{0}/{7}/{1}{2}/{3}/{4}_debug/{3}/{5}'.format(era, osRepo1, "-LTSS", args.architecture[0], era.lower()[:-1], fileName, smtserver, osRepo2)
    else:
      print("This version is not known: " + osVersion)
      quit()
  elif packageType == "base":
    # once again, major version have very different url paths
    if '10' in osVersion or '11' in osVersion:
      url = 'http://{5}/repo/$RCE/{0}-{1}/{2}-{3}/rpm/{3}/{4}'.format(osRepo3, era, osRepo2, args.architecture[0], fileName, smtserver)
      if 'LTSS' in osVersion:
        url = 'http://{5}/repo/$RCE/{0}-{1}/{2}-{3}/rpm/{3}/{4}'.format(osRepo3, "LTSS-Updates", osRepo2, args.architecture[0], fileName, smtserver)
    elif '12' in osVersion or '15' in osVersion:
      url = 'http://{5}/SUSE/{0}/{6}/{1}/{2}/{3}/{2}/{4}'.format(era, osRepo1, args.architecture[0], era.lower()[:-1], fileName, smtserver, osRepo2)
      if 'LTSS' in osVersion:
        url = 'http://{6}/SUSE/{0}/{7}/{1}{2}/{3}/{4}/{3}/{5}'.format(era, osRepo1, "-LTSS", args.architecture[0], era.lower()[:-1], fileName, smtserver, osRepo2)
    else:
      print("This version is not known: " + osVersion)
      quit()
  else:
    print("packageType not recognized. Unable to form URL. Exiting..")
    quit()
  return(url)

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


try:
  print("Registered the kernel as: " + args.kernelVersion[0])
except:
  print("Did you provide a kernel?")

print("Registered the flavor as: " + args.flavor[0])
print("Registered the architecture as: " + args.architecture[0])

with open('{0}/kernel_versions.json'.format(scriptPath), 'r') as document:
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
  if '10' in osVersion or '11' in osVersion:
    era = "Pool"
  elif '12' in osVersion or '15' in osVersion:
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
    if poolKernel:
      print("Download will likely fail. nu.novell.com doesn't have a pool repository for " + osVersion)
  elif 'SP2' in osVersion:
    osRepo1='SLE10-SP2'
    osRepo3='SLES10-SP2'
    if poolKernel:
      print("Download will likely fail. nu.novell.com doesn't have a pool repository for " + osVersion)
  elif 'SP3' in osVersion:
    osRepo1='SLE10-SP3'
    osRepo3='SLES10-SP3'
  elif 'SP4' in osVersion:
    osRepo1='SLE10-SP4'
    osRepo3='SLES10-SP4'
  else:
    osRepo1='SLE10'
    osRepo3='SLES10'
    if poolKernel:
      print("Download will likely fail. nu.novell.com doesn't have a pool repository for " + osVersion)
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
  osRepo2='SLE-SERVER'
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
elif '15' in osVersion:
  osRepo2='SLE-Module-Basesystem'
  if 'SP1' in osVersion:
    osRepo1='15-SP1'
  elif 'SP2' in osVersion:
    osRepo1='15-SP2'
  else:
    osRepo1='15'
else:
  print("This version is not known: " + osVersion)
  quit()


# loop through the info and source packages to download
for packageType in ["info", "source"]:
  debugFilename = "kernel-{3}-debug{0}-{1}.{2}.rpm".format(packageType, args.kernelVersion[0], args.architecture[0], args.flavor[0])
  if os.path.exists(debugFilename):
    print(debugFilename + " already exists.")
  else:
    url = urlAssemble(packageType, debugFilename)

    if '10' in osVersion and packageType == "source":
      print(osVersion + " doesn't have a separate debugsource package.")
    else:
      rpmDownload(url)

      if args.extraction and canDownload:
        rpmExtraction(packageType, debugFilename)

if args.base:
  if '10' in osVersion:
    baseFilename = "kernel-{2}-{0}.{1}.rpm".format(args.kernelVersion[0], args.architecture[0], args.flavor[0])
  elif '11' in osVersion:
    baseFilename = "kernel-{2}-base-{0}.{1}.rpm".format(args.kernelVersion[0], args.architecture[0], args.flavor[0])
  else:
    baseFilename = "kernel-{2}-{0}.{1}.rpm".format(args.kernelVersion[0], args.architecture[0], args.flavor[0])

  if os.path.exists(baseFilename):
    print(baseFilename + " already exists.")
  else:
    url = urlAssemble("base", baseFilename)
    rpmDownload(url)

    if args.extraction and canDownload:
      rpmExtraction("base", baseFilename)


