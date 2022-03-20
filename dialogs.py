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
    import ttk
    import tkFileDialog as filedialog
    import tkMessageBox as messagedialog
    import tkSimpleDialog as simpledialog
except ImportError:
    # Python 3
    import tkinter as tk
    from tkinter import ttk
    from tkinter import filedialog
    from tkinter import simpledialog

from datastore import get_datastore, set_datastore
from tools import PerformActionTask, is_xvi_running

import os, subprocess, datetime
import Queue
import yaml

# Dialog to configure the XVI Paths to scan
class XVIPathsDialog:

    def __init__(self, parent):

        self.top = tk.Toplevel(parent)
        self.top.title('Configure XVI Paths')
        self.top.geometry('480x360')
        self.top.update()
        self.top.minsize(self.top.winfo_width(), self.top.winfo_height())
        self.top.resizable(False, False)
        self.top.focus_set()
        self.top.grab_set()

        tk.Label(self.top,text='XVI directory locations').grid(row=0, columnspan=2, padx=5, pady=5)

        self.listbox_paths = tk.Listbox(self.top)
        self.listbox_paths.grid(row=1, columnspan=2, padx=(5,0), pady=5, sticky='news')

        vsb = ttk.Scrollbar(self.top, orient="vertical", command=self.listbox_paths.yview)
        vsb.grid(row=1, column=2, sticky=("N", "S", "E", "W"), padx=(0,10), pady=(5, 5))
        self.listbox_paths.configure(yscrollcommand=vsb.set)

        datastore = get_datastore()
        for p in datastore['xvi_paths']:
            self.listbox_paths.insert(tk.END, p)

        tk.Button(self.top,text='Add Path',command=self.add_xvi_path, width=20).grid(row=2, column=0, padx=5, pady=5)
        tk.Button(self.top,text='Remove Selected Path',command=self.remove_xvi_path, width=20).grid(row=2, column=1, padx=5, pady=5)

        self.top.columnconfigure(0, weight=1)
        self.top.columnconfigure(1, weight=1)
        self.top.rowconfigure(1, weight=1)

        self.top.attributes("-topmost", True)

    # Add a new path to the list and datastore
    def add_xvi_path(self):
        self.directory = os.path.normpath(filedialog.askdirectory(parent=self.top))

        datastore = get_datastore()
        datastore['xvi_paths'].append(self.directory)
        set_datastore(datastore)

        self.listbox_paths.insert(tk.END, self.directory)

    # Remove a path from the list and datastore
    def remove_xvi_path(self):

        datastore = get_datastore()

        selected_indexes = self.listbox_paths.curselection()

        for ind in selected_indexes:
            datastore['xvi_paths'].pop(int(ind))
            self.listbox_paths.delete(int(ind))

        set_datastore(datastore)

# Dialog to configure the Mosaiq connection parameters
class MosaiqConnectionDialog:

    def __init__(self, parent):

        self.top = tk.Toplevel(parent)
        self.top.title('Configure Mosaiq')
        self.top.geometry('450x300')
        self.top.update()
        self.top.focus_set()
        self.top.grab_set()

        self.top.columnconfigure(0, weight=1)
        self.top.columnconfigure(1, weight=3)

        self.top.attributes("-topmost", True)

        tk.Label(self.top, text='Configure the connection parameters for Mosaiq').grid(row=0, columnspan=2, padx=5, pady=5, sticky='EW')

        tk.Label(self.top, text='Host:').grid(row=1, sticky='EW', padx=5, pady=5)
        tk.Label(self.top, text='Username:').grid(row=2, sticky='EW', padx=5, pady=5)
        tk.Label(self.top, text='Password:').grid(row=3, sticky='EW', padx=5, pady=5)
        tk.Label(self.top, text='Database:').grid(row=4, sticky='EW', padx=5, pady=5)

        self.txt_host = tk.Entry(self.top)
        self.txt_user = tk.Entry(self.top)
        self.txt_pass = tk.Entry(self.top)
        self.txt_db = tk.Entry(self.top)

        datastore = get_datastore()
        try:
            self.txt_host.insert(0,datastore['mosaiq_config']['host'])
            self.txt_user.insert(0,datastore['mosaiq_config']['user'])
            self.txt_pass.insert(0,datastore['mosaiq_config']['pass'])
            self.txt_db.insert(0,datastore['mosaiq_config']['db'])
        except Exception as e:
            # No mosaiq_config in datastore yet
            pass

        self.txt_host.grid(row=1, column=1, padx=5, sticky='EW')
        self.txt_user.grid(row=2, column=1, padx=5, sticky='EW')
        self.txt_pass.grid(row=3, column=1, padx=5, sticky='EW')
        self.txt_db.grid(row=4, column=1, padx=5, sticky='EW')

        tk.Button(self.top,text='Save',command=self.save_configuration, width=15).grid(row=5, columnspan=2, padx=5, pady=5)

    # Save parameters to the datastore
    def save_configuration(self):

        datastore = get_datastore()

        mosaiq_config = {}
        mosaiq_config['host'] = self.txt_host.get()
        mosaiq_config['user'] = self.txt_user.get()
        mosaiq_config['pass'] = self.txt_pass.get()
        mosaiq_config['db'] = self.txt_db.get()

        datastore['mosaiq_config'] = mosaiq_config

        set_datastore(datastore)

        self.top.destroy()


