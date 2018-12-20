# -*- coding: utf-8 -*-
"""
Created on Mon Dec  3 16:22:42 2018

@author: thinh
"""
from datetime import datetime
import os
import re
import uuid

import h5py as h5
import matplotlib.pyplot as plt
import numpy as np

import datajoint as dj
from pipeline import reference, subject, acquisition, stimulation #, behavior, ephys, action
from pipeline.helper_functions import parse_prefix


# Merge all schema and generate the overall ERD (then save in "/images")
#all_erd = dj.ERD(reference) + dj.ERD(subject) + dj.ERD(action) + dj.ERD(acquisition) + dj.ERD(behavior) + dj.ERD(ephys) + dj.ERD(stimulation)
#all_erd.save('./images/all_erd.png')

# Merge all schema and generate the overall ERD (then save in "/images")
core_erd = dj.ERD(reference) + dj.ERD(subject) + dj.ERD(acquisition) + dj.ERD(stimulation)
core_erd.save('./images/core_erd.png')

############## Dataset #################
path = os.path.join('.','data','whole_cell_nwb2.0')
fnames = os.listdir(path)

for fname in fnames:
    try:
        nwb = h5.File(os.path.join(path,fname), 'r')
        print(f'File loaded: {fname}')
    except:
        print('=================================')
        print(f'!!! ERROR LOADING FILE: {fname}')   
        print('=================================')
        continue
    
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
    
    for k in np.arange(experimenter.size):
        reference.Experimenter.insert1({'experimenter': experimenter.item(k)},skip_duplicates=True)
    for k in np.arange(experiment_types.size):
        acquisition.ExperimentType.insert1({'experiment_type': experiment_types.item(k)},skip_duplicates=True)

    if date_of_experiment is not None: 
        with acquisition.Session.connection.transaction:
            acquisition.Session.insert1(            
                        {'subject_id':subject_id,
                         'session_time': date_of_experiment,
                         'session_note': session_description
                         },skip_duplicates=True)
            for k in np.arange(experimenter.size):
                acquisition.Session.Experimenter.insert1(            
                            {'subject_id':subject_id,
                             'session_time': date_of_experiment,
                             'experimenter': experimenter.item(k)
                             },skip_duplicates=True)
            for k in np.arange(experiment_types.size):
                acquisition.Session.ExperimentType.insert1(            
                            {'subject_id':subject_id,
                             'session_time': date_of_experiment,
                             'experiment_type': experiment_types.item(k)
                             },skip_duplicates=True)
            # there is still the ExperimentType part table here...
            print(f'\tSession created - Subject: {subject_id} - Date: {date_of_experiment}')
    
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
             'hemisphere': hemi},skip_duplicates=True)
    
    # -- ActionLocation
    coordinate_ref = 'bregma' # double check!!
    reference.ActionLocation.insert1(
            {'brain_region': brain_region,
             'brain_subregion':'N/A',
             'cortical_layer': 'N/A',
             'hemisphere': hemi,
             'coordinate_ref': coordinate_ref,
             'coordinate_ap':coord_ap_ml_dv[0],
             'coordinate_ml':coord_ap_ml_dv[1],
             'coordinate_dv':coord_ap_ml_dv[2]},skip_duplicates=True)
    
    # -- Whole Cell Device
    stim_device = ie_device
    reference.WholeCellDevice.insert1({'device_name':stim_device, 'device_desc': devices[stim_device]},skip_duplicates=True)
    
    # -- IntracellularInfo
    cell_id = re.split('.nwb',session_id)[0]
    acquisition.Cell.insert1(
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
             'device_name':ie_device},skip_duplicates=True)
        
    # -- read data - optogenetics
    opto_site_names = []
    opto_site_descs = []
    opto_excitation_lambdas = []
    opto_locations = []
    for site in list(nwb['general']['optogenetics']):
        opto_site_names.append(site)
        opto_site_descs.append(nwb['general']['optogenetics'][site]['description'].value.decode('UTF-8'))
        opto_excitation_lambdas.append(nwb['general']['optogenetics'][site]['excitation_lambda'].value.decode('UTF-8'))
        opto_locations.append(nwb['general']['optogenetics'][site]['location'].value.decode('UTF-8'))
    
    opto_location = opto_locations[0]
    splittedstr = re.split(', |AP-|ML-|DV-',opto_location)
    coord_ap_ml_dv = [float(splittedstr[-5]),float(splittedstr[-3]),float(splittedstr[-1])] # make sure this is in mm
    
    # -- BrainLocation
    brain_region = splittedstr[0]
    hemi = 'left' # this whole study is on left hemi
    reference.BrainLocation.insert1(
            {'brain_region': brain_region,
             'brain_subregion':'N/A',
             'cortical_layer': 'N/A',
             'hemisphere': hemi},skip_duplicates=True)
    
    # -- ActionLocation
    coordinate_ref = 'bregma' # double check!!
    reference.ActionLocation.insert1(
            {'brain_region': brain_region,
             'brain_subregion':'N/A',
             'cortical_layer': 'N/A',
             'hemisphere': hemi,
             'coordinate_ref': coordinate_ref,
             'coordinate_ap':coord_ap_ml_dv[0],
             'coordinate_ml':coord_ap_ml_dv[1],
             'coordinate_dv':coord_ap_ml_dv[2]},skip_duplicates=True)
    
    # -- Device
    stim_device = 'laser' # hard-coded here..., could not find a more specific name from metadata 
    stimulation.PhotoStimDevice.insert1({'device_name':stim_device, 'device_desc': devices[stim_device]},skip_duplicates=True)
    
    # -- StimulationInfo
    opto_site_name = opto_site_names[0]
    opto_wavelength = int(re.findall("\d+", opto_excitation_lambdas[0])[0])
    stimulation.PhotoStimulationInfo.insert1(
            {'photo_stim_id':opto_site_name,
             'brain_region': brain_region,
             'brain_subregion':'N/A',
             'cortical_layer': 'N/A',
             'hemisphere': hemi,
             'coordinate_ref': coordinate_ref,
             'coordinate_ap':coord_ap_ml_dv[0],
             'coordinate_ml':coord_ap_ml_dv[1],
             'coordinate_dv':coord_ap_ml_dv[2],
             'device_name':stim_device,
             'photo_stim_excitation_lambdas': float(opto_wavelength),
             'photo_stim_notes':opto_site_descs[0],},skip_duplicates=True)          

    # -- PhotoStimulation 
    # only 1 photostim per session, perform at the same time with session
    photostim_data = np.array(nwb['stimulus']['presentation']['photostimulus']['data'])
    photostim_timestamps = np.array(nwb['stimulus']['presentation']['photostimulus']['timestamps'])   
    acquisition.PhotoStimulation.insert1(
            {'subject_id':subject_id,
             'session_time': date_of_experiment,
             'photostim_datetime': date_of_experiment,
             'photo_stim_id':opto_site_name,
             'photostim_timeseries': photostim_data,
             'photostim_time_stamps': photostim_timestamps},skip_duplicates=True) 

    # -- finish manual ingestion for this file
    nwb.close()

# ====================== Starting import and compute procedure ======================

# -- Trial-related
acquisition.TrialSet.populate()

# -- Intracellular
acquisition.IntracellularAcquisition.populate()





















