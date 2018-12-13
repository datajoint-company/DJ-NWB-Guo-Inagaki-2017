# -*- coding: utf-8 -*-
"""
Created on Mon Dec  3 16:22:42 2018

@author: thinh
"""

from datetime import datetime
from dateutil.tz import tzlocal
import os
from pynwb import NWBFile, NWBHDF5IO
import h5py as h5
import matplotlib.pyplot as plt
import numpy as np
import re

import datajoint as dj
from pipeline import reference, subject, acquisition, behavior, ephys, action, stimulation


############## Dataset #################
path = os.path.join('..','data','whole_cell_nwb2.0')
fname = 'cell_20_1.nwb'
nwb = h5.File(os.path.join(path,fname), 'r')

############################ METADATA ############################

# ==================== subject ====================
list(nwb['general']['subject'])
subject_id = nwb['general']['subject']['subject_id'].value.decode('UTF-8')
age = nwb['general']['subject']['age'].value.decode('UTF-8')
desc = nwb['general']['subject']['description'].value.decode('UTF-8')
genotype = nwb['general']['subject']['genotype'].value.decode('UTF-8')
sex = nwb['general']['subject']['sex'].value.decode('UTF-8')
species = nwb['general']['subject']['species'].value.decode('UTF-8')
weight = nwb['general']['subject']['weight'].value.decode('UTF-8')

splittedstr = re.split('\n|Animal Strain: |Animal source: |Date of birth: ',desc)


#  Species ------------
subject.Species.insert1([species], skip_duplicates=True)
#  Strain ------------
subject.Strain.insert1(['N/A'], skip_duplicates=True)
#  Allele ------------
subject.Allele.insert1([source_strain], skip_duplicates=True)
#  Animal Source ------------
if source_identifier is None : source_identifier = 'N/A'
reference.AnimalSource.insert1([source_identifier], skip_duplicates=True)



# nwb['file_create_date']
file_created_date = list(nwb['file_create_date'])

# nwb['general']
list(nwb['general'])

    # data_collection
data_collection = nwb['general']['data_collection'].value.decode('UTF-8')
    # devices
list(nwb['general']['devices'])
devices = {}
for d in list(nwb['general']['devices']):
    devices[d] = nwb['general']['devices'][d].value.decode('UTF-8')

    # experiment_description
experiment_description = nwb['general']['experiment_description'].value
    # experimenter
experimenter = nwb['general']['experimenter'].value
    # institution
institution = nwb['general']['institution'].value
    # intracellular_ephys
list(nwb['general']['intracellular_ephys'])
list(nwb['general']['intracellular_ephys']['whole_cell'])
ie_desc = nwb['general']['intracellular_ephys']['whole_cell']['description'].value
ie_device = nwb['general']['intracellular_ephys']['whole_cell']['device'].value
ie_filtering = nwb['general']['intracellular_ephys']['whole_cell']['filtering'].value
ie_initial_access_resistance = nwb['general']['intracellular_ephys']['whole_cell']['initial_access_resistance'].value
ie_location = nwb['general']['intracellular_ephys']['whole_cell']['location'].value
ie_resistance = nwb['general']['intracellular_ephys']['whole_cell']['resistance'].value
ie_seal = nwb['general']['intracellular_ephys']['whole_cell']['seal'].value
ie_slice = nwb['general']['intracellular_ephys']['whole_cell']['slice'].value

    # lab
lab = nwb['general']['lab'].value
    # optogenetics
list(nwb['general']['optogenetics'])
site_names = []
site_desc = []
site_excitation_lambda = []
site_location = []
for site in list(nwb['general']['optogenetics']):
    site_names.append(site)
    site_desc.append(nwb['general']['optogenetics'][site]['description'].value.decode('UTF-8'))
    site_excitation_lambda.append(nwb['general']['optogenetics'][site]['excitation_lambda'].value.decode('UTF-8'))
    site_location.append(nwb['general']['optogenetics'][site]['location'].value.decode('UTF-8'))

    # related_publications
related_publications = nwb['general']['related_publications'].value.decode('UTF-8') 
    # session_id
session_id = nwb['general']['session_id'].value
    # surgery
surgery = nwb['general']['surgery'].value.decode('UTF-8')
    # task_keyword
task_keywords = list(nwb['general']['task_keyword'])

# nwb['identifier']
identifier = nwb['identifier'].value
# nwb['nwb_version']
nwb_version = nwb['nwb_version'].value
# nwb['session_description']
session_description = nwb['session_description'].value
# nwb['session_start_time']
#session_start_time = nwb['session_start_time'].value