# Dialog to configure MRNs to ignore
class IgnoreMRNsDialog:

    def __init__(self, parent):

        self.top = tk.Toplevel(parent)
        self.top.title('Ignore MRNs')
        self.top.geometry('480x360')
        self.top.update()
        self.top.minsize(self.top.winfo_width(), self.top.winfo_height())
        self.top.resizable(False, False)
        self.top.focus_set()
        self.top.grab_set()

        self.top.attributes("-topmost", True)

        tk.Label(self.top,text='Directories matching these MRNs will be ignored (from next scan)', wraplength=480).grid(row=0, columnspan=2, padx=5, pady=5)

        self.listbox_mrns = tk.Listbox(self.top)
        self.listbox_mrns.grid(row=1, columnspan=2, padx=(5,0), pady=5, sticky='news')

        vsb = ttk.Scrollbar(self.top, orient="vertical", command=self.listbox_mrns.yview)
        vsb.grid(row=1, column=2, sticky=("N", "S", "E", "W"), padx=(0,10), pady=(5, 5))
        self.listbox_mrns.configure(yscrollcommand=vsb.set)

        datastore = get_datastore()
        for p in datastore['ignore_mrns']:
            self.listbox_mrns.insert(tk.END, p)

        tk.Button(self.top,text='Add MRN',command=self.add_mrn, width=15).grid(row=2, column=0, padx=5, pady=5)
        tk.Button(self.top,text='Remove MRN',command=self.remove_mrn, width=15).grid(row=2, column=1, padx=5, pady=5)

        self.top.columnconfigure(0, weight=1)
        self.top.columnconfigure(1, weight=1)
        self.top.rowconfigure(1, weight=1)

    # Add a new MRN to the list and datastore
    def add_mrn(self):
        mrn = simpledialog.askstring('MRN', 'Enter MRN to ignore', parent=self.top)

        if not mrn == None and len(mrn) > 0:
            datastore = get_datastore()
            datastore['ignore_mrns'].append(mrn)
            set_datastore(datastore)

            self.listbox_mrns.insert(tk.END, mrn)

    # Remove an MRN from the list and datastore
    def remove_mrn(self):

        datastore = get_datastore()

        selected_indexes = self.listbox_mrns.curselection()

        for ind in selected_indexes:
            datastore['ignore_mrns'].pop(ind)
            self.listbox_mrns.delete(ind)

        set_datastore(datastore)
        
        
