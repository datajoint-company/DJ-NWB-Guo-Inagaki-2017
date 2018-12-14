'''
Schema of aquisition information.
'''
import re
import os
from datetime import datetime

import numpy as np
import scipy.io as sio
import datajoint as dj
import h5py as h5

from . import reference, subject, behavior, helper_functions

schema = dj.schema(dj.config.get('database.prefix', '') + 'gi2017_acquisition')


@schema
class ExperimentType(dj.Lookup):
    definition = """
    experiment_type: varchar(64)
    """
    contents = [
        ['behavior'], ['extracelluar'], ['photostim']
    ]


@schema 
class ActionLocation(dj.Manual): 
    definition = """ # Information relating the location of any experimental task (e.g. recording (extra/intra cellular), stimulation (photo or current) )
    -> reference.BrainLocation
    -> reference.CoordinateReference
    coordinate_ap: float    # in mm, anterior positive, posterior negative 
    coordinate_ml: float    # in mm, always postive, number larger when more lateral
    coordinate_dv: float    # in mm, always postive, number larger when more ventral (deeper)
    """
    
    
#@schema
#class PhotoStim(dj.Manual):
#    definition = """
#    photo_stim_id: int
#    ---
#    photo_stim_wavelength: int
#    photo_stim_method: enum('fiber', 'laser')
#    -> reference.BrainLocation.proj(photo_stim_location="brain_location")
#    -> reference.Hemisphere.proj(photo_stim_hemisphere="hemisphere")
#    -> reference.CoordinateReference.proj(photo_stim_coordinate_ref="coordinate_ref")
#    photo_stim_coordinate_ap: float    # in mm, anterior positive, posterior negative 
#    photo_stim_coordinate_ml: float    # in mm, always postive, number larger when more lateral
#    photo_stim_coordinate_dv: float    # in mm, always postive, number larger when more ventral (deeper)
#    """


