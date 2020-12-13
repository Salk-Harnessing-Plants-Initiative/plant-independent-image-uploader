"""
Salk Harnessing Plants Initiative
Python script for uploading files to AWS S3 bucket
Russell Tran
December 2020
"""

# https://stackoverflow.com/a/64261864/14775744
# https://blog.magrathealabs.com/filesystem-events-monitoring-with-python-9f5329b651c3

import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler

if __name__ == "__main__":
	print("YELLO")
	logging.basicConfig(level=logging.INFO,
		format='%(asctime)s - %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S')
	path = sys.argv[1] if len(sys.argv) > 1 else '.'
	event_handler = LoggingEventHandler()
	observer = Observer()
	observer.schedule(event_handler, path, recursive=True)
	observer.start()
	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		observer.stop()
		observer.join()