# Dialog to configure sending of Email Reports
class EmailReportsDialog:

    def __init__(self, parent):

        self.top = tk.Toplevel(parent)
        self.top.title('Email Reports')
        self.top.geometry('580x520')
        self.top.update()
        self.top.minsize(self.top.winfo_width(), self.top.winfo_height())
        self.top.resizable(False, False)
        self.top.focus_set()
        self.top.grab_set()

        self.top.attributes("-topmost", True)

        tk.Label(self.top,text='Configure Email reports to send for schedule runs (command line)', wraplength=480).grid(row=0, columnspan=2, padx=5, pady=5)

        tk.Label(self.top, text='This Machine Name:').grid(row=1, sticky='EW', padx=5, pady=5)
        tk.Label(self.top, text='SMTP Server Host:').grid(row=2, sticky='EW', padx=5, pady=5)
        tk.Label(self.top, text='SMTP Server Port:').grid(row=3, sticky='EW', padx=5, pady=5)
        tk.Label(self.top, text='Send Emails From:').grid(row=4, sticky='EW', padx=5, pady=5)

        self.txt_name = tk.Entry(self.top)
        self.txt_host = tk.Entry(self.top)
        self.txt_port = tk.Entry(self.top)
        self.txt_from = tk.Entry(self.top)

        datastore = get_datastore()
        try:
            self.txt_name.insert(0,datastore['email_reports_config']['name'])
            self.txt_host.insert(0,datastore['email_reports_config']['host'])
            self.txt_port.insert(0,datastore['email_reports_config']['port'])
            self.txt_from.insert(0,datastore['email_reports_config']['from'])
        except Exception as e:
            # No email_reports_config in datastore yet
            pass

        self.txt_name.grid(row=1, column=1, padx=5, sticky='EW')
        self.txt_host.grid(row=2, column=1, padx=5, sticky='EW')
        self.txt_port.grid(row=3, column=1, padx=5, sticky='EW')
        self.txt_from.grid(row=4, column=1, padx=5, sticky='EW')

        self.listbox_emails = tk.Listbox(self.top)
        self.listbox_emails.grid(row=5, columnspan=2, padx=(5,0), pady=5, sticky='news')

        vsb = ttk.Scrollbar(self.top, orient="vertical", command=self.listbox_emails.yview)
        vsb.grid(row=5, column=2, sticky=("N", "S", "E", "W"), padx=(0,10), pady=(5, 5))
        self.listbox_emails.configure(yscrollcommand=vsb.set)

        datastore = get_datastore()
        try:
            for p in datastore['email_reports_config']['email_addresses']:
                self.listbox_emails.insert(tk.END, p)
        except Exception as e:
            # No email_reports_config in datastore yet
            pass

        tk.Button(self.top,text='Add Email Address',command=self.add_email, width=15).grid(row=6, column=0, padx=5, pady=5)
        tk.Button(self.top,text='Remove Email Address',command=self.remove_email, width=15).grid(row=6, column=1, padx=5, pady=5)
        tk.Button(self.top,text='Save',command=self.save_configuration, width=15).grid(row=7, column=0, columnspan=2, padx=5, pady=5)

        self.top.columnconfigure(0, weight=1)
        self.top.columnconfigure(1, weight=1)
        self.top.rowconfigure(5, weight=1)

    # Add a new Email to the list
    def add_email(self):
        email = simpledialog.askstring('Email', 'Enter Email Address', parent=self.top)
        
        if not email == None and len(email) > 0:
            self.listbox_emails.insert(tk.END, email)

    # Remove an Email from the list
    def remove_email(self):

        selected_indexes = self.listbox_emails.curselection()

        for ind in selected_indexes:
            self.listbox_emails.delete(ind)
        

    # Save parameters to the datastore
    def save_configuration(self):

        datastore = get_datastore()

        email_reports_config = {}
        email_reports_config['name'] = self.txt_name.get()
        email_reports_config['host'] = self.txt_host.get()
        email_reports_config['port'] = self.txt_port.get()
        email_reports_config['from'] = self.txt_from.get()
        email_reports_config['email_addresses'] = self.listbox_emails.get(0, tk.END)

        datastore['email_reports_config'] = email_reports_config

        set_datastore(datastore)

        self.top.destroy()

        
        
# Dialog to configure the archive path
class ArchivePathDialog:

    def __init__(self, parent):

        self.top = tk.Toplevel(parent)
        self.top.title('Configure Archive Path')
        self.top.geometry('400x200')
        self.top.update()
        self.top.minsize(self.top.winfo_width(), self.top.winfo_height())
        self.top.resizable(True, False)
        self.top.focus_set()
        self.top.grab_set()

        self.top.attributes("-topmost", True)

        self.top.columnconfigure(0, weight=10)
        self.top.columnconfigure(1, weight=1)

        tk.Label(self.top, text='Location to archive XVI data to:').grid(row=0, columnspan=2, padx=5, pady=5)

        self.txt_path = tk.Entry(self.top)

        datastore = get_datastore()
        try:
            self.txt_path.insert(0,datastore['archive_path'])
        except Exception as e:
            # No archive path in datastore yet
            pass

        self.txt_path.grid(row=1, column=0, padx=5, pady=5, sticky='NEWS')

        tk.Button(self.top,text='...',command=self.select_path).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.top,text='Save',command=self.save_configuration, width=15).grid(row=3, columnspan=2, padx=5, pady=5)

    # Select a path and enter it in the text box
    def select_path(self):

        self.directory = filedialog.askdirectory(parent=self.top)
        self.txt_path.delete(0,tk.END)
        self.txt_path.insert(0,self.directory)

    # Save parameters to the datastore
    def save_configuration(self):

        datastore = get_datastore()
        datastore['archive_path'] = self.txt_path.get()
        set_datastore(datastore)
        self.top.destroy()

