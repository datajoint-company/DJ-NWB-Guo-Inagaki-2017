'''
Schema of aquisition information.
'''
import re
import os
from datetime import datetime
import numpy as np
import scipy.io as sio
import datajoint as dj
from .helper_functions import get_one_from_nested_array, get_list_from_nested_array, datetimeformat_ydm, datetimeformat_ymd, time_unit_convert_factor

import datajoint as dj
from . import reference, subject

schema = dj.schema('ttngu207_acquisition',locals())

@schema
class ExperimentType(dj.Lookup):
    definition = """
    experiment_type_name: varchar(64)
    """
    contents = [
        ['behavior'], ['extracelluar'], ['photostim']
    ]

@schema 
class RecordingLocation(dj.Manual): 
    definition = """ 
    -> reference.BrainLocation
    recording_depth: float # depth in um    
    """

@schema
class PhotoStim(dj.Manual):
    definition = """
    photo_stim_id: int
    ---
    photo_stim_wavelength: int
    photo_stim_method: enum('fiber', 'laser')
    -> reference.BrainLocation.proj(photo_stim_location="brain_location")
    -> reference.Hemisphere.proj(photo_stim_hemisphere="hemisphere")
    -> reference.CoordinateReference.proj(photo_stim_coordinate_ref="coordinate_ref")
    photo_stim_coordinate_ap: float    # in mm, anterior positive, posterior negative 
    photo_stim_coordinate_ml: float    # in mm, always postive, number larger when more lateral
    photo_stim_coordinate_dv: float    # in mm, always postive, number larger when more ventral (deeper)
    """

@schema
class Session(dj.Manual):
    definition = """
    -> subject.Cell
    session_time: datetime    # session time
    ---
    -> RecordingLocation
    session_directory = "": varchar(256)
    session_note = "" : varchar(256) # 
    """

    class Experimenter(dj.Part):
        definition = """
        -> master
        -> reference.Experimenter
        """

    class ExperimentType(dj.Part):
        definition = """
        -> master
        -> ExperimentType
        """
    
@schema
class BehaviorAcquisition(dj.Imported):
    definition = """
    -> Session
    -> reference.BehavioralType
    ---
    behavior_sampling_rate: int
    behavior_time_stamp: longblob
    behavior_timeseries: longblob        
    """    
    
    def _make_tuples(self,key):
        
        data_dir = os.path.abspath('..//NWB_Janelia_datasets//crcns_ssc5_data_HiresGutnisky2015//')
        sess_data_dir = os.path.join(data_dir,'datafiles')
        
        sess_data_files = os.listdir(sess_data_dir)
                
        # Get the Session definition from keys
        animal_id = key['subject_id']
        cell = key['cell_id']
        date_of_experiment = key['session_time']
                
        # Convert datetime to string format 
        date_of_experiment = datetime.strftime(date_of_experiment,datetimeformat_ymd) # expected datetime format: yymmdd
        
        # Search the filenames to find a match for "this" session (based on key)
        sess_data_file = None
        for s in sess_data_files:
            m1 = re.search(animal_id, s) 
            m2 = re.search(cell, s) 
            m3 = re.search(date_of_experiment, s) 
            if (m1 is not None) & (m2 is not None) & (m3 is not None):
                sess_data_file = s
                break
        
        # If session not found from dataset, break
        if sess_data_file is None:
            print(f'Session not found! - Subject: {animal_id} - Cell: {cell} - Date: {date_of_experiment}')
            return
        else: print(f'Found datafile: {sess_data_file}')
        
        # Now read the data and start ingesting
        matfile = sio.loadmat(os.path.join(sess_data_dir,sess_data_file), struct_as_record=False)
        sessdata = matfile['c'][0,0]
        
        timeSeries = sessdata.timeSeriesArrayHash[0,0]
        behav = timeSeries.value[0,0][0,0]
        
        # Make a dictionary of behavioral type and behavioral type id
        type_ids = get_list_from_nested_array(behav.id)
        type_names = get_list_from_nested_array(behav.idStr)
        behav_type_dict = {}
        for idx, val in enumerate(type_names):
            behav_type_dict[val] = type_ids[idx]
            
        # find behavioral type from 'key' and extract corresponding data
        behav_type = key['behavior_acquisition_type']
        behavior_timeseries = behav.valueMatrix[behav_type_dict[behav_type] - 1, :] # (-1 is to take into account that MATLAB index starts at 1)

        # Make a dictionary of time unit and time unit id  
        time_unit_ids = get_list_from_nested_array(sessdata.timeUnitIds)
        time_unit_names = get_list_from_nested_array(sessdata.timeUnitNames)
        time_unit_dict = {}
        for idx, val in enumerate(time_unit_ids):
            time_unit_dict[val] = time_unit_names[idx]
            
        # Extract time unit from data    
        time_unit = time_unit_dict[get_one_from_nested_array(behav.timeUnit)]
        
        # Extract time stamp from data and convert to 'second'
        behavior_time_stamp = np.array(get_list_from_nested_array(behav.time)) * time_unit_convert_factor[time_unit]
        behavior_sampling_rate = behavior_time_stamp.size / (behavior_time_stamp[-1] - behavior_time_stamp[0])
       
        # form new key-values pair and insert key
        key['behavior_sampling_rate'] = behavior_sampling_rate
        key['behavior_time_stamp'] = behavior_time_stamp
        key['behavior_timeseries'] = behavior_timeseries
        self.insert1(key)
        print(f'Inserted acquired behavioral data for session: Subject: {animal_id} - Cell: {cell} - Date: {date_of_experiment}')
    
