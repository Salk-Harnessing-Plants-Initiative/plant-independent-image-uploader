# Installation
*Note: As of 16 December 2020, it is NOT recommended that you use this Python script for macOS. 
(This has to do with the fact that `watchdog 1.0.1` has bugs for mac).
It should be fine for other operating systems.*

Ensure pipenv is installed on your computer. Then install the dependencies:
```
pipenv install
```
Install the [awscli](https://aws.amazon.com/cli/) and set your AWS credentials (our script uses the local `~/.aws/credentials` file):
```
aws configure
```
Copy the example config file, then fill out the settings:
```
cp config.yml.dst config.yml
```

# To run
```
pipenv run pythong main.py
```

* You should use Windows Task Scheduler or Windows Service / PowerShell to get the script to always "be on"
if you're running this script on a Windows computer: https://stackoverflow.com/questions/57511964/windows-10-how-do-i-ensure-python-script-will-run-as-long-as-computer-is-on