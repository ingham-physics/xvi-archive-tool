#!/usr/bin/python

# Copyright 2022 University of New South Wales, Ingham Institute

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    # Python 2
    import Tkinter  as tk
    import tkMessageBox as messagebox
except ImportError:
    # Python 3
    import tkinter as tk
    from tkinter import messagebox

from application import MainApplication

from datastore import get_datastore, set_datastore

import datetime, logging, sys, os, decimal, subprocess, yaml, Queue

from optparse import OptionParser

from tools import ScanPathsTask, PerformActionTask, send_email_report, is_xvi_running

# Load the release info to log the current version number
try:
    with open('release.yaml', 'r') as f:
        release_info = yaml.load(f)
except IOError as e:
        release_info = {}

# Log to file and stdout
log_file_name = 'logs/'+datetime.datetime.today().strftime('%Y')+'/'+datetime.datetime.today().strftime('%m')+'/XVI_ARCHIVE_'+datetime.datetime.today().strftime('%Y-%m-%d_%H_%M_%S')+'.log'
try:
    # Python 3
    os.makedirs(os.path.dirname(log_file_name), exist_ok=True) # > Python 3.2
except TypeError:
    # Python 2
    try:
        os.makedirs(os.path.dirname(log_file_name))
    except OSError:
        if not os.path.isdir(os.path.dirname(log_file_name)):
            raise

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename=log_file_name,
                    filemode='w')

# define a new Handler to log to console as well
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logger = logging.getLogger('')
logger.addHandler(console)

# If a log file path has been configured, also store a log file there
try:
    datastore = get_datastore()
    
    log_path = os.path.join(datastore['log_path'],log_file_name)
    try:
        # Python 3
        os.makedirs(os.path.dirname(log_path), exist_ok=True) # > Python 3.2
    except TypeError:
        # Python 2
        try:
            os.makedirs(os.path.dirname(log_path))
        except OSError:
            if not os.path.isdir(os.path.dirname(log_path)):
                raise
            
    path_handler = logging.FileHandler(log_path)
    path_handler.setLevel(logging.DEBUG)
    path_handler.setFormatter(formatter)
    logger.addHandler(path_handler)
    
except Exception as e:
    # No log file path configured
    pass

try:
    logger.info('XVI Archive Tool. Version: ' + release_info['version'])
except KeyError as e:
    logger.warn('XVI Archive Tool. Release metadata not found!')

# If running main function, launch MainApplication window
if __name__ == "__main__":

    usage = "usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option('--auto-run',
                      dest="auto_run",
                      default=False,
                      action="store_true",
                      )
    parser.add_option('--shutdown',
                      dest="shutdown",
                      default=False,
                      action="store_true",
                      )
    parser.add_option('--perform-archive',
                      dest="perform_archive",
                      default=False,
                      action="store_true",
                      )
    options, remainder = parser.parse_args()
    perform_archive = options.perform_archive
    auto_run = options.auto_run
    shutdown = options.shutdown
    
    logger.info('Will automatically perform archive operation: ' + str(perform_archive))
    
    if auto_run:
        
        job_start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
        logger.info('Will scan locations now')

        errors = []
        
        queue = Queue.Queue()
        scan_task = ScanPathsTask(queue, True) # Do this as a quick scan since file sizes aren't used
        scan_task.start()
        scan_task.join()
        
        logger.info('Finished scanning locations')
        
        archived_dirs = None
        for q in range(queue.qsize()):
            msg = queue.get(0) # Always get 0 because its a queue so FIFO
    
            # If the msg is a list then its returning the list of directories
            if type(msg) == list:
    
                directories = msg
                
                dirs_ignored = [d for d in directories if d['action'] == 'IGNORE']
                dirs_to_keep = [d for d in directories if d['action'] == 'KEEP']
                dirs_to_archive = [d for d in directories if d['action'] == 'ARCHIVE']
                dirs_to_delete = [d for d in directories if d['action'] == 'DELETE']
            
                logger.info('Directories to archive: ' + str(len(dirs_to_archive)))
                logger.info('Directories to delete: ' + str(len(dirs_to_delete)))
                logger.info('Directories to keep: ' + str(len(dirs_to_keep)))
                logger.info('Directories ignored: ' + str(len(dirs_ignored)))
                logger.info('Scanned ' + str(len(directories)) + ' directories.')
                
                if perform_archive:
                    # First check that the XVI process isn't running,
                    # If it is alert the user and abort the action
                    if is_xvi_running():
                        errors.append('XVI application running: The XVI application was not closed so the archive was unable to be run. Ensure that the XVI application is closed before scheduled run.')
                        break
                        
                    # Also make sure a valid archive path has been setup
                    datastore = get_datastore()
                    if not 'archive_path' in datastore or not os.path.exists(datastore['archive_path']):
                        errors.append('Archive Path missing: The path to the archive destination is missing. Make sure the archive directory exists and that the network location is available.')
                        break
                    
                    # Run the archive job task
                    queue = Queue.Queue()
                    action_task = PerformActionTask(queue, dirs_to_archive, 'ARCHIVE')
                    action_task.start()
                    action_task.join()
                    
                    for q in range(queue.qsize()):
                        msg = queue.get(0) # Always get 0 because its a queue so FIFO
            
                        # If the msg is a list, we know this was the last item
                        if type(msg) == list:
                            archived_dirs = msg
            
                    if archived_dirs == None:
                        errors.append('Archive Failed: An unknown error occurred during archiving of data. Please report this to the Medical Physics team for investigation.')
                        
            elif type(msg) == dict:
                # if it's a dict then its returning an error message to log
                logger.error('The following error occurred while scanning the directories')
                logger.error(msg['error'])
                logger.error(msg['msg'])
                errors.append(msg['error'] + ': ' + msg['msg'])
        
        job_finish = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        send_email_report(directories, archived_dirs, None, errors, job_start, job_finish, log_file_name)
        
        # Shutdown the system if requested
        if shutdown:
            logger.info('Will now shutdown the system')
            os.system('shutdown -s')
    
        sys.exit()

    try:
        root = tk.Tk()
        root.title('XVI Archive Tool')
        root.geometry('1000x600')

        MainApplication(root).pack(side="top", fill="both", expand=True)

        root.mainloop()

    except Exception as e:

        logging.exception("XVI Archive Crash")
        messagebox.showerror("Error", "An exception has occurred and the application must close: " + type(e).__name__)
