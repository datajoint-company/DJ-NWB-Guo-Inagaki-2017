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

from . import reference, subject, helper_functions, stimulation

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
class BehaviorAcquisition(dj.Imported):
    definition = """
    -> Session
    """    
    
    class LickTrace(dj.Part):
        definition = """
        -> master
        ---
        lick_trace_left: longblob   
        lick_trace_right: longblob
        lick_trace_time_stamps: longblob
        """       
        
    def make(self,key):
        ############## Dataset #################
        sess_data_dir = os.path.join('..','data','whole_cell_nwb2.0')
                
        # Get the Session definition from the keys of this session
        animal_id = key['subject_id']
        date_of_experiment = key['session_time']
        
        # Search the files in filenames to find a match for "this" session (based on key)
        sess_data_file = helper_functions.find_session_matched_nwbfile(sess_data_dir, animal_id, date_of_experiment)
        if sess_data_file is None: 
            return
        nwb = h5.File(os.path.join(sess_data_dir,sess_data_file), 'r')
        
        #  ============= Now read the data and start ingesting =============
        self.insert1(key)
        print('Insert extracellular data for: subject: {0} - date: {1}'.format(key['subject_id'],key['session_time']))
        # -- MembranePotential
        key['lick_trace_left'] = np.array(nwb['acquisition']['timeseries']['lick_trace_L']['data'])
        key['lick_trace_right'] = np.array(nwb['acquisition']['timeseries']['lick_trace_R']['data'])
        key['lick_trace_time_stamps'] = np.array(nwb['acquisition']['timeseries']['lick_trace_L']['timestamps'])
        self.LickTrace.insert1(key, ignore_extra_fields=True)


@schema
class PhotoStimulation(dj.Manual):
    definition = """ # Table containing information relating to the stimulatiom (stimulation type (optical or electrical), location, device)
    -> Session
    photostim_datetime: varchar(36) # the time of performing this stimulation with respect to start time of the session, in the scenario of multiple stimulations per session
    ---
    -> stimulation.PhotoStimulationInfo
    photostim_timeseries: longblob
    photostim_time_stamps: longblob
    """    


@schema
class Cell(dj.Manual):
    definition = """ # Information relating to the Cell and the intracellular recording of this cell (e.g. location, recording device)
    -> Session
    cell_id: varchar(36) # a string identifying the cell in which this intracellular recording is concerning
    ---
    cell_type: enum('excitatory','inhibitory','N/A')
    -> reference.ActionLocation
    -> reference.WholeCellDevice
    """    
  
    
@schema
class IntracellularAcquisition(dj.Imported):
    definition = """ # data pertain to intracellular recording
    -> Cell
    """     
    
    class MembranePotential(dj.Part):
        definition = """
        -> master
        ---
        membrane_potential: longblob    # Membrane potential recording at this cell
        membrane_potential_wo_spike: longblob # membrane potential without spike data, derived from membrane potential recording    
        membrane_potential_time_stamps: longblob # timestamps of membrane potential recording
        """
        
    class CurrentInjection(dj.Part):
        definition = """
        -> master
        ---
        current_injection: longblob
        current_injection_time_stamps: longblob        
        """
        
    def make(self,key):
        ############## Dataset #################
        sess_data_dir = os.path.join('..','data','whole_cell_nwb2.0')
                
        # Get the Session definition from the keys of this session
        animal_id = key['subject_id']
        date_of_experiment = key['session_time']
        
        # Search the files in filenames to find a match for "this" session (based on key)
        sess_data_file = helper_functions.find_session_matched_nwbfile(sess_data_dir, animal_id, date_of_experiment)
        if sess_data_file is None: 
            return
        nwb = h5.File(os.path.join(sess_data_dir,sess_data_file), 'r')
        
        #  ============= Now read the data and start ingesting =============
        self.insert1(key)
        print('Insert behavioral data for: subject: {0} - date: {1} - cell: {2}'.format(key['subject_id'],key['session_time'],key['cell_id']))
        # -- MembranePotential
        key['membrane_potential'] = np.array(nwb['acquisition']['timeseries']['membrane_potential']['data'])
        key['membrane_potential_wo_spike'] = np.array(nwb['analysis']['Vm_wo_spikes']['membrane_potential_wo_spike']['data'])
        key['membrane_potential_time_stamps'] = np.array(nwb['acquisition']['timeseries']['membrane_potential']['timestamps'])
        self.MembranePotential.insert1(key, ignore_extra_fields=True)
        # -- CurrentInjection
        key['current_injection'] = np.array(nwb['acquisition']['timeseries']['current_injection']['data'])
        key['current_injection_time_stamps'] = np.array(nwb['acquisition']['timeseries']['current_injection']['timestamps']),
        self.CurrentInjection.insert1(key, ignore_extra_fields=True)

    
