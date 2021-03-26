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
from os.path import dirname, abspath
import shutil
import ntpath
# For getting file creation timestamp
import platform
import pathlib
# For detecting new files
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
# For AWS S3
import boto3
from botocore.exceptions import ClientError
# For logging remotely to AWS CloudWatch
from boto3.session import Session
import watchtower
# QR decoding
from PIL import Image
from pyzbar.pyzbar import decode

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
    return datetime.fromtimestamp(creation_date(file_path)).astimezone().isoformat()

def get_metadata(file_path):
    metadata = {"Metadata": {}}
    metadata["Metadata"]["user_input_filename"] = os.path.basename(file_path)
    try:
        metadata["Metadata"]["file_created"] = get_file_created(file_path)
    except:
        pass
    return metadata

def upload_file(s3_client, file_name, bucket, object_name, print_progress=False):
    """Upload a file to an S3 bucket and include special metadata
    :param s3_client: Initialized S3 client to use
    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. Also known as a "Key" in S3 bucket terms.
    :param print_progress: Optional, prints upload progress if True
    """
    s3_client.upload_file(file_name, bucket, object_name, 
        Callback=ProgressPercentage(file_name) if print_progress else None,
        ExtraArgs=get_metadata(file_name))

def generate_bucket_key(file_path, s3_directory):
    """Keep things nice and random to prevent collisions
    "/Users/russell/Documents/taco_tuesday.jpg" becomes "raw/taco_tuesday-b94b0793-6c74-44a9-94e0-00420711130d.jpg"
    Note: We still like to keep the basename because some files' only timestamp is in the filename
    """
    root_ext = os.path.splitext(ntpath.basename(file_path));
    return s3_directory + root_ext[0] + "-" + str(uuid.uuid4()) + root_ext[1];

def delete_directory_if_empty_or_hidden(directory):
    all_hidden = True
    files = os.listdir(directory)
    for file in files:
        if file[0] != '.':
            all_hidden = False
    if all_hidden:
        try:
            for file in files:
                os.remove(os.path.join(directory, file))
            os.rmdir(directory)
        except:
            pass

def move(src_path, dst_path, src_root=None):
    """Move file from src_path to dst_path, creating new directories from dst_path 
    along the way if they don't already exist.     
    Avoids collisions if file already exists at dst_path by adding "(#)" if necessary, where # is a number
    (Formatted the same way filename collisions are resolved in Google Chrome downloads)

    If src_root is specified, then the function will try to delete the directory of src_path
    if it is not src_root and it is empty or only contains hidden files. (The hidden files will be deleted).
    If src_root is not actually a parent directory of src_path, deletion will never take place. 
    """
    root_ext = os.path.splitext(dst_path)
    i = 0
    while os.path.isfile(dst_path):
        # Recursively avoid the collision
        i += 1
        dst_path = root_ext[0] + " ({})".format(i) + root_ext[1]
    # Move file, make directories if needed
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    shutil.move(src_path, dst_path)
    # Delete directory if necessary (recursively)
    directory = os.path.dirname(src_path)
    while (src_root is not None and src_path.startswith(src_root) and directory != src_root):
        delete_directory_if_empty_or_hidden(directory)
        directory = os.path.dirname(directory)

def make_parallel_path(src_dir, dst_dir, src_path, add_date_subdir=True):
    """Creates a parallel path of src_path using dst_dir instead of src_dir
    as the prefix. If add_date_subdir is True, uses dst_dir/(today's date in "YYYY-MM-DD" format)/
    as the new prefix instead.

    src_dir should be a prefix of src_path, else error
    """
    # Remove prefix
    prefix = src_dir
    if src_path.startswith(prefix):
        suffix = src_path[len(prefix)+1:]
    else:
        raise Exception("src_dir {} was not a prefix of src_path {}".format(src_dir, src_path))

    # Add prefix
    result = dst_dir
    if add_date_subdir:
        result = os.path.join(result, datetime.today().strftime('%Y-%m-%d'))
    result = os.path.join(result, suffix)
    return result

def qr_code_valid(lambda_arn, lambda_client, qr_code, upload_device_id):
    d = {
        "qr_code" : qr_code,
        "upload_device_id" : upload_device_id
    }   
    response = lambda_client.invoke(
        FunctionName=lambda_arn,
        LogType='None',
        Payload=json.dumps(d)
    )
    payload = json.loads(response['Payload'].read())
    return payload['qr_code_valid']

def get_qr_codes(image_path):
    qr_codes = [qr_object.data.decode() for qr_object in decode(Image.open(image_path))]
    return qr_codes