# Dialog to configure the log file path
class LogPathDialog:

    def __init__(self, parent):

        self.top = tk.Toplevel(parent)
        self.top.title('Configure Log File Path')
        self.top.geometry('400x200')
        self.top.update()
        self.top.minsize(self.top.winfo_width(), self.top.winfo_height())
        self.top.resizable(True, False)
        self.top.focus_set()
        self.top.grab_set()

        self.top.attributes("-topmost", True)

        self.top.columnconfigure(0, weight=10)
        self.top.columnconfigure(1, weight=1)

        tk.Label(self.top, text='Location to store log files (restart required):').grid(row=0, columnspan=2, padx=5, pady=5)

        self.txt_path = tk.Entry(self.top)

        datastore = get_datastore()
        try:
            self.txt_path.insert(0,datastore['log_path'])
        except Exception as e:
            # No archive path in datastore yet
            pass

        self.txt_path.grid(row=1, column=0, padx=5, pady=5, sticky='NEWS')

        tk.Button(self.top,text='...',command=self.select_path).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.top,text='Save',command=self.save_configuration, width=15).grid(row=3, columnspan=2, padx=5, pady=5)

    # Select a path and enter it in the text box
    def select_path(self):

        self.directory = filedialog.askdirectory(parent=self.top)
        self.txt_path.delete(0,tk.END)
        self.txt_path.insert(0,self.directory)

    # Save parameters to the datastore
    def save_configuration(self):

        datastore = get_datastore()
        datastore['log_path'] = self.txt_path.get()
        set_datastore(datastore)
        self.top.destroy()

# About Dialog
class AboutDialog:

    def __init__(self, parent):

        # Load the release info to display authors and version
        try:
            with open('release.yaml', 'r') as f:
                release_info = yaml.load(f)
        except IOError as e:
                release_info = {}


        self.parent = parent

        self.top = tk.Toplevel(parent)
        self.top.title('About XVI Archive Tool')
        self.top.geometry('640x480')
        self.top.update()
        self.top.focus_set()
        self.top.grab_set()

        self.top.attributes("-topmost", True)

        authors = ""
        version = ""
        date = ""

        try:
            for a in release_info['authors']:
                authors += a['name'] + " (" + a['email'] + ")\n"

            version = release_info['version']
            date = release_info['date']
        except KeyError as e:
            pass

        txt = "Use this tool to archive and delete old patient data from XVI. If a " \
        + "patient has 4D data or was in a clinical trial their data will be archived, " \
        + "otherwise it will be deleted. Patients still under treatment will be kept.\n\n" \
        + "The data is only moved and deleted from the disk, no changes are made within " \
        + "XVI. See actioned.yaml for a list of patients removed by this tool, but still in " \
        + "XVI.\n\n" \
        + "This tool is developed by the Medical Physics Department at Liverpool and Macarthur  " \
        + "CTCs. It is intended for internal use only.\n\n" \
        + "Authors:\n" + authors + "\n" \
        + "Version: " + version + " (" + date + ")"

        lbl = tk.Label(self.top,text=txt)
        lbl.pack(expand=True, fill=tk.X)
        lbl.bind("<Configure>", self.resize)

    def resize(self, event):
        lbl = event.widget
        pad = 0
        pad += int(str(lbl['bd']))
        pad += int(str(lbl['padx']))
        pad *= 2
        lbl.configure(wraplength = event.width - pad)


