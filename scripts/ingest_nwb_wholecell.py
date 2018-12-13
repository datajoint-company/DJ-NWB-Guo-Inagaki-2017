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
from pipeline import reference, subject, acquisition #, behavior, ephys, action, stimulation
from pipeline.helper_functions import parse_prefix

# Merge all schema and generate the overall ERD (then save in "/images")
all_erd = dj.ERD(reference) + dj.ERD(subject) + dj.ERD(action) + dj.ERD(acquisition) + dj.ERD(behavior) + dj.ERD(ephys) + dj.ERD(stimulation)
all_erd.save('./images/all_erd.png')

# Merge all schema and generate the overall ERD (then save in "/images")
core_erd = dj.ERD(reference) + dj.ERD(subject) + dj.ERD(acquisition) 
core_erd.save('./images/core_erd.png')

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

# dob and sex
splittedstr = re.split('Date of birth: ',desc)
dob = splittedstr[-1]
dob = datetime.strptime(str(dob),'%Y-%m-%d') 
sex = sex[0].upper()

# strain and source
animal_strains = subject.Strain.fetch()
for s in animal_strains:
    m = re.search(s[0], desc) 
    if (m is not None):
        strain = s[0]
        break
animal_sources = reference.AnimalSource.fetch()
for s in animal_sources:
    m = re.search(s[0], desc) 
    if (m is not None):
        animal_source = s[0]
        break

if dob is not None:
    subject.Subject.insert1(
            {'subject_id':subject_id,
             'species':species,
             'strain':strain,
             'animal_source':animal_source,
             'sex': sex,
             'date_of_birth': dob,
             'subject_description':desc}, 
             skip_duplicates=True)
else: 
    subject.Subject.insert1(
            {'subject_id':subject_id,
             'sex': sex,
             'subject_description':desc}, 
             skip_duplicates=True)

# ==================== session ====================
    # experiment_description
experiment_description = nwb['general']['experiment_description'].value
    # experimenter
experimenter = np.array(nwb['general']['experimenter'])
    # institution
institution = nwb['general']['institution'].value
    # related_publications
related_publications = nwb['general']['related_publications'].value.decode('UTF-8') 
    # session_id
session_id = nwb['general']['session_id'].value
    # surgery
surgery = nwb['general']['surgery'].value.decode('UTF-8')
# nwb['identifier']
identifier = nwb['identifier'].value
# nwb['nwb_version']
nwb_version = nwb['nwb_version'].value
# nwb['session_description']
session_description = nwb['session_description'].value
# nwb['session_start_time']
session_start_time = nwb['session_start_time'].value

# -- session_time 
date_of_experiment = parse_prefix(session_start_time)
experiment_types = re.split('Experiment type: ',experiment_description)[-1]
experiment_types = np.array(re.split(', ',experiment_types))

if date_of_experiment is not None: 
    with acquisition.Session.connection.transaction:
        acquisition.Session.insert1(            
                    {'subject_id':subject_id,
                     'session_time': date_of_experiment,
                     'session_note': session_description
                     })
        for k in np.arange(experimenter.size):
            acquisition.Session.Experimenter.insert1(            
                        {'subject_id':subject_id,
                         'session_time': date_of_experiment,
                         'experimenter': experimenter.item(k)
                         })
        for k in np.arange(experiment_types.size):
            acquisition.Session.ExperimentType.insert1(            
                        {'subject_id':subject_id,
                         'session_time': date_of_experiment,
                         'experiment_type': experiment_types.item(k)
                         })
        # there is still the ExperimentType part table here...
        print(f'\tSession created - Subject: {subject_id} - IC: {cell_id} - EC: "N/A" - Date: {date_of_experiment}')

# ==================== Intracellular ====================
        
        
# -- read data - devices
devices = {}
for d in list(nwb['general']['devices']):
    devices[d] = nwb['general']['devices'][d].value.decode('UTF-8')
    
# -- read data - intracellular_ephys
ie_desc = nwb['general']['intracellular_ephys']['whole_cell']['description'].value
ie_device = nwb['general']['intracellular_ephys']['whole_cell']['device'].value
ie_filtering = nwb['general']['intracellular_ephys']['whole_cell']['filtering'].value
ie_initial_access_resistance = nwb['general']['intracellular_ephys']['whole_cell']['initial_access_resistance'].value
ie_location = nwb['general']['intracellular_ephys']['whole_cell']['location'].value
ie_resistance = nwb['general']['intracellular_ephys']['whole_cell']['resistance'].value
ie_seal = nwb['general']['intracellular_ephys']['whole_cell']['seal'].value
ie_slice = nwb['general']['intracellular_ephys']['whole_cell']['slice'].value

splittedstr = re.split(', |mm ',ie_location)
coord_ap_ml_dv = [float(splittedstr[0]),float(splittedstr[2]),float(splittedstr[4])] # make sure this is in mm