def process(file_path, s3_client, bucket, bucket_dir, done_dir, error_dir, unprocessed_dir,
    lambda_client, upload_device_id, lambda_arn, log_info=True):
    """Name, upload, move file
    """
    logger = logging.getLogger(__name__)
    object_name = generate_bucket_key(file_path, bucket_dir)
    try:
        # Preflight business
        # QR code if present
        qr_codes = [] # All QR codes present in the image, NOT the assigned QR code used for matching
        correct = False
        try:
            qr_codes = get_qr_codes(file_path)
            for qr_code in qr_codes:
                if qr_code_valid(lambda_arn, lambda_client, qr_code, upload_device_id):
                    correct = True
                    break
        except:
            pass

        if correct is False:
            # Try the name this time
            filename = os.path.basename(file_path)
            potential = filename.split(".")[-2]
            if not qr_code_valid(lambda_arn, lambda_client, potential, upload_device_id):
                raise Exception("Invalid filename {} doesn't have a QR code or filename that matches a container_id".format(plant_or_container_id))


        # Actual upload
        upload_file(s3_client, file_path, bucket, object_name)
        done_path = make_parallel_path(unprocessed_dir, done_dir, file_path)
        move(file_path, done_path, src_root=unprocessed_dir)
        if log_info:
            logger.info("S3 Desktop Uploader: Successfully uploaded {} to {} as {}".format(file_path, bucket, object_name))
    except Exception as e:
        if log_info:
            logger.exception("S3 Desktop Uploader: Failed to upload {}: {}".format(file_path, str(e)))
        error_path = make_parallel_path(unprocessed_dir, error_dir, file_path)
        move(file_path, error_path)

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
    logger = logging.getLogger(__name__)
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
        self._seen_so_far += bytes_amount
        percentage = (self._seen_so_far / self._size) * 100
        # Print instead of log because this gets kind of spammy
        print("Uploading status for {}: {} / {} ({}%)".format(self._filename, self._seen_so_far, self._size, percentage))

class S3EventHandler(FileSystemEventHandler):
    """Handler for what to do if watchdog detects a filesystem change
    """

    def __init__(self, s3_client, s3_bucket, s3_bucket_dir, unprocessed_dir, done_dir, error_dir, 
        lambda_client, upload_device_id, lambda_arn):

        self.s3_client = s3_client
        self.s3_bucket = s3_bucket
        self.s3_bucket_dir = s3_bucket_dir
        self.unprocessed_dir = unprocessed_dir
        self.done_dir = done_dir
        self.error_dir = error_dir
        self.lambda_client = lambda_client
        self.upload_device_id = upload_device_id
        self.lambda_arn = lambda_arn

    def on_created(self, event):
        is_file = not event.is_directory
        if is_file:
            process(event.src_path, self.s3_client, self.s3_bucket, self.s3_bucket_dir, 
                self.done_dir, self.error_dir, self.unprocessed_dir,
                self.lambda_client, self.upload_device_id, self.lambda_arn)
        else:
            # Crawl the new directory and process everything in it
            file_paths = get_preexisting_files(event.src_path)
            for file_path in file_paths:
                process(file_path, self.s3_client, self.s3_bucket, self.s3_bucket_dir, 
                    self.done_dir, self.error_dir, self.unprocessed_dir,
                    self.lambda_client, self.upload_device_id, self.lambda_arn)

def main(use_cloudwatch=True):
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    d = dirname(dirname(abspath(__file__)))
    config = yaml.safe_load(open(os.path.join(d, "config.yml")))
    s3_client = boto3.client('s3')
    bucket = config["s3"]["bucket"]
    bucket_dir = config["s3"]["bucket_dir"]
    unprocessed_dir = config["unprocessed_dir"]
    done_dir = config["done_dir"]
    error_dir = config["error_dir"]
    lambda_client = boto3.client('lambda')
    upload_device_id = config["upload_device_id"]
    lambda_arn = config["lambda_arn"]

    # Setup remote logging
    if use_cloudwatch:
        watchtower_handler = watchtower.CloudWatchLogHandler(
            log_group=config["cloudwatch"]["log_group"],
            stream_name=config["cloudwatch"]["stream_name"],
            send_interval=config["cloudwatch"]["send_interval"],
            create_log_group=False
        )
        logger.addHandler(watchtower_handler)

    # Check for any preexisting files in the "unprocessed" folder
    preexisting = get_preexisting_files(unprocessed_dir)

    # Setup the watchdog handler for new files that are added while the script is running
    event_handler = S3EventHandler(s3_client, bucket, bucket_dir, unprocessed_dir, done_dir, error_dir,
        lambda_client, upload_device_id, lambda_arn)
    observer = Observer()
    observer.schedule(event_handler, unprocessed_dir, recursive=True)
    observer.start()

    # Upload & process any preexisting files
    for file_path in preexisting:
        process(file_path, s3_client, bucket, bucket_dir, done_dir, error_dir, unprocessed_dir, 
            lambda_client, upload_device_id, lambda_arn)

    # Keep the main thread running so watchdog handler can be still be called
    keep_running(observer, config["send_heartbeat"], config["heartbeat_seconds"])

if __name__ == "__main__":
    main()

# FUTURE TODO: Discover whether it's necessary to renew the boto3 client after some time
# (https://stackoverflow.com/questions/63724485/how-to-refresh-the-boto3-credetials-when-python-script-is-running-indefinitely)
# FUTURE TODO: Discover whether single-threaded upload is too slow and whether multithreading is necessary here
# (Note that setting Config to something like=boto3.s3.transfer.TransferConfig(max_concurrency=5, use_threads=True)
# doesn't seem to have a multithreading effect for some reason)
