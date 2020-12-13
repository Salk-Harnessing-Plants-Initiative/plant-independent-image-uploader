"""
Salk Harnessing Plants Initiative
Python script for uploading files to AWS S3 bucket
Russell Tran
December 2020

* On startup, detects all files in the "unprocessed" directory (and recursive subdirectories),
and for each file, uploads it to S3 and moves it to the "done" directory upon success, "error" directory upon failure
* As long as the script is running, it will continuously monitor the "unprocessed" directory for new
files and do the same
* Logs to AWS CloudWatch for remote monitoring
* You should use Windows Task Scheduler or Windows Service / PowerShell to get the script to always "be on"
if you're running this script on a Windows computer

https://stackoverflow.com/questions/57511964/windows-10-how-do-i-ensure-python-script-will-run-as-long-as-computer-is-on
https://pythonhosted.org/watchdog/quickstart.html
https://blog.magrathealabs.com/filesystem-events-monitoring-with-python-9f5329b651c3
"""
import time
from datetime import datetime
import logging
import yaml
import uuid
import os
import shutil
import ntpath
# For detecting new files
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
# For AWS S3
import boto3
# For logging remotely to AWS CloudWatch
from boto3.session import Session
import watchtower

def upload_file(s3_client, file_name, bucket, object_name):
    """Upload a file to an S3 bucket
	:param s3_client: Initialized S3 client to use
    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. Also known as a "Key" in S3 bucket terms.
    :return: True if file was uploaded, else False
    """
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
        logging.info(response)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def generate_bucket_key(path):
	"""Keep things nice and random to prevent collisions
	"/Users/russell/Documents/taco_tuesday.jpg" becomes "taco_tuesday-b94b0793-6c74-44a9-94e0-00420711130d.jpg"
	"""
	root_ext = os.path.splitext(ntpath.basename(path));
	return root_ext[0] + "-" + str(uuid.uuid4()) + root_ext[1];

def ensure_today_subdir(dir):
	"""If dir doesn't have a subdirectory named today's date in "YYYY-MM-DD" format,
	make one and return the path
	"""
	today_subdir = os.path.join(dir, datetime.today().strftime('%Y-%m-%d'))
	if not os.path.exists(today_subdir):
    	os.makedirs(today_subdir)
    return today_subdir

def move(src_path, dir):
	""" Move the file {src_path} to {dir}/YYYY-MM-DD/{src_path's basename},
	where YYYY-MM-DD is today's date. If the YYYY-MM-DD subdirectory doesn't exist, creates it.
	If the destination path is already taken, moves the file to 
	"{dir}/YYYY-MM-DD/{src_path's baseroot} (i){src ext}" instead to avoid collisions. 
	(Where i is a recursive increment).
	"""
	today_subdir = ensure_today_subdir(dir)
	dst_path = os.path.join(today_subdir, ntpath.basename(src_path))
	# Avoid collisions
	i = 0
	while os.path.isfile(dst_path):
    	i += 1
    	root_ext = os.path.splitext(dst_path)
    	dst_path = root_ext[0] + " ({})".format(i) + root_ext[1]
    # Finally move file
	shutil.move(src_path, dst_path)

class ProgressPercentage(object):

    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0

    def __call__(self, bytes_amount):
    	"""Callback that logs how many bytes have been uploaded so far for a particular file
    	"""
        self._seen_so_far += bytes_amount
        percentage = (self._seen_so_far / self._size) * 100
        logging.info("Uploading status for {}: {} / {} ({}%)"
        	.format(self._filename, self._seen_so_far, self._size, percentage))

class S3EventHandler(FileSystemEventHandler):

	def __init__(self, s3_client, s3_bucket, unprocessed_dir, done_dir, error_dir):
		self.s3_client = s3_client
		self.s3_bucket = s3_bucket
		self.unprocessed_dir = unprocessed_dir
		self.done_dir = done_dir
		self.error_dir = error_dir

    def on_created(self, event):
    	if not event.is_directory:
    		file_path = event.src_path
    		object_name = generate_bucket_key(file_path)
        	success = upload_file(self.s3_client, file_path, self.s3_bucket, object_name,
        		Callback=ProgressPercentage(file_path))
        	if success:
        		move(file_path, self.done_dir)
        	else:
        		move(file_path, self.error_dir)

def main():
	logging.basicConfig(level=logging.INFO,
						format='%(asctime)s - %(message)s',
						datefmt='%Y-%m-%d %H:%M:%S')
	config = yaml.safe_load(open("config.yml"))
    s3_client = boto3.client('s3', aws_access_key_id=config["s3"]["access_key"], 
    					aws_secret_access_key=config["s3"]["secret_key"])
    cloudwatch = Session(aws_access_key_id=config["cloudwatch"]["access_key"],
    					aws_secret_access_key=config["cloudwatch"]["secret_key"],
    					region_name=config["cloudwatch"]["region_name"])
    bucket = config["s3"]["bucket"]
    unprocessed_dir = config["unprocessed_dir"]
    done_dir = config["done_dir"]
    error_dir = config["error_dir"]

    # Setup remote logging
    logger = logging.getLogger(__name__)
    logger.addHandler(watchtower.CloudWatchLogHandler(cloudwatch))

    # Check for any preexisting files in the "unprocessed" folder
	preexisting = []
	for root, dirs, files in os.walk(unprocessed_dir):
    	files = [f for f in files if not f[0] == '.']
    	for file in files:
    		preexisting.append(os.path.join(root, file))

    # Setup the watchdog handler for new files that are added while the script is running
    event_hander = S3EventHandler(s3_client, bucket, unprocessed_dir, done_dir, error_dir)
    observer = Observer()
	observer.schedule(event_handler, unprocessed_dir, recursive=True)
	observer.start()

	# Upload & process any preexisting files
	for file_path in preexisting:
		object_name = generate_bucket_key(file_path)
    	success = upload_file(s3_client, file_path, bucket, object_name,
    		Callback=ProgressPercentage(file_path))
    	if success:
    		move(file_path, done_dir)
    	else:
    		move(file_path, error_dir)

    # Keep the main thread running so watchdog handler can be still be called
	try:
		s = 0
		while True:
			time.sleep(1)
			s += 1
			if config["send_heartbeat"] and s >= config["heartbeat_seconds"]:
				logging.info("HEARTBEAT")
				s = 0
	except KeyboardInterrupt:
		logging.info("KeyboardInterrupt: shutting down script.py...")
		observer.stop()
		observer.join()

if __name__ == "__main__":
	main()
