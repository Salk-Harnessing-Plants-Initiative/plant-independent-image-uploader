# AWS S3 desktop file uploader
Python script for uploading files to AWS S3 bucket with some extra features

* On startup, detects all files in the "unprocessed" directory (and recursive subdirectories),
and for each file, uploads it to S3. Moves it to the "done" directory upon success, "error" directory upon failure
* Attaches to the newly created S3 file a field called "file_created" in its metadata section. This is the timestamp
of when the file was created in the uploader's filesystem
* As long as the script is running, it will continuously monitor the "unprocessed" directory for new
files and do the same
* Logs to AWS CloudWatch for remote monitoring

# Installation
*Note: As of 16 December 2020, it is NOT recommended that you use this Python script for macOS in production. 
(This has to do with the fact that `watchdog 1.0.1` has bugs for mac).
It should be fine for other operating systems.*

Ensure pipenv is installed on your computer. Then install the dependencies:
```
pipenv install
```
Install the [awscli](https://aws.amazon.com/cli/) (`pip install awscli` might work) and set your AWS credentials (our script uses the local `~/.aws/credentials` file):
```
aws configure
```
Copy the example config file, 
```
cp config.yml.dst config.yml
```
then fill out the settings.

# To run
```
pipenv run python main.py
```

* You should use Windows Task Scheduler or Windows Service / PowerShell to get the script to always "be on"
if you're running this script on a Windows computer: https://stackoverflow.com/questions/57511964/windows-10-how-do-i-ensure-python-script-will-run-as-long-as-computer-is-on
* For Linux: https://stackoverflow.com/questions/2366693/run-cron-job-only-if-it-isnt-already-running/38840507#38840507
