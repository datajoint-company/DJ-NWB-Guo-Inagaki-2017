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
from pipeline import utilities

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

    date_of_experiment = utilities.parse_prefix(session_start_time) # info here is incorrect (see identifier)

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

    # ==================== Trials ====================
    key = {'subject_id': subject_id, 'session_time': date_of_experiment}
    trial_type_choices = {'L':'lick left','R':'lick right'} # map the hardcoded trial description read from data to the lookup table 'reference.TrialType'
    trial_resp_choices = {'Hit':'correct','Err':'incorrect','NoLick':'no response','LickEarly':'early lick'} # map the hardcoded trial description read from data to the lookup table 'reference.TrialResponse'
    photostim_period_choices = {1:'sample', 2:'delay', 3:'response'} 
    # -- read data -- nwb['epochs']
    trial_names = []
    tags = []
    start_times = []
    stop_times = []
    for trial in list(nwb['epochs']):
        trial_names.append(trial)
        tags.append(nwb['epochs'][trial]['tags'].value)
        start_times.append(nwb['epochs'][trial]['start_time'].value)
        stop_times.append(nwb['epochs'][trial]['stop_time'].value)
    
    # -- read data -- nwb['analysis']
    trial_type_string = np.array(nwb['analysis']['trial_type_string'])
    trial_type_mat = np.array(nwb['analysis']['trial_type_mat'])
    # -- read data -- nwb['stimulus']['presentation'])
    auditory_cue = np.array(nwb['stimulus']['presentation']['auditory_cue']['timestamps'])
    pole_in_times = np.array(nwb['stimulus']['presentation']['pole_in']['timestamps'])
    pole_out_times = np.array(nwb['stimulus']['presentation']['pole_out']['timestamps'])
    nwb.close()
    
    # form new key-values pair and insert key
    key['trial_counts'] = len(trial_names)
    acquisition.TrialSet.insert1(key)
    print(f'Inserted trial set for session: Subject: {subject_id} - Date: {date_of_experiment}')
    print('Inserting trial ID: ', end="")
    
    # loop through each trial and insert
    for idx, trialId in enumerate(trial_names):
        key['trial_id'] = trialId.lower()
        # -- start/stop time
        key['start_time'] = start_times[idx]
        key['stop_time'] = stop_times[idx]
        # -- events timing
        key['cue_start_time'] = auditory_cue[idx]
        key['pole_in_time'] = pole_in_times[idx]
        key['pole_out_time'] = pole_out_times[idx]            
        # form new key-values pair for trial_partkey and insert
        acquisition.TrialSet.Trial.insert1(key, ignore_extra_fields=True)
        print(f'{trialId} ',end="")
        
        # ======== Now add trial descriptors to the TrialInfo part table ====
        # search through all keyword in trial descriptor tags (keywords are not in fixed order)
        for tag in tags[idx]:
            # good/bad
            key['trial_is_good'] = (re.match('good', tag, re.I) is not None)
            # stim/no-stim
            key['trial_stim_present'] = (re.match('non-stimulation',tag,re.I) is None)
            # trial type: left/right lick
            m = re.match('Hit|Err|NoLick',tag)
            key['trial_type'] = 'non-performing' if (m is None) else trial_type_choices[tag[m.end()]]
            # trial response type: correct, incorrect, early lick, no response
            if ('trial_response' in key) and (key['trial_response'] != 'early lick'):
                m = re.match('Hit|Err|NoLick|LickEarly',tag)
                key['trial_response'] = 'N/A' if (m is None) else trial_resp_choices[m.group()]
            # photo stim type: stimulation, inhibition, or N/A (for non-stim trial)
            m = re.match('PhotoStimulation|PhotoInhibition', tag, re.I)
            key['photo_stim_type'] = 'N/A' if (m is None) else m.group().replace('Photo','').lower()
        # insert
        acquisition.TrialSet.TrialInfo.insert1(key, ignore_extra_fields=True)
        
        # ======== Now add trial stimulation descriptors to the TrialStimInfo part table ====
        key['photo_stim_period'] = 'N/A' if trial_type_mat[idx,-5] == 0 else photostim_period_choices[trial_type_mat[idx,-5]]
        key['photo_stim_power'] = trial_type_mat[idx,-4]
        key['photo_loc_galvo_x'] = trial_type_mat[idx,-3]
        key['photo_loc_galvo_y'] = trial_type_mat[idx,-2]
        key['photo_loc_galvo_z'] = trial_type_mat[idx,-1]
        # insert
        acquisition.TrialSet.TrialStimInfo.insert1(key, ignore_extra_fields=True)
    print('')

    # ==================== Extracellular ====================

    # -- read data - devices
    device_names = list(nwb['general']['devices'])
    # -- read data - electrodes
    electrodes = nwb['general']['extracellular_ephys']['electrodes']
    probe_placement_brain_loc = electrodes[0][5].decode('UTF-8')  # get probe placement from 0th electrode (should be the same for all electrodes)
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
    ground_coordinates = nwb['general']['extracellular_ephys']['ground_coordinates'].value  # using 'ground_coordinates' here as the x, y, z for where the probe is placed in the brain, TODO double check if this is correct
    coordinate_ref = 'bregma' 
    reference.ActionLocation.insert1(
            {'brain_region': probe_placement_brain_loc,
             'brain_subregion':'N/A',
             'cortical_layer': 'N/A',
             'hemisphere': hemi,
             'coordinate_ref': coordinate_ref,
             'coordinate_ap':ground_coordinates[0],
             'coordinate_ml':ground_coordinates[1],
             'coordinate_dv':ground_coordinates[2]}, skip_duplicates=True)
    # -- Extracellular
    acquisition.Extracellular.insert1(
            {'subject_id' : subject_id,
             'session_time': date_of_experiment,
             'brain_region': probe_placement_brain_loc,
             'brain_subregion' : 'N/A',
             'cortical_layer': 'N/A',
             'hemisphere': hemi,
             'coordinate_ref': coordinate_ref,
             'coordinate_ap':ground_coordinates[0],
             'coordinate_ml':ground_coordinates[1],
             'coordinate_dv':ground_coordinates[2],
             'probe_name' : device_names[0]}, skip_duplicates=True)








