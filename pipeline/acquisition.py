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

from . import reference, subject, utilities, stimulation

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
        sess_data_file = utilities.find_session_matched_nwbfile(sess_data_dir, animal_id, date_of_experiment)
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
        sess_data_file = utilities.find_session_matched_nwbfile(sess_data_dir, animal_id, date_of_experiment)
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
class Extracellular(dj.Manual):
    definition = """ # Information relating to the extracelluar recording (e.g. location, probe)
    -> Session
    -> reference.ActionLocation
    -> reference.Probe
    """    
    

@schema
class ExtracellularAcquisition(dj.Imported):
    definition = """ # Raw extracellular recording, channel x time (e.g. LFP)
    -> Extracellular
    """    
    
    class Voltage(dj.Part):
        definition = """
        -> master
        ---
        voltage: longblob   
        voltage_time_stamps: longblob
        """
        

@schema
class Spike(dj.Imported):
    definition = """ 
    -> Extracellular
    unit_id : smallint
    ---
    spike_times: longblob
    spike_type: varchar(32) # e.g. wide width, narrow width spiking
    unit_depth_x: float
    unit_depth_y: float
    unit_depth_z: float
    """

    class SpikeWaveForm(dj.Part):
        definition = """ 
        -> master
        -> reference.Probe.Channel
        ---
        spike_waveform: longblob
        spike_time_stamps: longblob
        """   
        

@schema
class TrialSet(dj.Manual):
    definition = """
    -> Session
    ---
    trial_counts: int # total number of trials
    """
    
    class Trial(dj.Part):
        definition = """
        -> master
        trial_id: varchar(36)           # id of this trial in this trial set
        ---
        cue_start_time = null: float           # cue onset of this trial (auditory cue), with respect to this session's start time
        cue_end_time = null: float             # cue end of this trial, with respect to this session's start time
        pole_in_tim = null: float             # the start of sample period for each trial (e.g. the onset of pole motion towards the exploration area), relative to session start time
        pole_out_time = null: float            # the end of the sample period (e.g. the onset of pole motion away from the exploration area), relative to session start time
        start_time = null: float               # start time of this trial, with respect to starting point of this session
        stop_time = null: float                # end time of this trial, with respect to starting point of this session
        """
        
    class TrialInfo(dj.Part):
        definition = """ # General information about this trial 
        -> master.Trial
        ---
        -> reference.TrialType
        -> reference.TrialResponse
        trial_stim_present: bool  # is this a stim or no-stim trial
        trial_is_good: bool  # is this a good or bad trial
        """
 
    class TrialStimInfo(dj.Part):
        definition = """ # information related to the stimulation settings for this trial
        -> master.Trial
        ---
        photo_stim_type: enum('stimulation','inhibition','N/A')
        photo_stim_period: enum('sample','delay','response','N/A')
        photo_stim_power: float  # stimulation power in mW
        photo_loc_galvo_x: float  # photostim coordinates field (mm)
        photo_loc_galvo_y: float  # photostim coordinates field (mm)
        photo_loc_galvo_z: float  # photostim coordinates field (mm)
        """      

    
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
    
    