@schema
class Session(dj.Manual):
    definition = """
    -> subject.Subject
    session_time: datetime    # session time
    ---
    session_directory = "": varchar(256)
    session_note = "" : varchar(256) 
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
class IntracellularInfo(dj.Manual):
    definition = """ # Table containing information relating to the intracelluar recording (e.g. cell info)
    -> Session
    cell_id: varchar(64)
    ---
    cell_type: enum('excitatory','inhibitory','N/A')
    -> ActionLocation
    -> reference.Device
    """    
    
    
@schema
class ExtracellularInfo(dj.Manual):
    definition = """ # Table containing information relating to the extracelluar recording (e.g. location)
    -> Session
    ec_id: varchar(64)
    ---
    -> ActionLocation
    -> reference.Device
    """    
    
    
@schema
class StimulationInfo(dj.Manual):
    definition = """ # Table containing information relating to the stimulatiom (stimulation type (optical or electrical), location, device)
    -> Session
    stim_id: varchar(64)
    ---
    stim_type: enum('optical','electrical')
    -> ActionLocation
    -> reference.Device
    """    


@schema
class TrialSet(dj.Imported):
    definition = """
    -> Session
    ---
    n_trials: int # total number of trials
    """
    
    class Trial(dj.Part):
        definition = """
        -> master
        trial_id: varchar(32)
        ---
        cue_start_time: float           # cue onset of this trial, with respect to this trial's start time
        cue_end_time: float             # cue end of this trial, with respect to this trial's start time
        pole_in_time: float             # the start of sample period for each trial (e.g. the onset of pole motion towards the exploration area), relative to trial start time
        pole_out_time: float            # the end of the sample period (e.g. the onset of pole motion away from the exploration area), relative to trial start time
        start_time: float               # start time of this trial, with respect to starting point of this session
        stop_time: float                # end time of this trial, with respect to starting point of this session
        """
        
    class TrialLabels(dj.Part):
        definition = """
        -> master.Trial
        trial_type_label: varchar(32)  # label for this trial (e.g. 'No stim', 'Good', 'Bad', 'Lick Left')
        """

    def make(self,key):
        
        ############## Dataset #################
        sess_data_dir = os.path.join('..','data','whole_cell_nwb2.0')
        sess_data_files = os.listdir(sess_data_dir)
                
        # Get the Session definition from the keys of this session
        animal_id = key['subject_id']
        date_of_experiment = key['session_time']
                        
        # Search the filenames to find a match for "this" session (based on key)
        sess_data_file = None
        nwb = None
        for s in sess_data_files:
            try:
                temp_nwb = h5.File(os.path.join(sess_data_dir,s), 'r')
            except:
                print(f'!!! error load file: {s} when populating trials')   
                continue
            # read subject_id out of this file
            subject_id = temp_nwb['general']['subject']['subject_id'].value.decode('UTF-8')
            # -- session_time 
            session_start_time = temp_nwb['session_start_time'].value
            session_start_time = helper_functions.parse_prefix(session_start_time)
            # compare key with extracted info from this file
            if (animal_id == subject_id) and (date_of_experiment == session_start_time):
                # if true, meaning the current "nwb" variable is a match with this session
                sess_data_file = s
                nwb = temp_nwb # just a change of variable, no need for deep copy
                break
                    
        # If session not found from dataset, break
        if nwb is None:
            print(f'Session not found! - Subject: {animal_id} - Date: {date_of_experiment}')
            return
        else: print(f'Found datafile: {sess_data_file}')
        
        #  ============= Now read the data and start ingesting =============
        
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
                
        # this is to perserve the original key for use in the part table later
        trial_partkey = key.copy() 
        triallabel_partkey = key.copy() 
        # form new key-values pair and insert key
        key['n_trials'] = len(trial_names)
        self.insert1(key)
        print(f'Inserted trial set for session: Subject: {animal_id} - Date: {date_of_experiment}')
        print('Inserting trial ID: ', end="")
        
        # loop through each trial and insert
        for idx, trialId in enumerate(trial_names):
            trial_partkey['trial_id'] = trialId
            triallabel_partkey['trial_id'] = trialId
            # -- start/stop time
            trial_partkey['start_time'] = start_times[idx]
            trial_partkey['stop_time'] = stop_times[idx]
            # -- events timing
            trial_partkey['cue_start_time'] = cue_start_times[idx]
            trial_partkey['cue_end_time'] = cue_end_times[idx]
            trial_partkey['pole_in_time'] = pole_in_times[idx]
            trial_partkey['pole_out_time'] = pole_out_times[idx]            
            # form new key-values pair for trial_partkey and insert
            self.Trial.insert1(trial_partkey)
            print(f'{trialId} ',end="")

            # ======== Now add 'trial type labels' to the TrialLabels part table ====
            trial_labels = []  # 2brmv 
            # - good/bad trial (nwb['analysis']['good_trials'])
            if good_trials.flatten()[idx] == 1: 
                triallabel_partkey['trial_type_label'] = 'good trial'
                self.TrialLabels.insert1(triallabel_partkey)
                trial_labels.append('good trial') # 2brmv 
            elif good_trials.flatten()[idx] == 0: 
                triallabel_partkey['trial_type_label'] = 'bad trial'
                self.TrialLabels.insert1(triallabel_partkey)
                trial_labels.append('bad trial') # 2brmv 
            # -- trial description (nwb['epochs'][trial]['description'])
            for d in re.split(', ',trial_descs[idx]):
                triallabel_partkey['trial_type_label'] = d
                self.TrialLabels.insert1(triallabel_partkey)
                trial_labels.append(d) # 2brmv 
            # -- trial_type_string (nwb['analysis']['trial_type_string'])
            for i in  np.where(trial_type_mat[idx,:] == 1):
                triallabel_partkey['trial_type_label'] = trial_type_string.flatten()[i].item(0).decode('UTF-8')
                self.TrialLabels.insert1(triallabel_partkey)
                trial_labels.append(trial_type_string.flatten()[i].item(0).decode('UTF-8')) # 2brmv 
        print('')
    
    
@schema
class BehaviorAcquisition(dj.Imported):
    definition = """
    -> Session
    -> reference.BehavioralType
    ---
    behavior_time_stamp: longblob
    behavior_timeseries: longblob        
    """    
      
    
@schema
class ExtracellularAcquisition(dj.Imported):
    definition = """
    -> ExtracellularInfo
    -> reference.ExtracellularType
    ---
    ec_time_stamp: longblob
    ec_timeseries: longblob        
    """      
    
    
@schema
class IntracellularAcquisition(dj.Imported):
    definition = """
    -> IntracellularInfo
    -> reference.IntracellularType
    ---
    ic_time_stamp: longblob
    ic_timeseries: longblob        
    """     
       
     
@schema
class ExperimentalStimulus(dj.Imported):
    definition = """
    -> StimulationInfo
    ---
    stim_time_stamp: longblob
    stim_timeseries: longblob        
    """      
            
    
@schema
class TrialExtracellular(dj.Computed):
    definition = """
    -> ExtracellularAcquisition
    -> TrialSet.Trial
    ---
    segmented_extracellular: longblob
    """
    
    
@schema
class TrialIntracellular(dj.Computed):
    definition = """
    -> IntracellularAcquisition
    -> TrialSet.Trial
    ---
    segmented_intracellular: longblob
    """
    
    
@schema   
class TrialBehavior(dj.Computed):
    definition = """
    -> BehaviorAcquisition
    -> TrialSet.Trial
    ---
    segmented_behavior: longblob
    """
    
    
@schema
class TrialStimulus(dj.Computed):
    definition = """
    -> ExperimentalStimulus
    -> TrialSet.Trial
    ---
    segmented_stim: longblob
    """
    
    
    
    
    
    
    
    
    
    
    
        
        
        
    
    
    
    
    
    
    
    
    
    
    
    
    


