# nwb['acquisition']
    # nwb['acquisition']['images']
list(nwb['acquisition']['images'])

    # nwb['acquisition']['timeseries']
    # nwb['acquisition']['timeseries']['membrane_potential']
list(nwb['acquisition']['timeseries']['membrane_potential'])

membrane_potential = {
        'data': np.array(nwb['acquisition']['timeseries']['membrane_potential']['data']),
        'timestamps':np.array(nwb['acquisition']['timeseries']['membrane_potential']['timestamps'])
        }
current_injection = {
        'electrode': np.array(nwb['acquisition']['timeseries']['current_injection']['electrode']),
        'data': np.array(nwb['acquisition']['timeseries']['current_injection']['data']),
        'timestamps':np.array(nwb['acquisition']['timeseries']['current_injection']['timestamps']),
        'gain':np.array(nwb['acquisition']['timeseries']['current_injection']['gain'])
        }
lick_trace_L = {
        'data': np.array(nwb['acquisition']['timeseries']['lick_trace_L']['data']),
        'timestamps':np.array(nwb['acquisition']['timeseries']['lick_trace_L']['timestamps'])
        }
lick_trace_R = {
        'data': np.array(nwb['acquisition']['timeseries']['lick_trace_R']['data']),
        'timestamps':np.array(nwb['acquisition']['timeseries']['lick_trace_R']['timestamps'])
        }

# nwb['analysis']
list(nwb['analysis'])

analysis_desc = nwb['analysis']['description'].value
membrane_potential_wo_spike = {
        'data': np.array(nwb['analysis']['Vm_wo_spikes']['membrane_potential_wo_spike']['data']),
        'timestamps':np.array(nwb['analysis']['Vm_wo_spikes']['membrane_potential_wo_spike']['timestamps']),
        'num_samples':np.array(nwb['analysis']['Vm_wo_spikes']['membrane_potential_wo_spike']['num_samples'])
        }

good_trials = np.array(nwb['analysis']['good_trials'])
trial_type_string = np.array(nwb['analysis']['trial_type_string'])
trial_start_times = np.array(nwb['analysis']['trial_start_times'])
trial_type_mat = np.array(nwb['analysis']['trial_type_mat'])

# nwb['epochs']
list(nwb['epochs'])

trial_names = []
desc = []
start_time = []
stop_time = []
for trial in list(nwb['epochs']):
    trial_names.append(trial)
    desc.append(nwb['epochs'][trial]['description'].value)
    start_time.append(nwb['epochs'][trial]['start_time'].value)
    stop_time.append(nwb['epochs'][trial]['stop_time'].value)

# nwb['processing']
list(nwb['processing'])

# nwb['stimulus']
list(nwb['stimulus'])
list(nwb['stimulus']['templates'])
list(nwb['stimulus']['presentation'])
cue_end = {
        'data': np.array(nwb['stimulus']['presentation']['cue_end']['data']),
        'timestamps':np.array(nwb['stimulus']['presentation']['cue_end']['timestamps'])
        }
cue_start = {
        'data': np.array(nwb['stimulus']['presentation']['cue_start']['data']),
        'timestamps':np.array(nwb['stimulus']['presentation']['cue_start']['timestamps'])
        }
photostimulus = {
        'data': np.array(nwb['stimulus']['presentation']['photostimulus']['data']),
        'timestamps':np.array(nwb['stimulus']['presentation']['photostimulus']['timestamps']),
        'site': nwb['stimulus']['presentation']['photostimulus']['site'].value.decode('UTF-8')
        }
pole_in = {
        'data': np.array(nwb['stimulus']['presentation']['pole_in']['data']),
        'timestamps':np.array(nwb['stimulus']['presentation']['pole_in']['timestamps'])
        }
pole_out = {
        'data': np.array(nwb['stimulus']['presentation']['pole_out']['data']),
        'timestamps':np.array(nwb['stimulus']['presentation']['pole_out']['timestamps'])
        }



























## =========== R&D =================
#acq_timeseries = {}
#for ts in list(nwb['acquisition']['timeseries']):
#    tmp_dict = {}
#    for f in list(nwb['acquisition']['timeseries'][ts]):
#        tmp_dict[f] = nwb['acquisition']['timeseries'][ts][f]
#    acq_timeseries[ts] = tmp_dict
#
## --
#trial_no = 2
#trial_start_times[trial_no]
#cue_start['timestamps'][trial_no]
#cue_end['timestamps'][trial_no]
#pole_in['timestamps'][trial_no]
#pole_out['timestamps'][trial_no]









