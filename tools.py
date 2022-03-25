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

import os, threading, Queue, time, yaml, shutil, smtplib
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from datastore import get_datastore
from database import fetch_clinical_trials, fetch_patient_finished_treatment, fetch_patient_has_4d

import os, subprocess

import logging
logger = logging.getLogger(__name__)

# Return true is the XVI application is currently running
def is_xvi_running():
    if os.name == 'nt':
        processes = subprocess.check_output('tasklist', shell=True)
        if "SRI.exe" in processes:
            return True
            
    return False

# Get the size of a directory and all containing files (including all subdirs)
def get_size(start_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size
    
def send_email_report(directories, archived, deleted, errors, job_start, job_finish, log_file_name):

    datastore = get_datastore()
    email_reports_config = datastore['email_reports_config']
        
    msg = MIMEMultipart()
    msg['Subject'] = email_reports_config['name'] + ' XVI Clean Up Report'
    
    delete_dirs = [d for d in directories if d['action'] == 'DELETE']

    text = 'This is an automatically generated report. For more information on the XVI Archive Tool and instructions for use, see: http://physwiki/tiki-index.php?page=XVI+Archive+Tool\n\n'
    
    text += 'The automated XVI clean up job ran from ' + job_start + ' to ' + job_finish + '\n\n'
    
    if len(errors) == 0:
        text += 'No errors occurred while running the scheduled job.\n'
    else:
        text += 'The following errors occurred while running the scheduled job!!!\n'
        
        for error in errors:
            text += ' - ' + error + '\n'
    
    text += '\n'
    
    if len(delete_dirs) > 0:
        text += 'The following patients may be deleted from XVI:\n'
        text += 'MRN\t\tName\n'
        for d in delete_dirs:
            text += d['mrn'] + '\t' + d['name'] + '\n'
            
    else:
        text += 'No patients were detected for deletion\n'
       
    text += '\n'
    
    if archived:
        text += 'The following patients were archived and may be marked as inactive (do not delete) within XVI:\n'
        text += 'MRN\t\tName\n'
        for d in archived:
            text += d['mrn'] + '\t' + d['name'] + '\n'
        text += '\nImportant: Patients listed as archived will not appear on subsequent email reports!\n\n'
    else:
        text += 'No patients were archived\n\n'
        
    # Attach the log file
    try:
        with open(log_file_name, "rb") as fil:
            part = MIMEApplication(fil.read(), Name=os.path.basename(log_file_name))
            
        # Attach the file after it is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(log_file_name)
        msg.attach(part)
        text += 'The XVI archive tool log file has been attached to this email.\n'
    except:
        text += 'An error occurred attaching the XVI Archive Tool log file to this email.\n'
         
    msg_text = MIMEText(text)
    msg.attach(msg_text)   
    
    for email_address in email_reports_config['email_addresses']:
        msg['From'] = email_reports_config['from']
        msg['To'] = email_address
        
        # Send the message via the configured SMTP server
        s = smtplib.SMTP(email_reports_config['host'], email_reports_config['port'])

        if 'user' in email_reports_config and len(email_reports_config['user']) > 0:
            s.login(email_reports_config['user'], email_reports_config['password'])
        s.sendmail(email_reports_config['from'], [email_address], msg.as_string())
        s.quit()
        
        logger.info('Email Report sent to: ' + email_address)

def backup_xvi_sql():

    datastore = get_datastore()

    # Directory to backup files
    backup_dir = os.path.join(datastore['archive_path'],'backup')
    back_dir_name = os.path.join(backup_dir,datetime.today().strftime('%Y-%m-%d_%H_%M_%S'))
    try:
        # Python 3
        os.makedirs(back_dir_name, exist_ok=True) # > Python 3.2
    except TypeError:
        # Python 2
        try:
            os.makedirs(back_dir_name)
        except OSError:
            if not os.path.isdir(back_dir_name):
                raise
                    
    for p in datastore['xvi_paths']:

        back_files = [f for f in os.listdir(p) if f.endswith(".mdf") or f.endswith(".ldf")]
        
        for f in back_files:
            src = os.path.join(p,f)
            dst = os.path.join(back_dir_name,f)
            shutil.copyfile(src, dst)
            logger.info('%s backed up to %s', src, dst)
            
    # Clean out any old backup files
    dirs = [d for d in os.listdir(backup_dir) if os.path.isdir(os.path.join(backup_dir,d))]
    for d in dirs:
        mod_date = datetime.strptime(time.ctime(os.path.getmtime(os.path.join(backup_dir,d))), "%a %b %d %H:%M:%S %Y")
        
        # If the directory is older than 60 days then delete it
        if mod_date < datetime.now()-timedelta(days=60):
            shutil.rmtree(os.path.join(backup_dir,d))


class ScanPathsTask(threading.Thread):

    def __init__(self, queue, quick_scan):
        threading.Thread.__init__(self)
        self.queue = queue
        self.quick_scan = quick_scan
        self.abort = False

    def stop(self):
        self.abort = True
        logger.info('Stopping location scan')

    def run(self):

        self.directories = []

        # Scan the XVI Locations
        logger.info('Scanning locations')
        self.get_directories()

        # Get info for patients found in scan
        logger.info('Fetching patient info')
        self.fetch_patient_info()

        # If the scan was cancelled return an empty list
        if self.abort:
            self.queue.put([])

            return

        # Place the actioned directories into the queue as a final step
        self.queue.put(self.directories)


    # Get the directories in the configured locations and determine if they are a valid
    # patient directory or not
    def get_directories(self):

        datastore = get_datastore()

        for p in datastore['xvi_paths']:

            try:
                dirs = [d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d))]
            except:
                continue
            for d in dirs:

                if self.abort:
                    break

                patient = {}
                patient['path'] = p
                patient['dir_name'] = d
                patient['action'] = 'KEEP'
                patient['finished_treatment'] = False
                patient['clinical_trial'] = False
                patient['has_4d'] = False
                patient['last_fraction_date'] = ""

                if self.quick_scan:
                    patient['dir_size'] = 0
                else:
                    patient['dir_size'] = get_size(os.path.join(p, d))

                # Check if this is a patient directory
                dir_split = d.split('_')

                try:
                    if dir_split[0].lower() == 'patient' and len(dir_split[1]) == 7:
                        patient['mrn'] = dir_split[1]
                        patient['name'] = ''

                        # Ignore if in list of MRNs to ignore
                        if patient['mrn'] in datastore['ignore_mrns']:
                            patient['action'] = 'IGNORE'
                    else:
                        # Not a patient directory
                        patient['action'] = 'IGNORE'
                except:
                    # Not a patient directory
                    patient['action'] = 'IGNORE'

                self.directories.append(patient)

        logger.info('Found %d Directories',len(self.directories))
        logger.debug('Patient Directories: ' + str(self.directories))

    # Determine if directories contain data for patients who have:
    # - finished their treatment
    # - are on a clinical trial
    # - have some 4D cone beam data
    def fetch_patient_info(self):

        if self.abort:
            return

        mrns = "','".join([p['mrn'] for p in self.directories if 'mrn' in p])

        finished_treatment = fetch_patient_finished_treatment(mrns)
        clinical_trials = fetch_clinical_trials(mrns)
        has_4d = fetch_patient_has_4d(mrns)

        # If finished_treatment returns None, then OIS probably isn't configured
        if finished_treatment == None:
            self.queue.put({'error' : 'Could not query OIS', 'msg' : 'OIS could not be queried. Check connection settings.' })
            return

        for p in self.directories:

            if self.abort:
                break

            if p['action'] == 'IGNORE':
                continue

            # Get all finished_treatment fields for this patient
            patient_finished_treatment = [ft for ft in finished_treatment if ft['IDA'] == p['mrn']]

            # If there are no fields for this patient, assume they are still being treated,
            # otherwise assume finished for now
            if len(patient_finished_treatment) > 0:
                p['finished_treatment'] = True

            # Iterate over each of the patients treatment fields, to determine the last field
            # and whether or not their treatment is finished
            for ft in patient_finished_treatment:

                # Assign the name field
                p['name'] = ft['Last_Name'] + ' ' + ft['First_Name'] + ' ' + ft['MIddle_Name']

                # If a fields last_fraction_date has already been assigned update it if this one is newer
                if type(p['last_fraction_date']) == datetime:
                    if ft['last_fraction_date'] > p['last_fraction_date']:
                        p['last_fraction_date'] = ft['last_fraction_date']
                else:
                    p['last_fraction_date'] = ft['last_fraction_date']

                # If the prescribed fractions doesn't match the delivered fractions for this field, then
                # the treatment is not finished
                if not ft['presc_fractions'] == ft['deliv_fractions']:
                    p['finished_treatment'] = False

            # If the last fraction date was within the last 2 weeks, do not mark the treatment as finished
            if type(p['last_fraction_date']) == datetime:
                if datetime.now()-timedelta(days=14) <= p['last_fraction_date']:
                    p['finished_treatment'] = False


            # Get any clinical trials for this patiet
            patient_clinical_trials = [ct for ct in clinical_trials if ct['IDA'] == p['mrn']]

            # If there are any clinical trials then flag for this patient
            if len(patient_clinical_trials) > 0:
                p['clinical_trial'] = True
                p['name'] = patient_clinical_trials[0]['Last_Name'] + ' ' + patient_clinical_trials[0]['First_Name'] + ' ' + patient_clinical_trials[0]['MIddle_Name']

            # Get the 4D entries for this patient
            patient_has_4d = [h4 for h4 in has_4d if h4['IDA'] == p['mrn']]

            # If there are any 4D entires then flag for this patient
            if len(patient_has_4d) > 0:
                p['has_4d'] = True
                p['name'] = patient_has_4d[0]['Last_Name'] + ' ' + patient_has_4d[0]['First_Name'] + ' ' + patient_has_4d[0]['MIddle_Name']

            # Set the action for this patient directory based on the flags just set
            if p['finished_treatment']:

                if p['clinical_trial'] or p['has_4d']:
                    p['action'] = 'ARCHIVE'
                else:
                    p['action'] = 'DELETE'


        logger.debug('Patient Directories: ' + str(self.directories))


