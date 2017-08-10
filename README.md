# Crash Prep

This is an RPM download and extraction tool for internal SUSE employees looking to more quickly perform crash analysis on kernel core dumps.

## Getting Started

 

### Prerequisites

This tool has only been tested on openSUSE Leap 42.1 and 42.2. It relies on python3. The modules currently in use were all installed by default except for python wget module. That can be installed with:

```
sudo pip install wget
```

The machine in use needs passwordless access to http://nu.novell.com and access to https://wiki.microfocus.com/index.php/SUSE/SLES/Kernel_versions

### Installing

Download the files from this repository:

```
git clone https://github.com/ZeTopHat/SUSEcrashPrep.git
```

After that you just have to execute the crashPrep.py file. The other files are supporting and are not executed directly by the user.

## Additional Notes

```
user@host:~> ./crashPrep.py -h
usage: crashPrep.py [-h] [-a architecture] [-b] [-e] kernel

Download files for core analysis.

positional arguments:
  kernel                Kernel version to use.

optional arguments:
  -h, --help            show this help message and exit
  -a architecture, --arch architecture
                        Architecture to use. (defaults to x86_64)
  -b, --base            If included, will also download the kernel-default-
                        base
  -e, --extraction      If included, will also extract the downloaded rpm
                        files.
user@host:~> 

```

## Built With

* [Python](https://www.python.org/) - The primary programming language
* [JSON](http://www.json.org/) - Data-interchange format used for storing kernel lists.
* [BASH](http://www.bash.org/) - Used to extract rpms.

## Contributing

Please read [CONTRIBUTING.md](https://github.com/ZeTopHat/SUSEcrashPrep/blob/master/CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

## Author

* **Colin Hamilton** - *Initial work* - [ZeTopHat](https://github.com/ZeTopHat)

See also the list of [contributors](https://github.com/ZeTopHat/SUSEcrashPrep/contributors) who participated in this project.

## Acknowledgments

* To the crash utility for making us work that much harder to analyze kernel cores.