@schema
class EphysAcquisition(dj.Imported):
    definition = """
    -> Session
    -> reference.EphysType
    ---
    ephys_sampling_rate: int
    ephys_time_stamp: longblob
    ephys_timeseries: longblob        
    """      
        
    def _make_tuples(self,key):
        
        data_dir = os.path.abspath('..//NWB_Janelia_datasets//crcns_ssc5_data_HiresGutnisky2015//')
        sess_data_dir = os.path.join(data_dir,'datafiles')
        
        sess_data_files = os.listdir(sess_data_dir)
                
        # Get the Session definition from keys
        animal_id = key['subject_id']
        cell = key['cell_id']
        date_of_experiment = key['session_time']
                
        # Convert datetime to string format 
        date_of_experiment = datetime.strftime(date_of_experiment,datetimeformat_ymd) # expected datetime format: yymmdd
        
        # Search the filenames to find a match for "this" session (based on key)
        sess_data_file = None
        for s in sess_data_files:
            m1 = re.search(animal_id, s) 
            m2 = re.search(cell, s) 
            m3 = re.search(date_of_experiment, s) 
            if (m1 is not None) & (m2 is not None) & (m3 is not None):
                sess_data_file = s
                break
        
        # If session not found from dataset, break
        if sess_data_file is None:
            print(f'Session not found! - Subject: {animal_id} - Cell: {cell} - Date: {date_of_experiment}')
            return
        else: print(f'Found datafile: {sess_data_file}')
        
        # Now read the data and start ingesting
        matfile = sio.loadmat(os.path.join(sess_data_dir,sess_data_file), struct_as_record=False)
        sessdata = matfile['c'][0,0]
        
        timeSeries = sessdata.timeSeriesArrayHash[0,0]
        ephys = timeSeries.value[0,1][0,0]
        
        # Make a dictionary of behavioral type and behavioral type id
        type_ids = get_list_from_nested_array(ephys.id)
        type_names = get_list_from_nested_array(ephys.idStr)
        ephys_type_dict = {}
        for idx, val in enumerate(type_names):
            ephys_type_dict[val] = type_ids[idx]
            
        # find behavioral type from 'key' and extract corresponding data
        ephys_type = key['ephys_acquisition_type']
        ephys_timeseries = ephys.valueMatrix[ephys_type_dict[ephys_type] - 1, :] # (-1 is to take into account that MATLAB index starts at 1)

        # Make a dictionary of time unit and time unit id  
        time_unit_ids = get_list_from_nested_array(sessdata.timeUnitIds)
        time_unit_names = get_list_from_nested_array(sessdata.timeUnitNames)
        time_unit_dict = {}
        for idx, val in enumerate(time_unit_ids):
            time_unit_dict[val] = time_unit_names[idx]
            
        # Extract time unit from data    
        time_unit = time_unit_dict[get_one_from_nested_array(ephys.timeUnit)]
        
        # Extract time stamp from data and convert to 'second'
        ephys_time_stamp = np.array(get_list_from_nested_array(ephys.time)) * time_unit_convert_factor[time_unit]
        ephys_sampling_rate = ephys_time_stamp.size / (ephys_time_stamp[-1] - ephys_time_stamp[0])
       
        # form new key-values pair and insert key
        key['ephys_sampling_rate'] = ephys_sampling_rate
        key['ephys_time_stamp'] = ephys_time_stamp
        key['ephys_timeseries'] = ephys_timeseries
        self.insert1(key)
        print(f'Inserted acquired ephys data for session: Subject: {animal_id} - Cell: {cell} - Date: {date_of_experiment}')
    
    
    
    
    
    
    
    
    
    
        
#@schema
#class TrialAcquisition(dj.Computed):
#    definition = """
#    -> Acquisition
#    -> behavior.TrialSet.Trial
#    ---
#    
#    """
#    class TrialBehavior(dj.Part):
#        definition = """
#
#        """
    
    
    
    
    
    
    
    
    
    
    
    
        
        
        
    
    
    
    
    
    
    
    
    
    
    
    
    


