class PerformActionTask(threading.Thread):

    def __init__(self, queue, patients, action):
        threading.Thread.__init__(self)
        self.queue = queue
        self.patients = patients
        self.action = action
        self.abort = False

    def stop(self):
        self.abort = True

    def run(self):

         # Set True for testing and no data will be copied or deleted
        dry_run = False

        datastore = get_datastore()
        
        # Just double check that these patients are really for this action
        dirs = [d for d in self.patients if d['action'] == self.action]
        
        # Before performing action, backup any XVI SQL files (if there are patients being actioned)
        if len(dirs) > 0:
            backup_xvi_sql()

        actioned_dirs = []

        for d in dirs:

            if self.abort:
                break

            src = os.path.join(d["path"],d["dir_name"])

            # If archive action, first copy the directory

            if self.action == "ARCHIVE":

                dst = os.path.join(datastore['archive_path'],d["dir_name"])

                # Copy the directory recursively to the destination. If the destination directory already exists,
                # or another exception occurs, alert the user and skip this directory
                try:
                    if not dry_run:
                        shutil.copytree(src, dst)
                    else:
                        time.sleep(2)

                    logger.info('%s copied to %s', src, dst)
                except Exception as e:
                    logging.exception("Exception while copying %s to %s", src, dst)
                    error_msg = "The following error occurred while copying from\n" + src + "\nto\n" + dst + "\n\n" + str(e) + "\n\nThe patient directory has not be deleted."
                    logger.error(error_msg)
                    self.queue.put(d["mrn"] + " - " + d['name'] + ": Error copying to " + dst + " - " + str(e))
                    continue

                # Compute the size of the src and dst directories and ensure they are equal
                src_size = get_size(src)
                dst_size = get_size(dst)

                logger.info('Src (%s) size is %s', src, src_size)
                logger.info('Dst (%s) size is %s', dst, dst_size)

                if not src_size == dst_size and not dry_run:
                    logger.error("Directory sizes do not match after copy from %s to %s", src, dst)
                    error_msg = "The following error occurred while copying from\n" + src + "\nto\n" + dst + "\n\n Directory sizes do not match after copy. \n\nThe patient directory has not be deleted."
                    logger.error(error_msg)
                    self.queue.put(d["mrn"] + " - " + d['name'] + ": Error: Src and Dst directory sizes do not match.")
                    continue

                logger.info('%s same size as %s', src, dst)


            # Now delete the src directory
            try:
                if not dry_run:
                    shutil.rmtree(src)
                else:
                    time.sleep(2)

            except Exception as e:
                logging.exception("Exception while deleting %s", src)
                error_msg = "The following error occurred while deleting\n" + src + "\n\n" + str(e) + "\n\nThe patient directory has potentially been partially deleted, however the copy to the archive location was successful."
                logger.error(error_msg)
                self.queue.put(d["mrn"] + " - " + d['name'] + ": Error deleting " + str(e))
                continue

            logger.info('%s has been deleted', src)

            if self.action == "ARCHIVE":
                self.queue.put(d["mrn"] + " - " + d['name'] + ": Successfully Archived to " + dst)
            elif self.action == "DELETE":
                self.queue.put(d["mrn"] + " - " + d['name'] + ": Successfully Deleted")

            # Directory successfully actioned
            actioned_dirs.append(d)

            # Update actioned.yaml with directory
            date = datetime.now().strftime("%Y-%m-%d")
            archived = []
            deleted = []

            try:
                with open('actioned.yaml', 'r') as f:

                    previous = yaml.load(f)

                    if previous['ARCHIVED']:
                        archived = previous['ARCHIVED']

                    if previous['DELETED']:
                        deleted = previous['DELETED']
            except:
                # No previous patients actioned
                pass

            if d['action'] == 'ARCHIVE':
                archived.append(d['mrn'] + " on " + date)
            elif d['action'] == 'DELETE':
                deleted.append(d['mrn'] + " on " + date)

            actioned = { 'ARCHIVED': archived, 'DELETED' : deleted }
            with open('actioned.yaml', 'w') as f:
                yaml.dump(actioned, f, default_flow_style=False)

        # Place the actioned directories into the queue as a final step
        self.queue.put(actioned_dirs)