# Report Issue Dialog
class ReportDialog:

    def __init__(self, parent):

        # Load the release info to display authors
        try:
            with open('release.yaml', 'r') as f:
                release_info = yaml.load(f)
        except IOError as e:
                release_info = {}

        self.parent = parent

        self.top = tk.Toplevel(parent)
        self.top.title('Report Issue')
        self.top.geometry('640x480')
        self.top.update()
        self.top.focus_set()
        self.top.grab_set()

        self.top.attributes("-topmost", True)

        authors = ""
        try:
            for a in release_info['authors']:
                authors += a['name'] + " (" + a['email'] + ")\n"
        except KeyError as e:
            pass

        txt = "Please report any problems or feature requests to:\n" + authors + "\n\n" \
        + "or create an issue directly at: https://bitbucket.org/swscsmedphys/xviarchivetool/issues/new\n\n" \
        + "Provide a full description of the problem along with the date and time and machine where the problem occured."

        lbl = tk.Label(self.top,text=txt)
        lbl.pack(expand=True, fill=tk.X)
        lbl.bind("<Configure>", self.resize)

    def resize(self, event):
        lbl = event.widget
        pad = 0
        pad += int(str(lbl['bd']))
        pad += int(str(lbl['padx']))
        pad *= 2
        lbl.configure(wraplength = event.width - pad)


# Dialog to prompt the user to perform some actions in XVI
class ScanningDialog:

    def __init__(self, parent):

        self.parent = parent

        self.top = tk.Toplevel(parent)
        self.top.title('Scanning Directories')
        self.top.geometry('300x100')
        self.top.minsize(self.top.winfo_width(), self.top.winfo_height())
        self.top.resizable(True, False)
        self.top.update()
        self.top.focus_set()
        self.top.grab_set()

        self.top.attributes("-topmost", True)

        self.str_status = tk.StringVar()
        self.str_status.set("Scanning...")
        self.lbl_status = tk.Label(self.top,textvariable=self.str_status)
        self.lbl_status.grid(row=0, padx=5, pady=5)

        self.progress = ttk.Progressbar(self.top, orient="horizontal", mode="indeterminate")
        self.progress.grid(row=1, padx=5, pady=5, sticky='news')
        self.progress.start(50)

        self.top.columnconfigure(0, weight=1)
        self.top.rowconfigure(0, weight=1)

        self.top.protocol("WM_DELETE_WINDOW", self.cancel)

    def cancel(self):

        self.str_status.set("Stopping Scan...")

        self.parent.scan_task.stop();

