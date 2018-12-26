# -*- coding: utf-8 -*-
"""
Created on Mon Dec  3 16:22:42 2018

@author: thinh
"""
from datetime import datetime
import os
import re

import h5py as h5
import numpy as np

import datajoint as dj
from pipeline import reference, subject, acquisition, stimulation
from pipeline import helper_functions

############## Dataset #################
path = os.path.join('.','data','extracellular')
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
    subject_id = nwb['general']['subject']['subject_id'].value.decode('UTF-8')
    desc = nwb['general']['subject']['description'].value.decode('UTF-8')
    sex = nwb['general']['subject']['sex'].value.decode('UTF-8')
    species = nwb['general']['subject']['species'].value.decode('UTF-8')
    age = nwb['general']['subject']['age'].value.decode('UTF-8')
    genotype = nwb['general']['subject']['genotype'].value.decode('UTF-8')
        
    # dob and sex
    sex = sex[0].upper()
    splittedstr = re.split('dateOfBirth: ',desc)
    dob = splittedstr[-1].replace('\n','')
    dob = datetime.strptime(str(dob),'%Y-%m-%d') 

    # source and strain
    strain_str = re.search('(?<=animalStrain:\s)(.*)',desc) # extract the information related to animal strain
    if strain_str is not None: # if found, search found string to find matched strain in db
        for s in subject.StrainAlias.fetch():
            m = re.search(s[0], strain_str.group()) 
            if (m is not None):
                strain = (subject.StrainAlias & {'strain_alias':s[0]}).fetch1('strain')
                break
    source_str = re.search('(?<=animalSource:\s)(.*)',desc) # extract the information related to animal strain
    if source_str is not None: # if found, search found string to find matched strain in db
        for s in reference.AnimalSourceAlias.fetch():
            m = re.search(s[0], source_str.group()) 
            if (m is not None):
                animal_source = (reference.AnimalSourceAlias & {'animal_source_alias':s[0]}).fetch1('animal_source')
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
    experiment_description = nwb['general']['experiment_description'].value
    experimenter = np.array(nwb['general']['experimenter'])
    institution = nwb['general']['institution'].value
    related_publications = nwb['general']['related_publications'].value.decode('UTF-8') 
    #session_id = nwb['general']['session_id'].value
    surgery = nwb['general']['surgery'].value.decode('UTF-8')
    identifier = nwb['identifier'].value
    nwb_version = nwb['nwb_version'].value
    session_description = nwb['session_description'].value
    session_start_time = nwb['session_start_time'].value

    date_of_experiment = helper_functions.parse_prefix(session_start_time)

    # experimenter and experiment type (possible multiple experimenters or types)
    for k in np.arange(experimenter.size):
        reference.Experimenter.insert1({'experimenter': experimenter.item(k)},skip_duplicates=True)

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
            # there is still the ExperimentType part table here...
            print(f'Creating Session - Subject: {subject_id} - Date: {date_of_experiment}')


    # ==================== Extracellular ====================

    # -- read data - devices
    device_names = list(nwb['general']['devices'])
    # -- read data - electrodes
    electrodes = nwb['general']['extracellular_ephys']['electrodes']
    probe_placement_brain_loc = electrodes[0][5].decode('UTF-8')
    probe_placement_brain_loc = re.search("(?<=\[\')(.*)(?=\'\])",probe_placement_brain_loc).group()
    # -- Probe
    reference.Probe.insert1(
            {'probe_name' : device_names[0], 
             'channel_counts' : len(electrodes) },skip_duplicates=True)
    for electrode in electrodes:       
        reference.Probe.Channel.insert1(
                {'probe_name' : device_names[0], 
                 'channel_counts' : len(electrodes),
                 'channel_id' : electrode[0],
                 'channel_x_pos' : electrode[1],
                 'channel_y_pos' : electrode[2],
                 'channel_z_pos' : electrode[3],
                 'shank_id' : electrode[-2].decode('UTF-8')},skip_duplicates=True)
    # -- BrainLocation
    hemi = 'left' # this whole study is on left hemi
    reference.BrainLocation.insert1(
            {'brain_region': probe_placement_brain_loc,
             'brain_subregion':'N/A',
             'cortical_layer': 'N/A',
             'hemisphere': hemi},skip_duplicates=True)
    # -- ActionLocation
    coordinate_ref = 'bregma' # double check!!
    reference.ActionLocation.insert1(
            {'brain_region': probe_placement_brain_loc,
             'brain_subregion':'N/A',
             'cortical_layer': 'N/A',
             'hemisphere': hemi,
             'coordinate_ref': coordinate_ref,
             'coordinate_ap':coord_ap_ml_dv[0],
             'coordinate_ml':coord_ap_ml_dv[1],
             'coordinate_dv':coord_ap_ml_dv[2]},skip_duplicates=True)










