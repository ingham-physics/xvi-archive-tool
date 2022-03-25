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
    import Tkinter as tk
    import ttk
    import tkMessageBox as simpledialog
    import tkFileDialog as filedialog
except ImportError:
    # Python 3
    import tkinter as tk
    from tkinter import ttk
    from tkinter import simpledialog
    from tkinter import filedialog

from dialogs import (XVIPathsDialog, 
    ScanningDialog, 
    LogPathDialog, 
    ArchivePathDialog,
    OISConnectionDialog, 
    IgnoreMRNsDialog, 
    EmailReportsDialog, 
    ActionDialog, 
    AboutDialog, 
    ReportDialog)
from datastore import get_datastore, set_datastore
from tools import ScanPathsTask

from datetime import datetime, timedelta
import Queue
import os
import csv

import logging
logger = logging.getLogger(__name__)
LOG_LEVELS = ["Debug","Info","Warn","Error"]

# Main window of the application
class MainApplication(tk.Frame):

    def __init__(self, parent, *args, **kwargs):

        # Setup this window
        tk.Frame.__init__(self, parent, *args, **kwargs)
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        self.grid(sticky="news")

        self.parent = parent

        # Keep track of which actions are filtered in the treeview
        self.actions_filter = [
            {'action': 'KEEP', 'show': True},
            {'action': 'ARCHIVE', 'show': True},
            {'action': 'DELETE', 'show': True},
            {'action': 'IGNORE', 'show': False}
        ]

        # List of directories scanned
        self.directories = []

        # Frame with GUI for First step, Scanning locations
        scanFrame = ttk.Labelframe(self, text='Step 1: Scan XVI Locations')
        scanFrame.grid(row=0, padx=5, pady=5, sticky="news")

        scanFrame.columnconfigure(0, weight=1)

        tk.Button(scanFrame,text='Scan Now', command=self.scan_paths, width=20).grid(row=0, padx=5, pady=5)

        self.str_search_paths = tk.StringVar()
        tk.Label(scanFrame,textvariable=self.str_search_paths).grid(row=1, padx=1, pady=1, sticky='EW')

        self.str_dirs_scanned = tk.StringVar()
        tk.Label(scanFrame,textvariable=self.str_dirs_scanned).grid(row=2, padx=1, pady=1, sticky='EW')

        self.str_dirs_ignored = tk.StringVar()
        tk.Label(scanFrame,textvariable=self.str_dirs_ignored).grid(row=3, padx=1, pady=1, sticky='EW')

        # Frame with GUI for second step, archiving images
        archiveFrame = ttk.Labelframe(self, text='Step 2: Archive XVI Images')
        archiveFrame.grid(row=0, column=1, padx=5, pady=5, sticky="news")

        archiveFrame.columnconfigure(0, weight=1)

        self.str_dirs_archive = tk.StringVar()
        tk.Label(archiveFrame,textvariable=self.str_dirs_archive).grid(row=1, padx=1, pady=1, sticky='EW')

        self.str_dirs_archive_size = tk.StringVar()
        tk.Label(archiveFrame,textvariable=self.str_dirs_archive_size).grid(row=2, padx=1, pady=1, sticky='EW')

        self.str_archive_path = tk.StringVar()
        tk.Label(archiveFrame,textvariable=self.str_archive_path).grid(row=3, padx=1, pady=1, sticky='EW')

        self.btn_archive = tk.Button(archiveFrame, text='Perform Archive Action', command=self.perform_archive, state=tk.DISABLED, width=20)
        self.btn_archive.grid(row=0, padx=5, pady=5)

        # Frame with GUI for third step, deleting images
        deleteFrame = ttk.Labelframe(self, text='Step 3: Delete from XVI')
        deleteFrame.grid(row=0, column=2, padx=5, pady=5, sticky="news")

        deleteFrame.columnconfigure(0, weight=1)

        self.btn_delete = tk.Button(deleteFrame, text='Perform Delete', command=self.perform_delete, state=tk.DISABLED, width=20)
        self.btn_delete.grid(row=0, padx=5, pady=5)

        self.str_dirs_delete = tk.StringVar()
        tk.Label(deleteFrame,textvariable=self.str_dirs_delete).grid(row=1, padx=1, pady=1, sticky='EW')

        self.str_dirs_delete_size = tk.StringVar()
        tk.Label(deleteFrame,textvariable=self.str_dirs_delete_size).grid(row=2, padx=1, pady=1, sticky='EW')

        # Main contents of window containing treeview to display scanned locations
        self.list_frame = tk.Frame(self)
        self.list_frame.grid(row=6, column=0, columnspan=3, sticky=("N", "S", "E", "W"), padx=10, pady=(1, 1))
        self.list_frame.rowconfigure(1, weight=1)
        self.list_frame.columnconfigure(0, weight=1)

        tk.Label(self.list_frame,text='XVI Locations Scanned', font='Helvetica 11 bold').grid(row=0, padx=1, pady=1)
        style = ttk.Style(self)
        style.configure('Treeview', rowheight=30)
        col_headers = ["Action","MRN", "Name", "Finished Treatment", "Clinical Trial", "Has 4D", "Last Treatment Date" ,"Directory","Path","Size (GB)"]
        col_widths = [1, 1, 100, 10, 10, 10, 20, 20, 100, 10]
        self.treeview_patients = ttk.Treeview(self.list_frame, columns=col_headers, height=15)
        self.treeview_patients['show'] = 'headings'
        self.treeview_patients.grid(row=1, column=0, sticky=("N", "S", "E", "W"), padx=(10,0), pady=(1, 1))

        vsb = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.treeview_patients.yview)
        #vsb.pack(side='right', fill='y')
        vsb.grid(row=1, column=2, sticky=("N", "S", "E", "W"), padx=(0,10), pady=(1, 1))

        self.treeview_patients.configure(yscrollcommand=vsb.set)

        for col, w in zip(col_headers,col_widths):

            # Set the column heading (label)
            self.treeview_patients.heading(col, text=col)

            # Set the column width
            self.treeview_patients.column(col, width=w)

            # Sort by column when heading is pressed
            self.treeview_patients.heading(col, text=col.title(),
                command=lambda c=col: self.sortby(self.treeview_patients, c, 0))

        # Frame for filter functions at bottom of treeview
        filter_actions_frame = ttk.Labelframe(self.list_frame, text='Filter List')
        filter_actions_frame.grid(row=2, padx=5, pady=5, sticky="news")

        filter_actions_frame.columnconfigure(0, weight=1)
        filter_actions_frame.columnconfigure(1, weight=1)
        filter_actions_frame.columnconfigure(2, weight=1)
        filter_actions_frame.columnconfigure(3, weight=1)

        col_count = 0
        for action in self.actions_filter:
            action['btn'] = tk.Button(filter_actions_frame, text=action['action'], width=10)
            action['btn'].grid(row=0, column=col_count, padx=5, pady=5)
            action['btn'].bind("<Button-1>", lambda a: 'break')
            action['btn'].bind("<ButtonRelease-1>", self.filter)

            if action['show']:
                action['btn'].config(relief='sunken')
            col_count += 1

        self.addmenu_bar()

        self.update_gui()

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(6, weight=1)

    # Setup menu bar for window
    def addmenu_bar(self):
        menu_bar = tk.Menu(self)

        main_menu = tk.Menu(menu_bar, tearoff=0)
        main_menu.add_command(label='Configure XVI Paths', command=self.configure_window_xvi_paths)
        main_menu.add_command(label='Configure OIS Connection', command=self.configure_window_ois_connection)
        main_menu.add_command(label='Configure Archive Path', command=self.configure_window_archive_path)
        main_menu.add_command(label='Configure Log Path', command=self.configure_window_log_path)
        main_menu.add_command(label='Configure Ignore MRNs', command=self.configure_window_ignore_mrns)
        main_menu.add_command(label='Configure Email Reports', command=self.configure_window_email_reports)
        main_menu.add_separator()

        self.quick_scan = tk.BooleanVar()
        self.quick_scan.set(False)
        main_menu.add_checkbutton(label="Enable Quick Scan", onvalue=True, offvalue=False, variable=self.quick_scan)

        main_menu.add_separator()
        main_menu.add_command(label='Export CSV List', command=self.export_list)
        main_menu.add_separator()
        main_menu.add_command(label='Exit', command=tk.sys.exit)
        menu_bar.add_cascade(label='Setup', menu=main_menu)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label='Report Issue', command=self.report_issue)
        help_menu.add_command(label='About', command=self.show_about)
        menu_bar.add_cascade(label='Help', menu=help_menu)

        self.parent.config(menu=menu_bar)

    # Show About Dialog
    def show_about(self):

        dialog = AboutDialog(self)

        self.wait_window(dialog.top)

    # Show report issue dialog
    def report_issue(self):

        dialog = ReportDialog(self)

        self.wait_window(dialog.top)

    # Show configure XVI Path dialog and wait for it to finish
    def configure_window_xvi_paths(self):
        xvi_paths_dialog = XVIPathsDialog(self)

        self.wait_window(xvi_paths_dialog.top)

        self.update_gui()

    # Show configure Archive Path dialog and wait for it to finish
    def configure_window_archive_path(self):
        dialog = ArchivePathDialog(self)
        self.wait_window(dialog.top)
        self.update_gui()


    # Show configure Log File Path dialog and wait for it to finish
    def configure_window_log_path(self):
        dialog = LogPathDialog(self)
        self.wait_window(dialog.top)
        self.update_gui()

    # Show configure OIS dialog and wait for it to finish
    def configure_window_ois_connection(self):
        ois_connection_dialog = OISConnectionDialog(self)

        self.wait_window(ois_connection_dialog.top)

        self.update_gui()

    # Show configure Ignroe MRNs dialog and wait for it to finish
    def configure_window_ignore_mrns(self):
        ignore_mrns_dialog = IgnoreMRNsDialog(self)

        self.wait_window(ignore_mrns_dialog.top)

        self.update_gui()

    # Show configure Email Reports dialog and wait for it to finish
    def configure_window_email_reports(self):
        email_reports_dialog = EmailReportsDialog(self)

        self.wait_window(email_reports_dialog.top)

        self.update_gui()


    # Export the current list of directories as a CSV file
    def export_list(self):

        filepath = filedialog.asksaveasfilename(title = "Select CSV file",filetypes = (("CSV Files","*.csv"),("all files","*.*")))

        export_dirs = [d for d in self.directories if d['action'] == 'DELETE' or d['action'] == 'ARCHIVE' or d['action'] == 'KEEP']

        if len(export_dirs) == 0:
            simpledialog.showwarning('Export Error','Nothing to export!', parent=self)

        keys = export_dirs[0].keys()
        with open(filepath, 'wb') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(export_dirs)

    # Scan the configured paths
    def scan_paths(self):

        logger.info('Will scan locations now')

        self.queue = Queue.Queue()
        self.scan_task = ScanPathsTask(self.queue, self.quick_scan.get())
        self.scan_task.start()
        self.parent.after(100, self.process_queue)

        self.scan_dialog = ScanningDialog(self)

    def process_queue(self):

        task_done = False

        # Loop over each item in queue
        for q in range(self.queue.qsize()):
            msg = self.queue.get(0) # Always get 0 because its a queue so FIFO

            # If the msg is a list then its returning the list of directories
            if type(msg) == list:

                if len(msg) > 0: # If scan was cancelled, empty list is returned
                    self.directories = msg # Always get 0 because its a queue so FIFO

                    task_done = True

                    # Update the GUI and List
                    logger.info('Updating GUI')
                    self.update_gui()
                    logger.info('Updating Location List')
                    self.update_list()

                    logger.info('Scan finished')

                # Close the scanning dialog
                self.scan_dialog.top.destroy()

            elif type(msg) == dict:
                # if it's a dict then its returning an error message to display
                simpledialog.showwarning(msg['error'],msg['msg'], parent=self)

        if not task_done:
            self.parent.after(100, self.process_queue)


    # Update the various elements of the gui (labels, buttons, etc...)
    def update_gui(self):

        datastore = get_datastore()

        dirs_ignored = [d for d in self.directories if d['action'] == 'IGNORE']
        dirs_to_keep = [d for d in self.directories if d['action'] == 'KEEP']
        dirs_to_archive = [d for d in self.directories if d['action'] == 'ARCHIVE']
        dirs_to_delete = [d for d in self.directories if d['action'] == 'DELETE']

        logger.info('%d directories to ignore', len(dirs_ignored))
        logger.info('%d directories to archive', len(dirs_to_archive))
        logger.info('%d directories to delete', len(dirs_to_delete))
        logger.info('%d directories to keep', len(dirs_to_keep))

        self.str_search_paths.set('Number of XVI Search Paths: ' + str(len(datastore['xvi_paths'])))
        self.str_dirs_scanned.set('Total Directories Scanned: ' + str(len(self.directories)))
        self.str_dirs_ignored.set('Directories Ignored: ' + str(len(dirs_ignored)))
        self.str_dirs_archive.set('Directories to Archive: ' + str(len(dirs_to_archive)))
        archive_size = "{:.1f}".format(sum(d['dir_size'] for d in dirs_to_archive)/1024.0/1024.0/1024.0)
        self.str_dirs_archive_size.set('Size: ' + str(archive_size) + "GB")

        if 'archive_path' in datastore:
            ap = datastore['archive_path']
            ap = (ap[:15] + '...' + ap[len(ap)-15:]) if len(ap) > 30 else ap
            self.str_archive_path.set('Archive Path: ' + ap)

        self.str_dirs_delete.set('Directories to Delete: ' + str(len(dirs_to_delete)))
        delete_size = "{:.1f}".format(sum(d['dir_size'] for d in dirs_to_delete)/1024.0/1024.0/1024.0)
        self.str_dirs_delete_size.set('Size: ' + str(delete_size) + "GB")

        # Set the button states
        if(len(dirs_to_archive) > 0):
            self.btn_archive['state'] = 'normal'
        else:
            self.btn_archive['state'] = 'disabled'

        if(len(dirs_to_delete) > 0):
            self.btn_delete['state'] = 'normal'
        else:
            self.btn_delete['state'] = 'disabled'

    # Update the list to reflect the current directories scanned and filter settings
    def update_list(self):

        self.treeview_patients.delete(*self.treeview_patients.get_children())

        show_actions = [a['action'] for a in self.actions_filter if a['show']]

        for p in self.directories:
            if not p['action'] in show_actions:
                continue

            if p['action'] == 'IGNORE':
                self.treeview_patients.insert("", 'end', text="", values=(p['action'],'','','','','','',p['dir_name'],p['path'],"{:.1f}".format(p['dir_size']/1024.0/1024.0/1024.0)))
            else:
                self.treeview_patients.insert("", 'end', text="", values=(p['action'],p['mrn'],p['name'],p['finished_treatment'],p['clinical_trial'],p['has_4d'],p['last_fraction_date'],p['dir_name'],p['path'],"{:.1f}".format(p['dir_size']/1024.0/1024.0/1024.0)))

    # Callback for headers of treeview columns to perform sort on that column
    def sortby(self, tree, col, descending):
        """sort tree contents when a column header is clicked on"""
        # grab values to sort
        data = [(tree.set(child, col), child) \
            for child in tree.get_children('')]
        # if the data to be sorted is numeric change to float
        #data =  change_numeric(data)
        # now sort the data in place
        data.sort(reverse=descending)
        for ix, item in enumerate(data):
            tree.move(item[1], '', ix)
        # switch the heading so it will sort in the opposite direction
        tree.heading(col, command=lambda col=col: self.sortby(tree, col, int(not descending)))

    # Callback for filter buttons
    def filter(self, event):
        for action in self.actions_filter:
            if event.widget == action['btn']:
                if action['show']:
                    event.widget.config(relief=tk.RAISED)
                else:
                    event.widget.config(relief=tk.SUNKEN)

                action['show'] = not action['show']

        self.update_list()

    # Perform the archive action on each directory marked 'ARCHIVE'
    def perform_archive(self):


        archive_dirs = [d for d in self.directories if d['action'] == 'ARCHIVE']

        # Show dialog prompting Archive in XVI
        xvi_action_dialog = ActionDialog(self)
        xvi_action_dialog.set_patient_list(archive_dirs, 'ARCHIVE')
        self.wait_window(xvi_action_dialog.top)

    def perform_delete(self):

        delete_dirs = [d for d in self.directories if d['action'] == 'DELETE']

        # Show dialog prompting delete in XVI
        xvi_action_dialog = ActionDialog(self)
        xvi_action_dialog.set_patient_list(delete_dirs, 'DELETE')
        self.wait_window(xvi_action_dialog.top)