# Dialog to prompt the user to perform some actions in XVI
class ActionDialog:

    def __init__(self, parent):

        self.parent = parent

        self.top = tk.Toplevel(parent)
        self.top.title('XVI Action')
        self.top.geometry('840x600')
        self.top.update()
        self.top.focus_set()
        self.top.grab_set()

        self.top.attributes("-topmost", True)

        self.str_action_instructions = tk.StringVar()
        self.lbl_action_instructions = tk.Label(self.top,textvariable=self.str_action_instructions, wraplength=480)
        self.lbl_action_instructions.grid(row=0, padx=5, pady=5)

        self.progress = ttk.Progressbar(self.top, orient="horizontal", mode="determinate")

        self.listbox_patients = tk.Listbox(self.top)
        self.listbox_patients.grid(row=2, padx=(5,0), pady=5, sticky='news')

        vsb = ttk.Scrollbar(self.top, orient="vertical", command=self.listbox_patients.yview)
        vsb.grid(row=2, column=2, sticky=("N", "S", "E", "W"), padx=(0,10), pady=(5, 5))
        self.listbox_patients.configure(yscrollcommand=vsb.set)

        self.str_action_button = tk.StringVar()
        self.btn_perform_action = tk.Button(self.top,textvariable=self.str_action_button,command=self.perform_action, width=25)
        self.btn_perform_action.grid(row=3, padx=5, pady=5)

        self.btn_cancel_action = tk.Button(self.top,text='Cancel',command=self.cancel_action, width=15)
        self.btn_close = tk.Button(self.top,text='Close',command=self.close_dialog, width=15)

        self.action_running = False
        self.top.protocol("WM_DELETE_WINDOW", self.cancel_action)

        self.top.columnconfigure(0, weight=1)
        self.top.rowconfigure(2, weight=1)

        self.action = ""

    # Set list of patients
    def set_patient_list(self, list, action):

        self.patients = list
        self.action = action

        datastore = get_datastore()

        # First check that the XVI process isn't running,
        # If it is alert the user and abort the action
        if is_xvi_running():
            messagedialog.showwarning(
                "XVI Running",
                "Please close the XVI application before performing " + action.lower() + ".",
                parent=self.top
            )
            self.top.destroy()
            return

        # Also make sure a valid archive path has been setup (in case of archive)
        if action == 'ARCHIVE' and (not 'archive_path' in datastore or not os.path.exists(datastore['archive_path'])):
            messagedialog.showwarning(
                "Archive Path",
                "The archive path cannot be found. Make sure the directory exists and the network location is available.",
                parent=self.top
            )
            self.top.destroy()
            return

        for p in list:
            self.listbox_patients.insert(tk.END, p["mrn"] + " - " + p['name'])

        # Make sure the list contains some patients
        if len(list) > 0:

            if list[0]["action"] == "ARCHIVE":

                self.str_action_instructions.set("All data for the following patients will be copied to:\n\n" \
                + datastore['archive_path'] + \
                "\n\nOnce successfully copied the data will be deleted.")
                self.str_action_button.set("ARCHIVE PATIENT DATA")

            else:

                self.action = "DELETE"

                self.str_action_instructions.set("All data for the following patients will be deleted.")
                self.str_action_button.set("DELETE PATIENT DATA")

        else:
            # If there are no patients, alert the user and close the dialog
            messagedialog.showwarning(
                "No Patient Locations",
                "There are no patients for this action",
                parent=self.top
            )
            self.top.destroy()

    # Perform either the Archive or Delete Action
    def perform_action(self):

        # Hide the perform action button and show the cancel button
        self.btn_perform_action.grid_forget()
        self.btn_cancel_action.grid(row=3, padx=5, pady=5)

        # Remove the top label from the dialog
        self.lbl_action_instructions.grid_forget()

        # Clear the list box to show log of actions
        self.listbox_patients.delete(0, tk.END) # clear

        # Show the progress bar
        self.progress.grid(row=1, padx=5, pady=5, sticky='news')
        self.progress['maximum']=len(self.patients)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Start the action task, allowing it to report back its progress to the queue
        self.listbox_patients.insert(tk.END, now + " - " + self.action.capitalize() + " Action Start")
        self.queue = Queue.Queue()
        self.action_task = PerformActionTask(self.queue, self.patients, self.action)
        self.action_task.start()
        self.action_running = True
        self.parent.after(100, self.process_queue)

    def process_queue(self):

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        actioned_dirs = None

        # Loop over each item in queue
        for q in range(self.queue.qsize()):
            msg = self.queue.get(0) # Always get 0 because its a queue so FIFO

            # If the msg is a list, we know this was the last item
            if type(msg) == list:
                actioned_dirs = msg
            else:
                # Otherwise it was a progress update
                self.listbox_patients.insert(tk.END, now + " - " + msg)
                self.progress['value'] += 1

            # Scroll to end of listbox to see new message
            self.listbox_patients.yview(tk.END)

        # If actioned_dirs is not None then the action is complete
        if not actioned_dirs == None:

            self.action_running = False

            action_complete = "Complete"
            if not self.progress['value'] == self.progress['maximum']:
                action_complete = "Cancelled"

            self.listbox_patients.insert(tk.END, now + " - " + self.action.capitalize() + " Action " + action_complete)

            # Update the directories in the parent window
            for d in actioned_dirs:
                self.parent.directories[:] = [dir for dir in self.parent.directories if not os.path.join(dir["path"],dir["dir_name"]) == os.path.join(d["path"],d["dir_name"])]

            self.parent.update_gui()
            self.parent.update_list()

            # Hide the cancel button and show the close button
            self.btn_cancel_action.grid_forget()
            self.btn_close.grid(row=3, padx=5, pady=5)

            # Alert the user
            messagedialog.showinfo(action_complete, self.action.capitalize() + " " + action_complete, parent=self.top)

        else:

            # Run again in 100 ms
            self.parent.after(100, self.process_queue)

    # Cancel the current action
    def cancel_action(self):

        # Confirm that the user would like to cancel
        if self.action_running:
            if messagedialog.askyesno("Cancel " + self.action.capitalize() + " Action", "Are you sure you wish to cancel?", parent=self.top):
                self.btn_cancel_action['state'] = 'disabled'
                self.action_task.stop()
        else:
            self.top.destroy()

    # Close the window
    def close_dialog(self):
        self.top.destroy()
