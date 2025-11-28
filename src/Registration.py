#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 10 14:25:40 2021

@author: ColinVDB
Template
"""


import sys
import os
from os.path import join as pjoin
from os.path import exists as pexists
# from dicom2bids import *
import logging
from PyQt5.QtCore import (QSize,
                          Qt,
                          QModelIndex,
                          QMutex,
                          QObject,
                          QThread,
                          pyqtSignal,
                          QRunnable,
                          QThreadPool, 
                          QEvent)
from PyQt5.QtWidgets import (QDesktopWidget,
                             QApplication,
                             QWidget,
                             QPushButton,
                             QMainWindow,
                             QLabel,
                             QLineEdit,
                             QVBoxLayout,
                             QHBoxLayout,
                             QFileDialog,
                             QDialog,
                             QTreeView,
                             QFileSystemModel,
                             QGridLayout,
                             QPlainTextEdit,
                             QMessageBox,
                             QListWidget,
                             QTableWidget,
                             QTableWidgetItem,
                             QMenu,
                             QAction,
                             QTabWidget,
                             QCheckBox,
                             QInputDialog,
                             QTextBrowser,
                             QToolBar)
from PyQt5.QtGui import (QFont,
                         QIcon)
import markdown
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bids_registration import bids_registration, bids_registration_docker, bids_apply_transforms, bids_apply_transforms_docker, find_subjects_and_sessions, get_out_name
import time



def launch(parent, add_info=None):
    """
    

    Parameters
    ----------
    parent : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    window = MainWindow(parent, add_info)
    window.show()



