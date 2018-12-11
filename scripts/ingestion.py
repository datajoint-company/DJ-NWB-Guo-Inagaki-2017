import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio
import os
from datetime import datetime
import re

from pipeline.helper_functions import get_one_from_nested_array, extract_datetime

############## Dataset #################
# (this needs to be placed in a config file somewhere)
data_dir = os.path.abspath('..//NWB_Janelia_datasets//crcns_ssc5_data_HiresGutnisky2015//')
meta_data_dir = os.path.join(data_dir,'metadata')
sess_data_dir = os.path.join(data_dir,'datafiles')

#################################
import datajoint as dj

dj.config['database.host'] = 'tutorial-db.datajoint.io' # this goes to config file as well

import pipeline
from pipeline import reference, subject, acquisition, behavior, ephys, action

# Merge all schema and generate the overall ERD (then save in "/images")
all_erd = dj.ERD(reference) + dj.ERD(subject) + dj.ERD(action) + dj.ERD(acquisition) + dj.ERD(behavior) + dj.ERD(ephys)
all_erd.save('./images/all_erd.png')

############## INGESTION #################

# ===================== Part 1: metadata ========

meta_data_files = os.listdir(meta_data_dir)
for metadatafile in meta_data_files:    
    print(metadatafile)
    matfile = sio.loadmat(os.path.join(meta_data_dir,metadatafile), struct_as_record=False)
    metadata = matfile['meta_data'][0,0]
    
    animal_ID = get_one_from_nested_array(metadata.animal_ID).upper()            # subject.Subject # .upper() here to handle some inconsistencies in the dataset
    animal_background = get_one_from_nested_array(metadata.animal_background)    # empty
    cell = get_one_from_nested_array(metadata.cell)                              # reference.Cell
    dob = get_one_from_nested_array(metadata.data_of_birth)                      # subject.Subject
    dob = extract_datetime(dob) # map this date string to datetime object

    date_of_experiment = get_one_from_nested_array(metadata.date_of_experiment)  # acquisition.Session
    date_of_experiment = extract_datetime(date_of_experiment) # map this date string to datetime object
    
    experiment_type = metadata.experiment_type
    
    experimenters = get_one_from_nested_array(metadata.experimenters)            # reference.Experimenter
    fiber = metadata.fiber # empty
    manipulation_type = get_one_from_nested_array(metadata.manipulation_type)    # not sure
    onsetLatency = get_one_from_nested_array(metadata.onsetLatency)              # not sure
    sex = get_one_from_nested_array(metadata.sex)                                # subject.Subject
    source_gene_copy = get_one_from_nested_array(metadata.source_gene_copy)      # probably  reference.SourceStrain (not implemented)
    source_identifier = get_one_from_nested_array(metadata.source_identifier)    # reference.AnimalSource
    source_strain = get_one_from_nested_array(metadata.source_strain)            # subject.Allele
    source_transgene = get_one_from_nested_array(metadata.source_transgene)      # not sure
    species = get_one_from_nested_array(metadata.species)                        # subject.Species
    weight_after_experiment = get_one_from_nested_array(metadata.weight_after_experiment)   # action.Weighing
    weight_before_experiment = get_one_from_nested_array(metadata.weight_before_experiment) # action.Weighing
    whisker = get_one_from_nested_array(metadata.whisker)                        # reference.Whisker
    
    extracellular = metadata.extracellular[0,0] if metadata.extracellular.size != 0 else None  
    if  extracellular is not None:
        atlas_location = get_one_from_nested_array(extracellular.atlas_location)       # not sure
        cell_type = get_one_from_nested_array(extracellular.cell_type)                 # reference.Cell
        ground_location =  get_one_from_nested_array(extracellular.ground_location)    # not sure 
        identification_method =  get_one_from_nested_array(extracellular.identification_method) # not sure
        nth_time_accessing_tissue =  get_one_from_nested_array(extracellular.nth_time_accessing_tissue)
        probe_type =  get_one_from_nested_array(extracellular.probe_type)              # probably reference.Device (not implemented)
        recording_coord_location = get_one_from_nested_array(extracellular.recording_coord_location[0,0]) # reference.BrainLocation
        recording_coord_depth =    get_one_from_nested_array(extracellular.recording_coord_location[0,1]) # acquisition.RecordingLocation 
        recording_location_marker =  get_one_from_nested_array(extracellular.recording_location_marker) # not sure
        recording_type = get_one_from_nested_array(extracellular.recording_type)       # not sure
        ref_loc =  get_one_from_nested_array(extracellular.ref_loc)                            # not sure
    else: 
        atlas_location, cell_type, ground_location, identification_method, nth_time_accessing_tissue, \
        probe_type, recording_coord_location, recording_coord_depth, recording_location_marker, \
        recording_type, ref_loc = None, None, None, None, None, None, None, None, None, None, None 
    
    behaviorInfo = metadata.behavior[0,0] if metadata.behavior.size != 0 else None  
    if  behaviorInfo is not None:
        task_keyword = behaviorInfo.task_keyword                        # not sure
    else: task_keyword = None
    
    photostim = metadata.photostim[0,0] if metadata.photostim.size != 0 else None    
    if  photostim is not None:
        #stim_lambda =                                                        # acquisition.PhotoStim
        photostim_atlas_location = get_one_from_nested_array(photostim.photostim_atlas_location) # acquisition.PhotoStim
        photostim_coord_location = get_one_from_nested_array(photostim.photostim_coord_location) # acquisition.PhotoStim
        stimulation_method = get_one_from_nested_array(photostim.stimulation_method)
    else: photostim_atlas_location, photostim_coord_location, stimulation_method = None, None, None
    
    virus = metadata.virus[0,0] if metadata.virus.size != 0 else None  
    if  virus is not None:
        atlas_location = get_one_from_nested_array(virus.atlas_location)               # not sure (location)
        depth = virus.depth                                         # action.VirusInjection
        injection_date = get_one_from_nested_array(virus.injection_date)               # action.VirusInjection
        injection_pattern = virus.injection_pattern # empty         # action.VirusInjection
        titer = get_one_from_nested_array(virus.titer)                                 # reference.Virus
        virus_coord_location = get_one_from_nested_array(virus.virus_coord_location)  # not sure (location)
        virus_lot_number = virus.virus_lot_number # empty           # reference.Virus
        virus_name = get_one_from_nested_array(virus.virus_name)                       # reference.Virus
        virus_source = get_one_from_nested_array(virus.virus_source)                   # reference.VirusSource
        volume = virus.volume                                       # action.VirusInjection
    else: 
        atlas_location, depth, injection_date, injection_pattern, titer, \
        virus_coord_location, virus_lot_number, virus_name, virus_source, \
        volume = None, None, None, None, None, None, None, None, None, None
    
    # ------------ Species ------------
    subject.Species.insert1([species], skip_duplicates=True)
    
    # ------------ Strain ------------
    subject.Strain.insert1(['N/A'], skip_duplicates=True)
    
    # ------------ Allele ------------
    subject.Allele().insert1([source_strain], skip_duplicates=True)
    
    # ------------ Animal Source ------------
    if source_identifier is None : source_identifier = 'N/A'
    reference.AnimalSource.insert1([source_identifier], skip_duplicates=True)
    
    # ------------ Subject ------------
    sex = 'U' if sex is None else sex
            
    strain = 'N/A' # for this dataset, let's just say we dont know strain
    
    if dob is not None:
        subject.Subject.insert1(
                {'subject_id':animal_ID,
                 'species':species,
                 'strain': strain,
                 'animal_source':source_identifier,
                 'sex': sex,
                 'date_of_birth': dob}, 
                 skip_duplicates=True)
    else: 
        subject.Subject.insert1(
                {'subject_id':animal_ID,
                 'species':species,
                 'strain': strain,
                 'animal_source':source_identifier,
                 'sex': sex},
                 skip_duplicates=True)
    
    # ------------ Cell ------------
    
    # handling some inconsistency in cell naming convention in the metadata
    if len(cell) < 7 : cell = cell + '_AAAA'
    
    subject.Cell.insert1(
            {'subject_id':animal_ID,
             'cell_id':cell, 
             'cell_type':cell_type},
             skip_duplicates=True)
    
    # ------------ RecordingLocation ------------
    splittedstr = re.split(', |Layer | ',recording_coord_location)
    layer = splittedstr[1].lower() 
    subregion = splittedstr[2].lower()  
    region = splittedstr[3].lower()  
    depth = re.findall(r'\d+',recording_coord_depth)[0] # need to implement a way to check if the unit is in um, if not then convert
    
    # Check brain location first
    if not (reference.BrainLocation() & {'brain_location': region , 'cortical_layer' : layer , 'brain_subregion' : subregion}).fetch() : 
        reference.BrainLocation.insert1(
                {'brain_location':region,
                 'cortical_layer':layer,
                 'brain_subregion':subregion})        
    
    acquisition.RecordingLocation.insert1(
            {'brain_location':region,
             'cortical_layer':layer,
             'brain_subregion':subregion,
             'recording_depth':depth},
            skip_duplicates=True)
    
    # ------------ Experimenter ------------
    reference.Experimenter.insert1([experimenters],skip_duplicates=True)
    
    # ------------ Session ------------        
    if date_of_experiment is not None: 
        with acquisition.Session.connection.transaction:
            acquisition.Session.insert1(            
                        {'subject_id':animal_ID,
                         'cell_id':cell,
                         'session_time': date_of_experiment,
                         'brain_location':region,
                         'cortical_layer':layer,
                         'brain_subregion':subregion,
                         'recording_depth':depth,
                         }, 
                         skip_duplicates=True)
            acquisition.Session.Experimenter.insert1(            
                        {'subject_id':animal_ID,
                         'cell_id':cell,
                         'session_time': date_of_experiment,
                         'experimenter': experimenters
                         }, 
                         skip_duplicates=True)
            # there is still the ExperimentType part table here...
            print(f'\tSession created - Subject: {animal_ID} - Cell: {cell} - Date: {date_of_experiment}')
    
    
    ## Need to perform ingestion for Virus, VirusInjection and PhotoStim ##
    


# ===================== Part 2: Acquisition data (still in experimental stage) ========

behavior.TrialSet.populate()



#=========================== R&D ==========================

matdata = sio.loadmat('data_structure_Cell01_ANM244028_141021_JY1243_AAAA.mat', struct_as_record=False)

c = matdata['c'][0,0]
timeSeries = c.timeSeriesArrayHash[0,0]
behav = timeSeries.value[0,0][0,0]
ephys = timeSeries.value[0,1][0,0]

trialProperties = c.trialPropertiesHash[0,0]




