@schema
class Probe(dj.Manual):
    definition = """ # Table containing information relating to the extracelluar recording (e.g. location)
    -> Session
    probe_id: varchar(36) # a string uniquely identify the probe for extracellular recording, it is likely that multiple probes recording multiple extracellular traces
    ---
    -> reference.ActionLocation
    """    
    

@schema
class ExtracellularAcquisition(dj.Imported):
    definition = """
    -> Probe
    """    
    
    class Voltage(dj.Part):
        definition = """
        -> master
        ---
        voltage: longblob   
        voltage_time_stamps: longblob
        """
        
    class Spike(dj.Part):
        definition = """
        -> master
        ---
        spike: longblob   
        spike_time_stamps: longblob
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
        trial_id: varchar(36)           # unique id of this trial in this trial set
        ---
        cue_start_time: float           # cue onset of this trial, with respect to this trial's start time
        cue_end_time: float             # cue end of this trial, with respect to this trial's start time
        pole_in_time: float             # the start of sample period for each trial (e.g. the onset of pole motion towards the exploration area), relative to trial start time
        pole_out_time: float            # the end of the sample period (e.g. the onset of pole motion away from the exploration area), relative to trial start time
        start_time: float               # start time of this trial, with respect to starting point of this session
        stop_time: float                # end time of this trial, with respect to starting point of this session
        """
        
    class TrialInfo(dj.Part):
        definition = """
        -> master.Trial
        ---
        -> reference.TrialType
        -> reference.TrialResponse
        trial_stim_present: bool # is this trial a Stimulation or No stimulation trial
        trial_is_good: bool # is this a good or bad trial
        """

    def make(self,key):
        ############## Dataset #################
        sess_data_dir = os.path.join('..','data','whole_cell_nwb2.0')
                
        # Get the Session definition from the keys of this session
        animal_id = key['subject_id']
        date_of_experiment = key['session_time']
        
        # Search the files in filenames to find a match for "this" session (based on key)
        sess_data_file = helper_functions.find_session_matched_nwbfile(sess_data_dir, animal_id, date_of_experiment)
        if sess_data_file is None: 
            return
        nwb = h5.File(os.path.join(sess_data_dir,sess_data_file), 'r')
                
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
        nwb.close()
        
        # form new key-values pair and insert key
        key['n_trials'] = len(trial_names)
        self.insert1(key)
        print(f'Inserted trial set for session: Subject: {animal_id} - Date: {date_of_experiment}')
        print('Inserting trial ID: ', end="")
        
        # loop through each trial and insert
        for idx, trialId in enumerate(trial_names):
            key['trial_id'] = trialId
            # -- start/stop time
            key['start_time'] = start_times[idx]
            key['stop_time'] = stop_times[idx]
            # -- events timing
            key['cue_start_time'] = cue_start_times[idx]
            key['cue_end_time'] = cue_end_times[idx]
            key['pole_in_time'] = pole_in_times[idx]
            key['pole_out_time'] = pole_out_times[idx]            
            # form new key-values pair for trial_partkey and insert
            self.Trial.insert1(key, ignore_extra_fields=True)
            print(f'{trialId} ',end="")
            # ======== Now add trial descriptors to the TrialInfo part table ====
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
            self.TrialInfo.insert1(key, ignore_extra_fields=True)
        print('')
       
    
@schema
class TrialExtracellular(dj.Computed):
    definition = """
    -> ExtracellularAcquisition
    -> TrialSet.Trial
    ---
    segmented_extracellular: longblob
    """
    
    class Voltage(dj.Part):
        definition = """
        -> master
        ---
        segmented_voltage: longblob   
        """
    
    class Spike(dj.Part):
        definition = """
        -> master
        ---
        segmented_spike: longblob   
        """      
    
    
@schema
class TrialIntracellular(dj.Computed):
    definition = """
    -> IntracellularAcquisition
    -> TrialSet.Trial
    """
    
    class MembranePotential(dj.Part):
        definition = """
        -> master
        ---
        segmented_mp: longblob   
        segmented_mp_wo_spike: longblob
        """
    
    class CurrentInjection(dj.Part):
        definition = """
        -> master
        ---
        segmented_current_injection: longblob
        """
    
    
@schema     
class TrialBehavior(dj.Computed):
    definition = """
    -> BehaviorAcquisition
    -> TrialSet.Trial
    ---
    segmented_behavior: longblob
    """
    
    class LickTrace(dj.Part):
        definition = """
        -> master
        ---
        segmented_lt_left: longblob   
        segmented_lt_right: longblob
        """   
    
    
@schema
class TrialPhotoStimulus(dj.Computed):
    definition = """
    -> PhotoStimulation
    -> TrialSet.Trial
    ---
    segmented_photostim: longblob
    """
    
    