# =============================================================================
# MainWindow
# =============================================================================
class MainWindow(QMainWindow):
    """
    """
    

    def __init__(self, parent, add_info):
        """
        

        Parameters
        ----------
        parent : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        super().__init__()
        self.parent = parent
        self.bids = self.parent.bids
        self.add_info = add_info

        self.setWindowTitle("Registration")
        self.window = QWidget(self)
        self.setCentralWidget(self.window)
        self.center()
        
        # Create a toolbar and add it to the main window
        self.toolbar = QToolBar("Help?")
        self.addToolBar(self.toolbar)
        
        # Create an action
        help_action = QAction("Help?", self)
        help_action.triggered.connect(self.show_help)  # Connect to function

        # Add action to the toolbar
        self.toolbar.addAction(help_action)
        
        self.pipeline = "Registration"
        
        sss_slurm = self.add_info.get('sss_slurm')
        
        if sss_slurm == None:
            print('no sss slurm')
            self.tabs = QTabWidget(self)
            self.reg_tab = RegistrationTab(self, sss_slurm)
            self.trans_tab = TransformationTab(self, sss_slurm)
            self.tabs.addTab(self.reg_tab, "Registration")
            self.tabs.addTab(self.trans_tab, "Transformation")
            layout = QVBoxLayout()
            layout.addWidget(self.tabs)
            
        else:
            # get job_info
            path = os.path.dirname(os.path.abspath(__file__))
            
            if not pexists(pjoin(path, sss_slurm)):
                print('[ERROR] sss_slurm json file not found')
            
            self.job_json = None
            with open(pjoin(path, sss_slurm), 'r') as f:
                self.job_json = json.load(f)
            
            self.tabs = QTabWidget(self)
            
            self.reg_tab = RegistrationTab(self, sss_slurm)
            self.trans_tab = TransformationTab(self, sss_slurm)
            self.job_tab = JobTab(self, self.job_json["slurm_infos"])
            
            self.tabs.addTab(self.reg_tab, "Registration")
            self.tabs.addTab(self.trans_tab, "Apply Transform")
            self.tabs.addTab(self.job_tab, "Slurm Job")
            
            layout = QVBoxLayout()
            layout.addWidget(self.tabs)

        self.window.setLayout(layout)


    def center(self):
        """
        

        Returns
        -------
        None.

        """
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        
        
    def event(self, event):
        # Override the help button event
        if event.type() == QEvent.NonClientAreaMouseButtonPress:
            if self.windowFlags() & Qt.WindowContextHelpButtonHint:
                self.show_help()
                return True
        return super().event(event)

    def show_help(self):
        # Open the help window with the Markdown file
        markdown_path = pjoin(os.path.dirname(__file__), "..", "README.md")
        if pexists(markdown_path):
            self.help_window = HelpWindow(markdown_path)
            self.help_window.show()
        else:
            print('Readme not found')
            
            
class HelpWindow(QWidget):
    def __init__(self, markdown_file):
        super().__init__()
        self.setWindowTitle("Help")
        self.resize(600, 400)

        # Load and convert markdown to HTML
        with open(markdown_file, 'r', encoding="utf-8", errors="replace") as file:
            markdown_content = file.read()
        html_content = markdown.markdown(markdown_content)

        # Setup QTextBrowser to display the HTML content
        self.text_browser = QTextBrowser()
        base_path = os.path.dirname(os.path.abspath(markdown_file))
        self.text_browser.setSearchPaths([base_path])
        self.text_browser.setHtml(html_content)

        layout = QVBoxLayout()
        layout.addWidget(self.text_browser)
        self.setLayout(layout)



# =============================================================================
# TemplateTab
# =============================================================================
class RegistrationTab(QWidget):
    """
    """
    

    def __init__(self, parent, sss_slurm=None):
        """
        

        Parameters
        ----------
        parent : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        super().__init__()
        self.parent = parent
        self.bids = self.parent.bids
        self.bmat_path = self.parent.parent.bmat_path
        self.setMinimumSize(500, 200)
        
        self.pipeline = 'Registration'
        
        self.local = sss_slurm == None
        
        if not self.local:
            self.job_json = self.parent.job_json
        
        # self.label = QLabel("This is a Template Pipeline")
        self.sub = ''
        self.ses = ''
        
        self.quick = QCheckBox('Quick registration')
        self.quick.setChecked(True)
        
        self.select_sequence_to_register_button = QPushButton("Select image to register")
        self.select_sequence_to_register_button.clicked.connect(self.select_sequence_to_register)
        self.sequence_to_register_label = QLabel()

        self.select_ref_sequence_button = QPushButton("Select reference image")
        self.select_ref_sequence_button.clicked.connect(self.select_ref_sequence)
        self.ref_sequence_label = QLabel()

        self.subjects_input = QLineEdit(self)
        self.subjects_input.setPlaceholderText("Select subjects")

        self.sessions_input = QLineEdit(self)
        self.sessions_input.setPlaceholderText("Select sessions")
        
        self.deriv_input = QLineEdit(self)
        self.deriv_input.setPlaceholderText('derivative name (default: registrations/reg-{space of ref image})')

        self.select_name_reg = QLineEdit(self)
        self.select_name_reg.setPlaceholderText('registration name (default: add reg-{space of ref image})')

        self.apply_same_transformation_check = QCheckBox('Apply same transformation ?')
        self.apply_same_transformation_check.stateChanged.connect(self.apply_same_transformation)
        self.apply_same_transformation_label = QLabel()

        self.registration_button = QPushButton("Registration")
        self.registration_button.clicked.connect(self.action)

        layout = QGridLayout()
        layout.addWidget(self.quick, 0, 0, 1, 1)
        layout.addWidget(self.select_sequence_to_register_button, 1, 0, 1, 1)
        layout.addWidget(self.sequence_to_register_label, 1, 1, 1, 1)
        layout.addWidget(self.select_ref_sequence_button, 2, 0, 1, 1)
        layout.addWidget(self.ref_sequence_label, 2, 1, 1, 1)
        layout.addWidget(self.subjects_input, 3, 0, 1, 1)
        layout.addWidget(self.sessions_input, 3, 1, 1, 1)
        layout.addWidget(self.deriv_input, 4, 0, 1, 2)
        layout.addWidget(self.select_name_reg, 5, 0, 1, 2)
        layout.addWidget(self.apply_same_transformation_check, 6, 0, 1, 1)
        layout.addWidget(self.apply_same_transformation_label, 6, 1, 1, 1)
        layout.addWidget(self.registration_button, 7, 0, 1, 2)
        
        self.setLayout(layout)
        
        
    def select_sequence_to_register(self):
        """


        Returns
        -------
        None.

        """
        self.reg_seq, _ = QFileDialog.getOpenFileName(self, "Select image to register", self.bids.root_dir, options=QFileDialog.DontUseNativeDialog)
        if self.reg_seq == '':
            return
        
        filename = os.path.basename(self.reg_seq)
        filename_no_ext = filename.split('.')[0]
        filename_d = filename_no_ext.split('_')
        seq_name_d = []
        for k in filename_d:
            if 'sub-' in k:
                self.sub = k.split('-')[1]
            elif'ses-' in k:
                self.ses = k.split('-')[1]
            else:
                seq_name_d.append(k)
        seq_name = '_'.join(seq_name_d)
        self.sequence_to_register_label.setText(seq_name)
        
        
    def select_ref_sequence(self):
        """


        Returns
        -------
        None.

        """
        self.ref_seq, _ = QFileDialog.getOpenFileName(self, "Select reference image", self.bids.root_dir, options=QFileDialog.DontUseNativeDialog)
        if self.ref_seq == '':
            return
        
        filename = os.path.basename(self.ref_seq)
        filename_no_ext = filename.split('.')[0]
        filename_d = filename_no_ext.split('_')
        seq_name_d = []
        for k in filename_d:
            if 'sub-' in k:
                self.sub = k.split('-')[1]
            elif'ses-' in k:
                self.ses = k.split('-')[1]
            else:
                seq_name_d.append(k)
        seq_name = '_'.join(seq_name_d)
        self.ref_sequence_label.setText(seq_name)
        
        
    def apply_same_transformation(self):
        """


        Returns
        -------
        None.

        """
        if self.apply_same_transformation_check.isChecked() == True:
            self.trans_seq_to_register, _ = QFileDialog.getOpenFileNames(self, "Select images to apply same transformation", self.bids.root_dir, options=QFileDialog.DontUseNativeDialog)
            
            trans_sequences_lab = ""
            for image in self.trans_seq_to_register:
                if image == '':
                    return
                
                filename = os.path.basename(image)
                filename_no_ext = filename.split('.')[0]
                filename_d = filename_no_ext.split('_')
                seq_name_d = []
                for k in filename_d:
                    if 'sub-' in k:
                        self.sub = k.split('-')[1]
                    elif'ses-' in k:
                        self.ses = k.split('-')[1]
                    else:
                        seq_name_d.append(k)
                seq_name = '_'.join(seq_name_d)
                trans_sequences_lab += f'{seq_name}\n'
                
        self.apply_same_transformation_label.setText(trans_sequences_lab[:-1])


    def action(self):
        """
        

        Returns
        -------
        None.

        """
        
        # select sub and ses to run
        sub = self.subjects_input.text()
        if sub == '':
            sub = self.sub
        ses = self.sessions_input.text()
        if ses == '':
            ses = self.ses
        # sub = '001'
        # ses = '01'
        
        deriv = self.deriv_input.text()
        if deriv == '':
            deriv = None
        name_reg = self.select_name_reg.text()
        if name_reg == '':
            name_reg = None
            
        if self.apply_same_transformation_check.isChecked():
            same_transformations = self.trans_seq_to_register
        else:
            same_transformations = None
            
        args = []
        args.extend(['--input-image', self.reg_seq])
        args.extend(['--reference-image', self.ref_seq])
        if self.quick.isChecked():
            args.append('--quick')
        if deriv:
            args.extend(['--derivative', deriv])
        if name_reg:
            args.extend(['--reg-name', name_reg])
        
        if self.local:
            use_docker = self.parent.add_info.get('use_docker')
            self.thread = QThread()
            self.action = ActionWorker(self.bids.root_dir, sub, ses, self.pipeline, self.reg_seq, self.ref_seq, quick=self.quick.isChecked(), same_transformations=same_transformations, deriv=deriv, reg_name=name_reg, use_docker=use_docker)
            self.action.moveToThread(self.thread)
            self.thread.started.connect(self.action.run)
            self.action.in_progress.connect(self.is_in_progress)
            self.action.finished.connect(self.thread.quit)
            self.action.finished.connect(self.action.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()
        
            self.parent.hide()
            
        else:
            self.job_json["slurm_infos"] = self.parent.job_tab.get_slurm_job_info()
            if self.job_json["slurm_infos"]["use_local"]:
                self.local = True
                self.action()
                return
            
            else:
                self.job_json["slurm_infos"].pop("use_local")
            
            # Import the submit_job_sss
            sys.path.insert(0, self.bmat_path)
            submit_job_sss = __import__('submit_job_sss')
            submit_job = submit_job_sss.submit_job
            submit_job_compose = submit_job_sss.submit_job_compose
            sys.path.pop(0)
            
            # Do action
            def getPassword():
                password, ok = QInputDialog.getText(self, "SSH Key Passphrase", "Unlocking SSH key with passphrase?", 
                                        QLineEdit.Password)
                passphrase = None
                if ok and password:
                    passphrase = password
                return passphrase
            
            passphrase = getPassword()
            
            # Do the job here and not in a thread 
            self.is_in_progress(('Registration', True))
            jobs_submitted = []
                
            try:
                if self.apply_same_transformation_check.isChecked():
                    print('bruuuuuuuuuuuuh')
                    jobs_info_compose = [self.job_json]
                    args_compose = [args]
                    out_name_kwargs = {k: v for k, v in {"deriv":deriv, "reg_name":name_reg}.items() if v is not None}
                    out_name = get_out_name(self.bids.root_dir, sub.split(',')[0], ses.split(',')[0], self.reg_seq, self.ref_seq, **out_name_kwargs)
                    for seq in same_transformations:
                        jobs_info_compose.append(self.job_json)
                        arg_comp = []
                        arg_comp.extend(['--input-image', seq])
                        arg_comp.extend(['--reference-image', self.ref_seq])
                        arg_comp.append('--apply-transform')
                        arg_comp.extend(['--transformation-matrix', f'{out_name}0GenericAffine.mat'])
                        if deriv:
                            args.extend(['--derivative', deriv])
                        if name_reg:
                            args.extend(['-reg-name', name_reg])
                        args_compose.append(args)
                        
                    job_id = submit_job_compose(self.bids.root_dir, sub, ses, jobs_info_compose, args=args_compose, use_asyncssh=True, passphrase=passphrase, one_job=False)
                
                else:
                    job_id = submit_job(self.bids.root_dir, sub, ses, self.job_json, args=args, use_asyncssh=True, passphrase=passphrase, one_job=False)
                    # job_id = ['Submitted batch job 2447621']
                    if job_id is not None and job_id != []:
                        if type(job_id) is list:
                            jobs_submitted.extend(job_id)
                        else:
                            jobs_submitted.append(job_id)

            except Exception as e:
                self.error_handler(e)
            
            self.is_in_progress(('Registration', False))
            self.submitted_jobs(jobs_submitted)
            
    def is_in_progress(self, in_progress):
        self.parent.parent.work_in_progress.update_work_in_progress(in_progress)
        
    
    def error_handler(self, exception):
        QMessageBox.critical(self, type(exception).__name__, str(exception))
        
    def submitted_jobs(self, jobs_id):
        print('submitted jobs')
        class SubmittedJobsDialog(QDialog):
            def __init__(self, results, parent=None):
                super().__init__()
        
                self.setWindowTitle('Jobs Submitted')
                self.setGeometry(300, 300, 400, 300)
                
                layout = QVBoxLayout(self)
                
                # Create and populate the QListWidget
                self.listWidget = QListWidget(self)
                for result in results:
                    self.listWidget.addItem(result)
                
                layout.addWidget(self.listWidget)
        
                # Create OK button
                self.okButton = QPushButton('OK', self)
                self.okButton.clicked.connect(self.accept)
                
                # Add OK button to layout
                buttonLayout = QHBoxLayout()
                buttonLayout.addStretch()
                buttonLayout.addWidget(self.okButton)
                
                layout.addLayout(buttonLayout)
                
        job_dialog = SubmittedJobsDialog(jobs_id)
        # job_submitted_window = QMainWindow()
        # job_submitted_window.setCentralWidget(job_dialog)
        job_dialog.exec_()
        
        
        
class TransformationTab(QWidget):
    """
    """
    

    def __init__(self, parent, sss_slurm=None):
        """
        

        Parameters
        ----------
        parent : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        super().__init__()
        self.parent = parent
        self.bids = self.parent.bids
        self.bmat_path = self.parent.parent.bmat_path
        self.setMinimumSize(500, 200)
        
        self.pipeline = 'ApplyTransform'
        
        self.local = sss_slurm == None
        
        if not self.local:
            self.job_json = self.parent.job_json
        
        # self.label = QLabel("This is a Template Pipeline")
        self.sub = ''
        self.ses = ''
        
        self.select_sequence_to_register_button = QPushButton("Select image to register")
        self.select_sequence_to_register_button.clicked.connect(self.select_sequence_to_register)
        self.sequence_to_register_label = QLabel()

        self.select_ref_sequence_button = QPushButton("Select reference image")
        self.select_ref_sequence_button.clicked.connect(self.select_ref_sequence)
        self.ref_sequence_label = QLabel()

        self.select_transformation_matrix_button = QPushButton("Select transformation matrix")
        self.select_transformation_matrix_button.clicked.connect(self.select_transformation_matrix)
        self.transformation_matrix_label = QLabel()
        
        self.label = QCheckBox('Label Transformation')
        self.label.setChecked(False)
        
        self.inverse = QCheckBox('Use inverse Transform')
        self.inverse.setChecked(False)
        
        self.subjects_input = QLineEdit(self)
        self.subjects_input.setPlaceholderText("Select subjects")

        self.sessions_input = QLineEdit(self)
        self.sessions_input.setPlaceholderText("Select sessions")
        
        self.deriv_input = QLineEdit(self)
        self.deriv_input.setPlaceholderText('derivative name (default: registrations/reg-{space of ref image})')

        self.select_name_reg = QLineEdit(self)
        self.select_name_reg.setPlaceholderText('registration name (default: add reg-{space} of ref image})')

        self.transformation_button = QPushButton("Apply Transform")
        self.transformation_button.clicked.connect(self.action)

        layout = QGridLayout()
        layout.addWidget(self.select_sequence_to_register_button, 0, 0, 1, 1)
        layout.addWidget(self.sequence_to_register_label, 0, 1, 1, 1)
        layout.addWidget(self.select_ref_sequence_button, 1, 0, 1, 1)
        layout.addWidget(self.ref_sequence_label, 1, 1, 1, 1)
        layout.addWidget(self.select_transformation_matrix_button, 2, 0, 1, 1)
        layout.addWidget(self.transformation_matrix_label, 2, 1, 1, 1)
        layout.addWidget(self.label, 3, 0, 1, 1)
        layout.addWidget(self.inverse, 3, 1, 1, 1)
        layout.addWidget(self.subjects_input, 4, 0, 1, 1)
        layout.addWidget(self.sessions_input, 4, 1, 1, 1)
        layout.addWidget(self.deriv_input, 5, 0, 1, 2)
        layout.addWidget(self.select_name_reg, 6, 0, 1, 2)
        layout.addWidget(self.transformation_button, 7, 0, 1, 2)
        
        self.setLayout(layout)
        
        
    def select_sequence_to_register(self):
        """


        Returns
        -------
        None.

        """
        self.reg_seq, _ = QFileDialog.getOpenFileName(self, "Select image to register", self.bids.root_dir, options=QFileDialog.DontUseNativeDialog)
        if self.reg_seq == '':
            return
        
        filename = os.path.basename(self.reg_seq)
        filename_no_ext = filename.split('.')[0]
        filename_d = filename_no_ext.split('_')
        seq_name_d = []
        for k in filename_d:
            if 'sub-' in k:
                self.sub = k.split('-')[1]
            elif'ses-' in k:
                self.ses = k.split('-')[1]
            else:
                seq_name_d.append(k)
        seq_name = '_'.join(seq_name_d)
        self.sequence_to_register_label.setText(seq_name)
        
        
    def select_ref_sequence(self):
        """


        Returns
        -------
        None.

        """
        self.ref_seq, _ = QFileDialog.getOpenFileName(self, "Select reference image", self.bids.root_dir, options=QFileDialog.DontUseNativeDialog)
        if self.ref_seq == '':
            return
        
        filename = os.path.basename(self.ref_seq)
        filename_no_ext = filename.split('.')[0]
        filename_d = filename_no_ext.split('_')
        seq_name_d = []
        for k in filename_d:
            if 'sub-' in k:
                self.sub = k.split('-')[1]
            elif'ses-' in k:
                self.ses = k.split('-')[1]
            else:
                seq_name_d.append(k)
        seq_name = '_'.join(seq_name_d)
        self.ref_sequence_label.setText(seq_name)
        
        
    def select_transformation_matrix(self):
        """


        Returns
        -------
        None.

        """
        self.trans_mat, _ = QFileDialog.getOpenFileName(self, "Select Transformation Matrix", self.bids.root_dir, options=QFileDialog.DontUseNativeDialog)
        if self.trans_mat == '':
            return
        
        filename = os.path.basename(self.trans_mat)
        filename_no_ext = filename.split('.')[0]
        filename_d = filename_no_ext.split('_')
        seq_name_d = []
        for k in filename_d:
            if 'sub-' in k:
                self.sub = k.split('-')[1]
            elif'ses-' in k:
                self.ses = k.split('-')[1]
            else:
                seq_name_d.append(k)
        seq_name = '_'.join(seq_name_d)
        self.transformation_matrix_label.setText(seq_name)


    def action(self):
        """
        

        Returns
        -------
        None.

        """
        
        # select sub and ses to run
        sub = self.subjects_input.text()
        if sub == '':
            sub = self.sub
        ses = self.sessions_input.text()
        if ses == '':
            ses = self.ses
        # sub = '001'
        # ses = '01'
        
        deriv = self.deriv_input.text()
        if deriv == '':
            deriv = None
        name_reg = self.select_name_reg.text()
        if name_reg == '':
            name_reg = None
            
        args = []
        args.extend(['--input-image', self.reg_seq])
        args.extend(['--reference-image', self.ref_seq])
        args.append('--apply-transform')
        args.extend(['--transformation-matrix', self.trans_mat])
        if self.label.isChecked():
            args.append('--label')
        if self.inverse.isChecked():
            args.append('--inverse')
        if deriv:
            args.extend(['--derivative', deriv])
        if name_reg:
            args.extend(['-reg-name', name_reg])
        
        if self.local:
            use_docker = self.parent.add_info.get('use_docker')
            self.thread = QThread()
            self.action = ActionWorker(self.bids.root_dir, sub, ses, self.pipeline, self.reg_seq, self.ref_seq, apply_transform=True, trans_mat=self.trans_mat, label=self.label.isChecked(), inverse=self.inverse.isChecked(), deriv=deriv, reg_name=name_reg, use_docker=use_docker)
            self.action.moveToThread(self.thread)
            self.thread.started.connect(self.action.run)
            self.action.in_progress.connect(self.is_in_progress)
            self.action.finished.connect(self.thread.quit)
            self.action.finished.connect(self.action.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()
        
            self.parent.hide()
            
        else:
            self.job_json["slurm_infos"] = self.parent.job_tab.get_slurm_job_info()
            if self.job_json["slurm_infos"]["use_local"]:
                self.local = True
                self.action()
                return
            
            else:
                self.job_json["slurm_infos"].pop("use_local")
            
            # Import the submit_job_sss
            sys.path.insert(0, self.bmat_path)
            submit_job_sss = __import__('submit_job_sss')
            submit_job = submit_job_sss.submit_job
            sys.path.pop(0)
            
            # Do action
            def getPassword():
                password, ok = QInputDialog.getText(self, "SSH Key Passphrase", "Unlocking SSH key with passphrase?", 
                                        QLineEdit.Password)
                passphrase = None
                if ok and password:
                    passphrase = password
                return passphrase
            
            passphrase = getPassword()
            
            # Do the job here and not in a thread 
            self.is_in_progress(('ApplyTransform', True))
            jobs_submitted = []
                
            try:
                job_id = submit_job(self.bids.root_dir, sub, ses, self.job_json, args=args, use_asyncssh=True, passphrase=passphrase, one_job=False)
                # job_id = ['Submitted batch job 2447621']
                if job_id is not None and job_id != []:
                    if type(job_id) is list:
                        jobs_submitted.extend(job_id)
                    else:
                        jobs_submitted.append(job_id)

            except Exception as e:
                self.error_handler(e)
            
            self.is_in_progress(('ApplyTransform', False))
            self.submitted_jobs(jobs_submitted)
            
    def is_in_progress(self, in_progress):
        self.parent.parent.work_in_progress.update_work_in_progress(in_progress)
        
    
    def error_handler(self, exception):
        QMessageBox.critical(self, type(exception).__name__, str(exception))
        
    def submitted_jobs(self, jobs_id):
        print('submitted jobs')
        class SubmittedJobsDialog(QDialog):
            def __init__(self, results, parent=None):
                super().__init__()
        
                self.setWindowTitle('Jobs Submitted')
                self.setGeometry(300, 300, 400, 300)
                
                layout = QVBoxLayout(self)
                
                # Create and populate the QListWidget
                self.listWidget = QListWidget(self)
                for result in results:
                    self.listWidget.addItem(result)
                
                layout.addWidget(self.listWidget)
        
                # Create OK button
                self.okButton = QPushButton('OK', self)
                self.okButton.clicked.connect(self.accept)
                
                # Add OK button to layout
                buttonLayout = QHBoxLayout()
                buttonLayout.addStretch()
                buttonLayout.addWidget(self.okButton)
                
                layout.addLayout(buttonLayout)
                
        job_dialog = SubmittedJobsDialog(jobs_id)
        # job_submitted_window = QMainWindow()
        # job_submitted_window.setCentralWidget(job_dialog)
        job_dialog.exec_()
        
        

class JobTab(QWidget):
    """
    """
    
    def __init__(self, parent, slurm_infos):
        """
        

        Returns
        -------
        None.

        """
        super().__init__()
        
        self.parent = parent
        self.bids = self.parent.bids
        self.slurm_info = slurm_infos
        self.setMinimumSize(500, 200)
        
        self.use_local_check = QCheckBox('Use local instead of server pipeline')
        
        self.slurm_info_input = {}
        layout = QVBoxLayout()
        layout.addWidget(self.use_local_check)
        for key in self.slurm_info.keys():
            key_label = QLabel(key)
            key_input = QLineEdit(self)
            key_input.setPlaceholderText(self.slurm_info[key])
            key_layout = QHBoxLayout()
            self.slurm_info_input[f'{key}_input'] = key_input
            key_layout.addWidget(key_label)
            key_layout.addWidget(key_input)
            layout.addLayout(key_layout)
            
        self.setLayout(layout)
            
            
    def get_slurm_job_info(self):
        use_local = self.use_local_check.isChecked()
        slurm_job_info = {"use_local":use_local}
        for key in self.slurm_info.keys():
            key_text = self.slurm_info_input[f'{key}_input'].text()
            if key_text == None or key_text == "":
                key_text = self.slurm_info_input[f'{key}_input'].placeholderText()
                
            slurm_job_info[key] = key_text
        return slurm_job_info



# =============================================================================
# ActionWorker
# =============================================================================
class ActionWorker(QObject):
    """
    """
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    in_progress = pyqtSignal(tuple)
    

    def __init__(self, bids, sub, ses, pipeline, reg_seq, ref_seq, quick=True, same_transformations=None, apply_transform=False, trans_mat=None, label=False, inverse=False, deriv=None, reg_name=None, use_docker=False):
        """
        

        Returns
        -------
        None.

        """
        super().__init__()
        
        self.bids = bids
        self.sub = sub
        self.ses = ses
        self.pipeline = pipeline
        self.reg_seq = reg_seq
        self.ref_seq = ref_seq
        self.quick = quick
        self.same_transformations = same_transformations
        self.apply_transform = apply_transform
        self.trans_mat = trans_mat
        self.label = label
        self.inverse = inverse
        self.deriv = deriv
        self.reg_name = reg_name
        self.use_docker = use_docker
        

    def run(self):
        """
        

        Returns
        -------
        None.

        """
        self.in_progress.emit((self.pipeline, True))
        # Action
        print('Beginning of the action')
        subjects_and_sessions = find_subjects_and_sessions(self.bids, self.sub, self.ses, check_if_exist=False)
        
        kwargs = {k: v for k, v in {"deriv":self.deriv, "reg_name":self.reg_name}.items() if v is not None}
        
        for sub, sess in subjects_and_sessions:
            for ses in sess:
                print(sub, ses)
                if self.apply_transform:
                    if self.use_docker:
                        bids_apply_transforms_docker(self.bids, sub, ses, self.reg_seq, self.ref_seq, self.trans_mat, label=self.label, inverse=self.inverse, **kwargs)
                    else:
                        bids_apply_transforms(self.bids, sub, ses, self.reg_seq, self.ref_seq, self.trans_mat, label=self.label, inverse=self.inverse, **kwargs)
                else:
                    if self.use_docker:
                        sub_ses_outreg = bids_registration_docker(self.bids, sub, ses, self.reg_seq, self.ref_seq, quick=self.quick, **kwargs)
                        
                        if self.same_transformations:
                            print('apply same transformation')
                            if type(self.same_transformations) == list:
                                for seq in self.same_transformations:
                                    bids_apply_transforms_docker(self.bids, sub, ses, seq, self.ref_seq, f'{sub_ses_outreg}0GenericAffine.mat', label=False, inverse=False, **kwargs)
                            else:
                                print('[ERROR] not a list')
                    else:
                        sub_ses_outreg = bids_registration(self.bids, sub, ses, self.reg_seq, self.ref_seq, quick=self.quick, **kwargs)
                        
                        if self.same_transformations:
                            print('apply same transformation')
                            if type(self.same_transformations) == list:
                                for seq in self.same_transformations:
                                    bids_apply_transforms(self.bids, sub, ses, seq, self.ref_seq, f'{sub_ses_outreg}0GenericAffine.mat', label=False, inverse=False, **kwargs)
                            else:
                                print('[ERROR] not a list')
                
        print('End of the action')
        self.in_progress.emit((self.pipeline, False))
        self.finished.emit()


