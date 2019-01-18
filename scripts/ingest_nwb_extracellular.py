# -*- coding: utf-8 -*-
"""
Created on Mon Dec  3 16:22:42 2018

@author: thinh
"""
from datetime import datetime
import os
import re
os.chdir('..')
import h5py as h5
import numpy as np

import datajoint as dj
from pipeline import reference, subject, acquisition, stimulation, analysis
from pipeline import utilities

############## Dataset #################
path = os.path.join('.','data','extracellular','datafiles')
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
    dob = re.search('(?<=dateOfBirth:\s)(.*)(?=\n)',desc)
    dob = utilities.parse_prefix(dob.group())
    
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
                 'species':species,
                 'strain':strain,
                 'animal_source':animal_source,
                 'sex': sex,
                 'subject_description':desc}, 
                 skip_duplicates=True)

    # ==================== session ====================
    experiment_description = nwb['general']['experiment_description'].value
    experimenter = np.array(nwb['general']['experimenter'])
    institution = nwb['general']['institution'].value
    related_publications = nwb['general']['related_publications'].value.decode('UTF-8') 
    # session_id = nwb['general']['session_id'].value
    surgery = nwb['general']['surgery'].value.decode('UTF-8')
    identifier = nwb['identifier'].value
    nwb_version = nwb['nwb_version'].value
    session_description = nwb['session_description'].value
    session_start_time = nwb['session_start_time'].value

    date_of_experiment = utilities.parse_prefix(session_start_time) # info here is incorrect (see identifier)
    # due to incorrect info in "session_start_time" - temporary fix: use info in 'identifier'
    date_of_experiment = re.split(';\s?',identifier)[-1].replace('T',' ')
    date_of_experiment = utilities.parse_prefix(date_of_experiment) 

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
    cue_duration = 0.1  # hard-coded the fact that an auditory cue last 0.1 second
    auditory_cue = np.array(nwb['stimulus']['presentation']['auditory_cue']['timestamps'])
    pole_in_times = np.array(nwb['stimulus']['presentation']['pole_in']['timestamps'])
    pole_out_times = np.array(nwb['stimulus']['presentation']['pole_out']['timestamps'])
    
    # form new key-values pair and insert key
    key['trial_counts'] = len(trial_names)
    acquisition.TrialSet.insert1(key, skip_duplicates=True, allow_direct_insert=True)
    print(f'Inserted trial set for session: Subject: {subject_id} - Date: {date_of_experiment}')
    print('Inserting trial ID: ', end="")
    
    # loop through each trial and insert
    for idx, trial_id in enumerate(trial_names):
        trial_id = int(re.search('(\d+)', trial_id).group())
        key['trial_id'] = trial_id
        # -- start/stop time
        key['start_time'] = start_times[idx]
        key['stop_time'] = stop_times[idx]
        # ======== Now add trial descriptors ====
        # search through all keyword in trial descriptor tags (keywords are not in fixed order)
        tag_key = {}
        tag_key['trial_is_good'] = False
        tag_key['trial_stim_present'] = True
        tag_key['trial_type'] = 'non-performing'
        tag_key['trial_response'], tag_key['photo_stim_type'] = 'N/A', 'N/A'
        for tag in tags[idx]:
            # good/bad
            if not tag_key['trial_is_good']:
                tag_key['trial_is_good'] = (re.match('good', tag, re.I) is not None)
            # stim/no-stim
            if tag_key['trial_stim_present']:
                tag_key['trial_stim_present'] = (re.match('non-stimulation', tag, re.I) is None)
            # trial type: left/right lick
            if tag_key['trial_type'] == 'non-performing':
                m = re.match('Hit|Err|NoLick', tag)
                tag_key['trial_type'] = 'non-performing' if (m is None) else trial_type_choices[tag[m.end()]]
            # trial response type: correct, incorrect, early lick, no response
            if tag_key['trial_response'] == 'N/A' or tag_key['trial_response'] != 'early lick':
                m = re.match('Hit|Err|NoLick|LickEarly', tag)
                if m: m.group()
                tag_key['trial_response'] = trial_resp_choices[m.group()] if m else tag_key['trial_response']
            # photo stim type: stimulation, inhibition, or N/A (for non-stim trial)
            if tag_key['photo_stim_type'] == 'N/A':
                m = re.match('PhotoStimulation|PhotoInhibition', tag, re.I)
                tag_key['photo_stim_type'] = 'N/A' if (m is None) else m.group().replace('Photo','').lower()
        # insert
        acquisition.TrialSet.Trial.insert1({**key, **tag_key}, ignore_extra_fields=True, skip_duplicates=True, allow_direct_insert=True)
        # ======== Now add trial event timing to the TrialInfo part table ====
        # -- events timing
        acquisition.TrialSet.EventTime.insert1(dict(key, trial_event='trial_start', event_time = start_times[idx]),
                                               ignore_extra_fields=True, skip_duplicates=True, allow_direct_insert=True)
        acquisition.TrialSet.EventTime.insert1(dict(key, trial_event='trial_stop', event_time = stop_times[idx]),
                                               ignore_extra_fields=True, skip_duplicates=True, allow_direct_insert=True)
        acquisition.TrialSet.EventTime.insert1(dict(key, trial_event='cue_start', event_time = auditory_cue[idx]),
                                               ignore_extra_fields=True, skip_duplicates=True, allow_direct_insert=True)
        acquisition.TrialSet.EventTime.insert1(dict(key, trial_event='cue_end', event_time = auditory_cue[idx] + cue_duration),  
                                               ignore_extra_fields=True, skip_duplicates=True, allow_direct_insert=True)  # hard-coded cue_end time here 
        acquisition.TrialSet.EventTime.insert1(dict(key, trial_event='pole_in', event_time = pole_in_times[idx]),
                                               ignore_extra_fields=True, skip_duplicates=True, allow_direct_insert=True)
        acquisition.TrialSet.EventTime.insert1(dict(key, trial_event='pole_out', event_time = pole_out_times[idx]),
                                               ignore_extra_fields=True, skip_duplicates=True, allow_direct_insert=True)          
        # ======== Now add trial stimulation descriptors to the TrialStimInfo table ====
        key['photo_stim_period'] = 'N/A' if trial_type_mat[-5, idx] == 0 else photostim_period_choices[trial_type_mat[-5, idx]]
        key['photo_stim_power'] = trial_type_mat[-4, idx]
        key['photo_loc_galvo_x'] = trial_type_mat[-3, idx]
        key['photo_loc_galvo_y'] = trial_type_mat[-2, idx]
        key['photo_loc_galvo_z'] = trial_type_mat[-1, idx]
        # insert
        acquisition.TrialStimInfo.insert1(key, ignore_extra_fields=True, skip_duplicates=True, allow_direct_insert=True)
        print(f'{trial_id} ', end="")
    print('')

    # ==================== Extracellular ====================
    # -- read data - devices
    device_names = list(nwb['general']['devices'])
    # -- read data - electrodes
    electrodes = nwb['general']['extracellular_ephys']['electrodes']
    probe_placement_brain_loc = electrodes[0][5].decode('UTF-8')  # get probe placement from 0th electrode (should be the same for all electrodes)
    probe_placement_brain_loc = re.search("(?<=\[\')(.*)(?=\'\])",probe_placement_brain_loc).group()
    
    # hemisphere: left-hemisphere is ipsi, so anything contra is right
    brain_region, hemi = utilities.get_brain_hemisphere(probe_placement_brain_loc)
    
    # -- Probe
    reference.Probe.insert1(
            {'probe_name' : device_names[0], 
             'channel_counts' : len(electrodes) }, skip_duplicates=True)
    for electrode in electrodes:       
        shank_id = electrode[-2].decode('UTF-8')
        shank_id = int(re.search('\d+',shank_id).group())
        reference.Probe.Channel.insert1(
                {'probe_name' : device_names[0], 
                 'channel_id' : electrode[0],
                 'channel_x_pos' : electrode[1],
                 'channel_y_pos' : electrode[2],
                 'channel_z_pos' : electrode[3],
                 'shank_id' : shank_id}, skip_duplicates=True)
    # -- BrainLocation
    reference.BrainLocation.insert1(
            {'brain_region': probe_placement_brain_loc,
             'brain_subregion':'N/A',
             'cortical_layer': 'N/A',
             'hemisphere': hemi}, skip_duplicates=True)
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
    # -- ProbeInsertion
    acquisition.ProbeInsertion.insert1(
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

    # ==================== Photo stimulation ====================
    # -- Device
    stim_device = 'laser' # hard-coded here..., could not find a more specific name from metadata 
    stimulation.PhotoStimDevice.insert1({'device_name':stim_device}, skip_duplicates=True)

    # -- read data - optogenetics
    opto_site_name = list(nwb['general']['optogenetics'].keys())[0]
    opto_descs = nwb['general']['optogenetics'][opto_site_name]['description'].value.decode('UTF-8')
    opto_excitation_lambda = nwb['general']['optogenetics'][opto_site_name]['excitation_lambda'].value.decode('UTF-8')
    opto_location = nwb['general']['optogenetics'][opto_site_name]['location'].value.decode('UTF-8')
    opto_stimulation_method = nwb['general']['optogenetics'][opto_site_name]['stimulation_method'].value.decode('UTF-8')

    brain_region = re.search('(?<=atlas location:\s)(.*)', opto_location).group()
    
    # hemisphere: left-hemisphere is ipsi, so anything contra is right
    brain_region, hemi = utilities.get_brain_hemisphere(brain_region)
    
    # if no brain region (NA, or N/A, or ' '), skip photostim insert
    if re.search('\s+|N/?A', brain_region) is None:
        
        coord_ap_ml_dv = re.search('(?<=\[)(.*)(?=\])', opto_location).group()
        coord_ap_ml_dv = re.split(',',coord_ap_ml_dv)

        # -- BrainLocation
        reference.BrainLocation.insert1(
                {'brain_region': brain_region,
                 'brain_subregion':'N/A',
                 'cortical_layer': 'N/A',
                 'hemisphere': hemi}, skip_duplicates=True)
        
        # -- ActionLocation
        coordinate_ref = 'bregma' # double check!!
        reference.ActionLocation.insert1(
                {'brain_region': brain_region,
                 'brain_subregion':'N/A',
                 'cortical_layer': 'N/A',
                 'hemisphere': hemi,
                 'coordinate_ref': coordinate_ref,
                 'coordinate_ap': float(coord_ap_ml_dv[0]),
                 'coordinate_ml': float(coord_ap_ml_dv[1]),
                 'coordinate_dv': float(coord_ap_ml_dv[2])}, skip_duplicates=True)
            
        # -- PhotoStimulationInfo
        stimulation.PhotoStimulationInfo.insert1(
                {'brain_region': brain_region,
                 'brain_subregion':'N/A',
                 'cortical_layer': 'N/A',
                 'hemisphere': hemi,
                 'coordinate_ref': coordinate_ref,
                 'coordinate_ap':float(coord_ap_ml_dv[0]),
                 'coordinate_ml':float(coord_ap_ml_dv[1]),
                 'coordinate_dv':float(coord_ap_ml_dv[2]),
                 'device_name':stim_device,
                 'photo_stim_excitation_lambda': float(opto_excitation_lambda),
                 'photo_stim_notes':f'{opto_site_name} - {opto_descs}'}, skip_duplicates=True)
    
        # -- PhotoStimulation 
        # only 1 photostim per session, perform at the same time with session
        photostim_data = nwb['stimulus']['presentation']['photostimulus_1']['data'].value
        photostim_timestamps = nwb['stimulus']['presentation']['photostimulus_1']['timestamps'].value   
        # if the dataset does not contain photostim timeseries set to None
        photostim_data = None if not isinstance(photostim_data, np.ndarray) else photostim_data
        photostim_timestamps = None if not isinstance(photostim_timestamps, np.ndarray) else photostim_timestamps
        photostim_start_time = None if not isinstance(photostim_timestamps, np.ndarray) else photostim_timestamps[0]
        photostim_sampling_rate = None if not isinstance(photostim_timestamps, np.ndarray) else 1/np.mean(np.diff(photostim_timestamps))
            
        acquisition.PhotoStimulation.insert1(
                {'subject_id':subject_id,
                 'session_time': date_of_experiment,
                 'photostim_datetime': date_of_experiment,
                 'brain_region': brain_region,
                 'brain_subregion':'N/A',
                 'cortical_layer': 'N/A',
                 'hemisphere': hemi,
                 'coordinate_ref': coordinate_ref,
                 'coordinate_ap':float(coord_ap_ml_dv[0]),
                 'coordinate_ml':float(coord_ap_ml_dv[1]),
                 'coordinate_dv':float(coord_ap_ml_dv[2]),
                 'device_name':stim_device,
                 'photo_stim_excitation_lambda': float(opto_excitation_lambda),
                 'photostim_timeseries': photostim_data,
                 'photostim_start_time': photostim_start_time,
                 'photostim_sampling_rate': photostim_sampling_rate}, skip_duplicates=True) 

    # -- finish manual ingestion for this file
    nwb.close()

# ====================== Starting import and compute procedure ======================

# -- Ingest unit spike times
acquisition.UnitSpikeTimes.populate()
# -- UnitSpikeTimes trial-segmentation
analysis.TrialSegmentedUnitSpikeTimes.populate()
