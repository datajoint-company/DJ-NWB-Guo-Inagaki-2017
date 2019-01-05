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
from pipeline import reference, subject, acquisition, stimulation, analysis #, behavior, ephys, action
from pipeline import utilities


# Merge all schema and generate the overall ERD (then save in "/images")
all_erd = dj.ERD(reference) + dj.ERD(subject) + dj.ERD(stimulation) + dj.ERD(acquisition)  + dj.ERD(analysis) #+ dj.ERD(behavior) + dj.ERD(ephys) + dj.ERD(action)  
all_erd.save('./images/all_erd.png')

acq_erd = dj.ERD(acquisition)
acq_erd.save('./images/acquisition_erd.png')

analysis_erd = dj.ERD(analysis)
analysis_erd.save('./images/analysis_erd.png')


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
    subject_id = nwb['general']['subject']['subject_id'].value.decode('UTF-8')
    desc = nwb['general']['subject']['description'].value.decode('UTF-8')
    sex = nwb['general']['subject']['sex'].value.decode('UTF-8')
    species = nwb['general']['subject']['species'].value.decode('UTF-8')
    weight = nwb['general']['subject']['weight'].value.decode('UTF-8') 
    age = nwb['general']['subject']['age'].value.decode('UTF-8')
    genotype = nwb['general']['subject']['genotype'].value.decode('UTF-8')
    
    # dob and sex
    sex = sex[0].upper()
    dob = re.search('(?<=Date of birth:\s)(.*)', desc)
    dob = utilities.parse_prefix(dob.group())
        
    # source and strain
    strain_str = re.search('(?<=Animal Strain:\s)(.*)',desc) # extract the information related to animal strain
    if strain_str is not None: # if found, search found string to find matched strain in db
        for s in subject.StrainAlias.fetch():
            m = re.search(s[0], strain_str.group()) 
            if (m is not None):
                strain = (subject.StrainAlias & {'strain_alias':s[0]}).fetch1('strain')
                break
    source_str = re.search('(?<=Animal source:\s)(.*)',desc) # extract the information related to animal strain
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
    experimenter = nwb['general']['experimenter'].value
    institution = nwb['general']['institution'].value
    related_publications = nwb['general']['related_publications'].value.decode('UTF-8') 
    session_id = nwb['general']['session_id'].value
    surgery = nwb['general']['surgery'].value.decode('UTF-8')
    identifier = nwb['identifier'].value
    nwb_version = nwb['nwb_version'].value
    session_description = nwb['session_description'].value
    session_start_time = nwb['session_start_time'].value
    
    # -- session_time 
    date_of_experiment = utilities.parse_prefix(session_start_time)
    experiment_types = re.split('Experiment type: ',experiment_description)[-1]
    experiment_types = re.split(',\s?',experiment_types)
    
    # experimenter and experiment type (possible multiple experimenters or types)
    experimenter = [experimenter] if np.array(experimenter).size <= 1 else  experimenter  # in case there's only 1 experimenter
        
    for k in experimenter:
        reference.Experimenter.insert1({'experimenter': k},skip_duplicates=True)
    for k in experiment_types:
        acquisition.ExperimentType.insert1({'experiment_type': k},skip_duplicates=True)

    if date_of_experiment is not None: 
        with acquisition.Session.connection.transaction:
            acquisition.Session.insert1(            
                        {'subject_id':subject_id,
                         'session_time': date_of_experiment,
                         'session_note': session_description
                         },skip_duplicates=True)
            for k in experimenter:
                acquisition.Session.Experimenter.insert1(            
                            {'subject_id':subject_id,
                             'session_time': date_of_experiment,
                             'experimenter': k
                             },skip_duplicates=True)
            for k in experiment_types:
                acquisition.Session.ExperimentType.insert1(            
                            {'subject_id':subject_id,
                             'session_time': date_of_experiment,
                             'experiment_type': k
                             },skip_duplicates=True)
            # there is still the ExperimentType part table here...
            print(f'Creating Session - Subject: {subject_id} - Date: {date_of_experiment}')

    # ==================== Trials ====================
    key = {'subject_id': subject_id, 'session_time': date_of_experiment}
    # -- read data -- nwb['epochs']
    trial_names = []
    trial_descs = []
    start_times = []
    stop_times = []
    for trial in list(nwb['epochs']):
        trial_names.append(trial)
        trial_descs.append(nwb['epochs'][trial]['description'].value)
        start_times.append(nwb['epochs'][trial]['start_time'].value)
        stop_times.append(nwb['epochs'][trial]['stop_time'].value)
    # -- read data -- nwb['analysis']
    good_trials = np.array(nwb['analysis']['good_trials'])
    trial_type_string = np.array(nwb['analysis']['trial_type_string'])
    trial_type_mat = np.array(nwb['analysis']['trial_type_mat'])
    # -- read data -- nwb['stimulus']['presentation'])
    cue_start_times = np.array(nwb['stimulus']['presentation']['cue_start']['timestamps'])
    cue_end_times = np.array(nwb['stimulus']['presentation']['cue_end']['timestamps'])
    pole_in_times = np.array(nwb['stimulus']['presentation']['pole_in']['timestamps'])
    pole_out_times = np.array(nwb['stimulus']['presentation']['pole_out']['timestamps'])
    
    # form new key-values pair and insert key
    key['trial_counts'] = len(trial_names)
    acquisition.TrialSet.insert1(key, skip_duplicates=True, allow_direct_insert=True)
    print(f'Inserted trial set for session: Subject: {subject_id} - Date: {date_of_experiment}')
    print('Inserting trial ID: ', end="")
    
    # loop through each trial and insert
    for idx, trial_id in enumerate(trial_names):
        trial_id = int(re.search('\d+',trial_id).group())
        key['trial_id'] = trial_id
        # -- start/stop time
        key['start_time'] = start_times[idx]
        key['stop_time'] = stop_times[idx]
        # ======== Now add trial descriptors ====
        # - good/bad trial_status (nwb['analysis']['good_trials'])
        key['trial_is_good'] = True if good_trials.flatten()[idx] == 1 else False
        # - trial_type and trial_stim_present (nwb['epochs'][trial]['description']) 
        trial_type, trial_stim_present =  re.split(', ',trial_descs[idx])
        trial_type_choices = {'lick l trial':'lick left','lick r trial':'lick right'} # map the hardcoded trial description read from data to the lookup table 'reference.TrialType'
        key['trial_type'] = trial_type_choices.get(trial_type.lower(),'N/A')
        key['trial_stim_present'] = (trial_stim_present == 'Stim')
        # - trial_response (nwb['analysis']['trial_type_string'])
        # note, the last type_string value is duplicated info of "stim"/"no stim" above, so ignore it here (hence the [idx,:-1])
        match_idx = np.where(trial_type_mat[idx,:-1] == 1)
        trial_response =  trial_type_string.flatten()[match_idx].item(0).decode('UTF-8')
        if re.search('correct',trial_response.lower()) is not None:
            trial_response = 'correct'
        elif re.search('incorrect',trial_response.lower()) is not None:
            trial_response = 'incorrect'
        key['trial_response'] = trial_response.lower()
        # insert
        acquisition.TrialSet.Trial.insert1(key, ignore_extra_fields=True, skip_duplicates=True, allow_direct_insert=True)
        # ======== Now add trial event timing to the TrialInfo part table ====
        # -- events timing
        key['cue_start_time'] = cue_start_times[idx]
        key['cue_end_time'] = cue_end_times[idx]
        key['pole_in_time'] = pole_in_times[idx]
        key['pole_out_time'] = pole_out_times[idx]            
        # insert
        acquisition.TrialSet.CuePoleTiming.insert1(key, ignore_extra_fields=True, skip_duplicates=True, allow_direct_insert=True)
        print(f'{trial_id} ',end="")
    print('')

    # ==================== Intracellular ====================
            
    # -- read data - devices
    devices = {}
    for d in list(nwb['general']['devices']):
        devices[d] = nwb['general']['devices'][d].value.decode('UTF-8')
        
    # -- read data - intracellular_ephys
    ie_device = nwb['general']['intracellular_ephys']['whole_cell']['device'].value
    ie_filtering = nwb['general']['intracellular_ephys']['whole_cell']['filtering'].value
    ie_location = nwb['general']['intracellular_ephys']['whole_cell']['location'].value
    
    brain_region = re.split(',\s?',ie_location)[-1]
    coord_ap_ml_dv = re.findall('\d+.\d+',ie_location)
    
    # hemisphere: left-hemisphere is ipsi, so anything contra is right
    brain_region, hemi = utilities.get_brain_hemisphere(brain_region)
        
    # -- BrainLocation
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
             'coordinate_ap':float(coord_ap_ml_dv[0]),
             'coordinate_ml':float(coord_ap_ml_dv[1]),
             'coordinate_dv':float(coord_ap_ml_dv[2])},skip_duplicates=True)
    
    # -- Whole Cell Device
    stim_device = ie_device
    reference.WholeCellDevice.insert1({'device_name':stim_device, 'device_desc': devices[stim_device]},skip_duplicates=True)
    
    # -- Cell
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
             'coordinate_ap':float(coord_ap_ml_dv[0]),
             'coordinate_ml':float(coord_ap_ml_dv[1]),
             'coordinate_dv':float(coord_ap_ml_dv[2]),
             'device_name':ie_device},skip_duplicates=True)

    # ==================== Photo stimulation ====================    
    # -- read data - optogenetics
    opto_site_name = list(nwb['general']['optogenetics'].keys())[0]
    opto_descs = nwb['general']['optogenetics'][opto_site_name]['description'].value.decode('UTF-8')
    opto_excitation_lambda = nwb['general']['optogenetics'][opto_site_name]['excitation_lambda'].value.decode('UTF-8')
    opto_location = nwb['general']['optogenetics'][opto_site_name]['location'].value.decode('UTF-8')
    
    splittedstr = re.split(',\s?coordinates:\s?',opto_location)
    brain_region = splittedstr[0]
    coord_ap_ml_dv = re.findall('\d+.\d+',splittedstr[-1])
    
    # hemisphere: left-hemisphere is ipsi, so anything contra is right
    brain_region, hemi = utilities.get_brain_hemisphere(brain_region)
        
    # -- BrainLocation
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
             'coordinate_ap':float(coord_ap_ml_dv[0]),
             'coordinate_ml':float(coord_ap_ml_dv[1]),
             'coordinate_dv':float(coord_ap_ml_dv[2])},skip_duplicates=True)
    
    # -- Device
    stim_device = 'laser' # hard-coded here..., could not find a more specific name from metadata 
    stimulation.PhotoStimDevice.insert1({'device_name':stim_device, 'device_desc': devices[stim_device]},skip_duplicates=True)
    
    # -- PhotoStimulationInfo
    opto_excitation_lambda = re.search("\d+", opto_excitation_lambda).group()
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
             'photo_stim_notes':(f'{opto_site_name} - {opto_descs}')},skip_duplicates=True)          

    # -- PhotoStimulation 
    # only 1 photostim per session, perform at the same time with session
    photostim_data = nwb['stimulus']['presentation']['photostimulus']['data'].value
    photostim_timestamps = nwb['stimulus']['presentation']['photostimulus']['timestamps'].value   
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
             'photostim_start_time': photostim_timestamps[0],
             'photostim_sampling_rate': 1/np.mean(np.diff(photostim_timestamps))},skip_duplicates=True) 

    # -- finish manual ingestion for this file
    nwb.close()

# ====================== Starting import and compute procedure ======================

# -- Intracellular
acquisition.IntracellularAcquisition.populate()
# -- Behavioral
acquisition.BehaviorAcquisition.populate()
# -- Perform trial segmentation
analysis.TrialSegmentedBehavior.populate()
analysis.TrialSegmentedIntracellular.populate()
analysis.TrialSegmentedPhotoStimulus.populate()