# -- BrainLocation
brain_region = splittedstr[-1]
hemi = 'left' # this whole study is on left hemi
reference.BrainLocation.insert1(
        {'brain_region': brain_region,
         'brain_subregion':'N/A',
         'cortical_layer': 'N/A',
         'hemisphere': hemi})

# -- ActionLocation
coordinate_ref = 'lambda' # double check!!
acquisition.ActionLocation.insert1(
        {'brain_region': brain_region,
         'brain_subregion':'N/A',
         'cortical_layer': 'N/A',
         'hemisphere': hemi,
         'coordinate_ref': coordinate_ref,
         'coordinate_ap':coord_ap_ml_dv[0],
         'coordinate_ml':coord_ap_ml_dv[1],
         'coordinate_dv':coord_ap_ml_dv[2]})

# -- Device
reference.Device.insert1({'device_name':ie_device})

# -- IntracellularInfo
cell_id = re.split('.nwb',session_id)[0]
acquisition.IntracellularInfo.insert1(
        {'subject_id':subject_id,
         'session_time': date_of_experiment,
         'cell_id':cell_id,
         'cell_type':'N/A',
         'brain_region': brain_region,
         'brain_subregion':'N/A',
         'cortical_layer': 'N/A',
         'hemisphere': hemi,
         'coordinate_ref': coordinate_ref,
         'coordinate_ap':coord_ap_ml_dv[0],
         'coordinate_ml':coord_ap_ml_dv[1],
         'coordinate_dv':coord_ap_ml_dv[2],
         'device_name':ie_device})

# ==================== Stimulation ====================

# -- read data - optogenetics
site_names = []
site_descs = []
site_excitation_lambdas = []
site_locations = []
for site in list(nwb['general']['optogenetics']):
    site_names.append(site)
    site_descs.append(nwb['general']['optogenetics'][site]['description'].value.decode('UTF-8'))
    site_excitation_lambdas.append(nwb['general']['optogenetics'][site]['excitation_lambda'].value.decode('UTF-8'))
    site_locations.append(nwb['general']['optogenetics'][site]['location'].value.decode('UTF-8'))


site_location = site_locations[0]
splittedstr = re.split(', |AP-|ML-|DV-',site_location)
coord_ap_ml_dv = [float(splittedstr[-5]),float(splittedstr[-3]),float(splittedstr[-1])] # make sure this is in mm

# -- BrainLocation
brain_region = splittedstr[0]
hemi = 'left' # this whole study is on left hemi
reference.BrainLocation.insert1(
        {'brain_region': brain_region,
         'brain_subregion':'N/A',
         'cortical_layer': 'N/A',
         'hemisphere': hemi})

# -- ActionLocation
coordinate_ref = 'lambda' # double check!!
acquisition.ActionLocation.insert1(
        {'brain_region': brain_region,
         'brain_subregion':'N/A',
         'cortical_layer': 'N/A',
         'hemisphere': hemi,
         'coordinate_ref': coordinate_ref,
         'coordinate_ap':coord_ap_ml_dv[0],
         'coordinate_ml':coord_ap_ml_dv[1],
         'coordinate_dv':coord_ap_ml_dv[2]})

# -- Device
stim_device = 'laser' # could not find a more specific name from metadata 
reference.Device.insert1({'device_name':stim_device, 'device_desc': devices[stim_device]})

# -- StimulationInfo
site_name = site_names[0]
acquisition.StimulationInfo.insert1(
        {'subject_id':subject_id,
         'session_time': date_of_experiment,
         'stim_id':site_name,
         'brain_region': brain_region,
         'brain_subregion':'N/A',
         'cortical_layer': 'N/A',
         'hemisphere': hemi,
         'coordinate_ref': coordinate_ref,
         'coordinate_ap':coord_ap_ml_dv[0],
         'coordinate_ml':coord_ap_ml_dv[1],
         'coordinate_dv':coord_ap_ml_dv[2],
         'device_name':stim_device})


# -- read data - electrical stimulation (current injection)









#########################################################################################################
#########################################################################################################
# nwb['file_create_date']
file_created_date = list(nwb['file_create_date'])

# nwb['general']
list(nwb['general'])
    # data_collection
data_collection = nwb['general']['data_collection'].value.decode('UTF-8')

    # lab
lab = nwb['general']['lab'].value

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
ci_desc = nwb['acquisition']['timeseries']['current_injection']['electrode']['description'].value
ci_device = nwb['acquisition']['timeseries']['current_injection']['electrode']['device'].value
ci_filtering = nwb['acquisition']['timeseries']['current_injection']['electrode']['filtering'].value
ci_initial_access_resistance = nwb['acquisition']['timeseries']['current_injection']['electrode']['initial_access_resistance'].value
ci_location = nwb['acquisition']['timeseries']['current_injection']['electrode']['location'].value
ci_resistance = nwb['acquisition']['timeseries']['current_injection']['electrode']['resistance'].value
ci_seal = nwb['acquisition']['timeseries']['current_injection']['electrode']['seal'].value
ci_slice = nwb['acquisition']['timeseries']['current_injection']['electrode']['slice'].value

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









