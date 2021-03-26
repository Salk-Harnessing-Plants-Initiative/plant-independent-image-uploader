# plant-independent-image-uploader
Fork of https://github.com/Salk-Harnessing-Plants-Initiative/aws-s3-desktop-uploader specific to HPI lab use

* On startup, detects all files in the `unprocessed` directory (and recursive subdirectories),
and for each file, uploads it to S3. Moves it to the `done` directory upon success, `error` directory upon failure
* Attaches to the newly created S3 file a field called `file_created` in its metadata section. This is the timestamp
of when the file was created in the uploader's filesystem
* As long as the script is running, it will continuously monitor the `unprocessed` directory for new
files and do the same
* Logs to AWS CloudWatch for remote monitoring

# Installation

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
then fill out the settings. You should have both S3 and CloudWatch set up on AWS.

# To run
```
pipenv run python aws_s3_desktop_uploader/desktop_uploader.py
```

* For Windows: https://stackoverflow.com/questions/32404/how-do-you-run-a-python-script-as-a-service-in-windows/46450007#46450007
* For Linux: https://stackoverflow.com/questions/2366693/run-cron-job-only-if-it-isnt-already-running/38840507#38840507

## Linux example
```
apt-get install run-one
```
"Ensure exactly one instance of `main.py` is running, and check every 5 minutes":
```
*/5 * * * * run-one /path/to/pipenv run python /path/to/aws_s3_desktop_uploader/desktop_uploader.py
```

# Use as a package
Haven't taken the time to distribute a full-fledged package, but you can still use this as a git submodule:
```
git submodule add https://github.com/Salk-Harnessing-Plants-Initiative/aws-s3-desktop-uploader
pipenv install --editable ./aws-s3-desktop-uploader
```
Then in your Python script:
```
from aws_s3_desktop_uploader import desktop_uploader
print(desktop_uploader.get_file_created("iguana.jpg"))
```
