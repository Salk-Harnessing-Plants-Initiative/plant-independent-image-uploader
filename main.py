"""
Salk Harnessing Plants Initiative
Python script for uploading files to AWS S3 bucket
Russell Tran
December 2020

References:
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
# For getting file creation timestamp
import platform
import pathlib
# For detecting new files
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
# (For bug workaround for watchdog 1.0.1)
from watchdog.utils import platform
from watchdog.observers.polling import PollingObserver
# For AWS S3
import boto3
from botocore.exceptions import ClientError
# For logging remotely to AWS CloudWatch
from boto3.session import Session
import watchtower

# Have a global logger so you can add the AWS CloudWatch handler
logger = logging.getLogger(__name__)

def creation_date(file_path):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return os.path.getctime(file_path)
    else:
        stat = os.stat(file_path)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime

def get_file_created(file_path):
    """Gets the file's creation timestamp from the filesystem and returns it as a string
    Errors upon failure
    """
    return datetime.fromtimestamp(creation_date(file_path)).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')

def get_metadata(file_path):
    metadata = {"Metadata": {}}
    try:
        metadata["Metadata"]["file_created"] = get_file_created(file_path)
    except:
        pass
    return metadata

def upload_file(s3_client, file_name, bucket, object_name):
    """Upload a file to an S3 bucket
    :param s3_client: Initialized S3 client to use
    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. Also known as a "Key" in S3 bucket terms.
    :return: True if file was uploaded, else False
    """
    global logger
    try:
        response = s3_client.upload_file(file_name, bucket, object_name, 
            Callback=ProgressPercentage(file_name), ExtraArgs=get_metadata(file_name))
        logger.info(response)
    except ClientError as e:
        logger.error(e)
        return False
    return True

def generate_bucket_key(file_path, s3_directory):
    """Keep things nice and random to prevent collisions
    "/Users/russell/Documents/taco_tuesday.jpg" becomes "raw/taco_tuesday-b94b0793-6c74-44a9-94e0-00420711130d.jpg"
    Note: We still like to keep the basename because some files' only timestamp is in the filename
    """
    root_ext = os.path.splitext(ntpath.basename(file_path));
    return s3_directory + root_ext[0] + "-" + str(uuid.uuid4()) + root_ext[1];

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
    global logger
    try:
        today_subdir = ensure_today_subdir(dir)
        dst_path = os.path.join(today_subdir, ntpath.basename(src_path))
        # Avoid collisions
        root_ext = os.path.splitext(dst_path)
        i = 0
        while os.path.isfile(dst_path):
            i += 1
            dst_path = root_ext[0] + " ({})".format(i) + root_ext[1]
        # Finally move file
        shutil.move(src_path, dst_path)
    except Exception as e:
        logger.error(e)
        pass

def process(file_path, s3_client, bucket, bucket_dir, done_dir, error_dir):
    """Name, upload, move file
    """
    global logger
    object_name = generate_bucket_key(file_path, bucket_dir)
    success = upload_file(s3_client, file_path, bucket, object_name)
    if success:
        logger.info("Successfully uploaded {} to {} as {}".format(file_path, bucket, object_name))
        move(file_path, done_dir)
    else:
        move(file_path, error_dir)

def get_preexisting_files(dir):
    """Recursively get all filenames in a directory
    Returns them as a list of paths
    """
    preexisting = []
    for root, dirs, files in os.walk(dir):
        # Ignore hidden files
        files = [f for f in files if not f[0] == '.']
        for file in files:
            preexisting.append(os.path.join(root, file))
    return sorted(preexisting)

def keep_running(observer, send_heartbeat, heartbeat_seconds):
    """Note: Loops until Ctrl-C
    If send_heartbeat is true, logs a heartbeat approximately every
    heartbeat_seconds
    """
    global logger
    try:
        s = 0
        while True:
            time.sleep(1)
            s += 1
            if send_heartbeat and s >= heartbeat_seconds:
                logger.info("HEARTBEAT")
                s = 0
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt: shutting down script.py...")
        observer.stop()
        observer.join()

class ProgressPercentage(object):
    """Callback used for boto3 to sporadically report the upload progress for a large file
    """

    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0

    def __call__(self, bytes_amount):
        """Callback that logs how many bytes have been uploaded so far for a particular file
        """
        global logger
        self._seen_so_far += bytes_amount
        percentage = (self._seen_so_far / self._size) * 100
        #logger.info("Uploading status for {}: {} / {} ({}%)"
        #    .format(self._filename, self._seen_so_far, self._size, percentage))
        # Print for now instead of log because this gets kind of spammy
        print("Uploading status for {}: {} / {} ({}%)".format(self._filename, self._seen_so_far, self._size, percentage))

class S3EventHandler(FileSystemEventHandler):
    """Handler for what to do if watchdog detects a filesystem change
    """

    def __init__(self, s3_client, s3_bucket, s3_bucket_dir, unprocessed_dir, done_dir, error_dir):
        self.s3_client = s3_client
        self.s3_bucket = s3_bucket
        self.s3_bucket_dir = s3_bucket_dir
        self.unprocessed_dir = unprocessed_dir
        self.done_dir = done_dir
        self.error_dir = error_dir

    def on_created(self, event):
        is_file = not event.is_directory
        if is_file:
            process(event.src_path, self.s3_client, self.s3_bucket, self.s3_bucket_dir, self.done_dir, self.error_dir)

def main():
    global logger
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    config = yaml.safe_load(open("config.yml"))
    s3_client = boto3.client('s3')
    bucket = config["s3"]["bucket"]
    bucket_dir = config["s3"]["bucket_dir"]
    unprocessed_dir = config["unprocessed_dir"]
    done_dir = config["done_dir"]
    error_dir = config["error_dir"]

    # Setup remote logging
    watchtower_handler = watchtower.CloudWatchLogHandler(
        log_group=config["cloudwatch"]["log_group"],
        stream_name=config["cloudwatch"]["stream_name"],
        send_interval=config["heartbeat_seconds"],
        create_log_group=False
    )
    logger.addHandler(watchtower_handler)

    # Check for any preexisting files in the "unprocessed" folder
    preexisting = get_preexisting_files(unprocessed_dir)

    # Setup the watchdog handler for new files that are added while the script is running
    event_handler = S3EventHandler(s3_client, bucket, bucket_dir, unprocessed_dir, done_dir, error_dir)
    if platform.is_darwin():
        # Bug workaround for watchdog 1.0.1
        # For now you should NOT use this script for production use because
        # the polling observer is usually used as the a last resort in the watchdog library
        # and is literally implemented by spinning / constantly poking the filesystem
        observer = PollingObserver()
    else:
        observer = Observer()
    observer.schedule(event_handler, unprocessed_dir, recursive=True)
    observer.start()

    # Upload & process any preexisting files
    if preexisting:
        for file_path in preexisting:
            process(file_path, s3_client, bucket, bucket_dir, done_dir, error_dir)

    # Keep the main thread running so watchdog handler can be still be called
    keep_running(observer, config["send_heartbeat"], config["heartbeat_seconds"])

if __name__ == "__main__":
    main()

# FUTURE TODO: Discover whether it's necessary to renew the boto3 client after some time
# (https://stackoverflow.com/questions/63724485/how-to-refresh-the-boto3-credetials-when-python-script-is-running-indefinitely)
# FUTURE TODO: Discover whether single-threaded upload is too slow and whether multithreading is necessary here
# (Note that setting Config to something like=boto3.s3.transfer.TransferConfig(max_concurrency=5, use_threads=True)
# doesn't seem to have a multithreading effect for some reason)
# TODO: Clean up upload progress callback logic
