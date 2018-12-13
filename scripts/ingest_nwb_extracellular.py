# -*- coding: utf-8 -*-


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

path = os.path.join('..','data','extracellular','datafiles')
fname = 'data_structure_ANM229327_20140423.nwb'

nwb = h5.File(os.path.join(path,fname), 'r')


# ------------------ acquisition ----------------
# nwb['acquisition']
    # nwb['acquisition']['images']
list(nwb['acquisition']['images'])

    # nwb['acquisition']['timeseries']
    # nwb['acquisition']['timeseries']['membrane_potential']['ephys_raw_data']
ephys_raw_data = nwb['acquisition']['timeseries']['extracellular_traces']['ephys_raw_data'].value.decode('UTF-8') 

# ------------------ analysis ----------------
# nwb['analysis']
list(nwb['analysis'])

analysis_desc = nwb['analysis']['description'].value.decode('UTF-8') 
trial_type_string = np.array(nwb['analysis']['trial_type_string'])
trial_start_times = np.array(nwb['analysis']['trial_start_times'])
trial_type_mat = np.array(nwb['analysis']['trial_type_mat'])

# nwb['epochs']
list(nwb['epochs'])
# extracellular
trial_names = []
tags = []
start_time = []
stop_time = []
for trial in list(nwb['epochs']):
    trial_names.append(trial)
    tags.append(np.array(nwb['epochs'][trial]['tags']))
    start_time.append(nwb['epochs'][trial]['start_time'].value)
    stop_time.append(nwb['epochs'][trial]['stop_time'].value)

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
    devices[d] = np.array(nwb['general']['devices'][d])

    # experiment_description
experiment_description = nwb['general']['experiment_description'].value
    # experimenter
experimenter = nwb['general']['experimenter'].value
    # institution
institution = nwb['general']['institution'].value

    # extracellular_ephys: extracellular
list(nwb['general']['extracellular_ephys'])
data_types = np.array(nwb['general']['extracellular_ephys']['data_types'])
electrodes = np.array(nwb['general']['extracellular_ephys']['electrodes'])
ground_coordinates = np.array(nwb['general']['extracellular_ephys']['ground_coordinates'])
penetration_num = nwb['general']['extracellular_ephys']['penetration_num'].value.decode('UTF-8') 
recording_marker = nwb['general']['extracellular_ephys']['recording_marker'].value.decode('UTF-8') 
recording_type = nwb['general']['extracellular_ephys']['recording_type'].value.decode('UTF-8') 

shank0 = nwb['general']['extracellular_ephys']['shank0']['device'] # not sure what these are
shank1 = nwb['general']['extracellular_ephys']['shank1']['device'] # not sure what these are

    # lab
lab = nwb['general']['lab'].value
    # optogenetics
list(nwb['general']['optogenetics'])
site_names = []
site_desc = []
site_excitation_lambda = []
site_location = []
site_stimulation_method = []
for site in list(nwb['general']['optogenetics']):
    site_names.append(site)
    site_desc.append(nwb['general']['optogenetics'][site]['description'].value.decode('UTF-8'))
    site_excitation_lambda.append(nwb['general']['optogenetics'][site]['excitation_lambda'].value.decode('UTF-8'))
    site_location.append(nwb['general']['optogenetics'][site]['location'].value.decode('UTF-8'))
    site_stimulation_method.append(nwb['general']['optogenetics'][site]['stimulation_method'].value.decode('UTF-8'))

    # related_publications
related_publications = nwb['general']['related_publications'].value.decode('UTF-8') 
    # session_id
session_id = nwb['general']['session_id'].value
    # subject
list(nwb['general']['subject'])
subject_id = nwb['general']['subject']['subject_id'].value.decode('UTF-8')
age = nwb['general']['subject']['age'].value.decode('UTF-8')
desc = nwb['general']['subject']['description'].value.decode('UTF-8')
genotype = nwb['general']['subject']['genotype'].value.decode('UTF-8')
sex = nwb['general']['subject']['sex'].value.decode('UTF-8')
species = nwb['general']['subject']['species'].value.decode('UTF-8')
#weight = nwb['general']['subject']['weight'].value.decode('UTF-8')
    # surgery
surgery = nwb['general']['surgery'].value.decode('UTF-8')
#    # task_keyword
#task_keywords = list(nwb['general']['task_keyword'])

# nwb['identifier']
identifier = nwb['identifier'].value
# nwb['nwb_version']
nwb_version = nwb['nwb_version'].value
# nwb['session_description']
session_description = nwb['session_description'].value
# nwb['session_start_time']
session_start_time = nwb['session_start_time'].value

# nwb['processing']
list(nwb['processing'])
list(nwb['processing']['extracellular_units'])
ec_event_waveform = np.array(nwb['processing']['extracellular_units']['EventWaveform'])
ec_unit_times = np.array(nwb['processing']['extracellular_units']['UnitTimes'])
ec_unit_desc = nwb['processing']['extracellular_units']['description'].value.decode('UTF-8')
ec_unit_identification_method = nwb['processing']['extracellular_units']['identification_method'].value.decode('UTF-8')
ec_unit_spike_sorting = nwb['processing']['extracellular_units']['spike_sorting'].value

# nwb['stimulus']
list(nwb['stimulus'])
list(nwb['stimulus']['templates'])
list(nwb['stimulus']['presentation'])
auditory_cue = {
        'data': np.array(nwb['stimulus']['presentation']['auditory_cue']['data']),
        'timestamps':np.array(nwb['stimulus']['presentation']['auditory_cue']['timestamps'])
        }
pole_in = {
        'data': np.array(nwb['stimulus']['presentation']['pole_in']['data']),
        'timestamps':np.array(nwb['stimulus']['presentation']['pole_in']['timestamps'])
        }
pole_out = {
        'data': np.array(nwb['stimulus']['presentation']['pole_out']['data']),
        'timestamps':np.array(nwb['stimulus']['presentation']['pole_out']['timestamps'])
        }























