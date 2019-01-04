# -*- coding: utf-8 -*-
'''
Schema of analysis data.
'''
import re
import os
from datetime import datetime

import numpy as np
import scipy.io as sio
import datajoint as dj
import h5py as h5

from . import reference, utilities, acquisition

schema = dj.schema(dj.config.get('database.prefix', '') + 'gi2017_analysis')


@schema
class TrialSegmentationSetting(dj.Lookup):
    definition = """ 
    event: varchar(16)
    pre_stim_duration: float  # (in second) pre-stimulus duration
    post_stim_duration: float  # (in second) post-stimulus duration
    """
    contents = [['pole_out_time', 1.5, 3]]
    
@schema
class RealignedEvent(dj.Manual):
    definition = """
    trial_start: decimal(10,6)  # (in second) start time of this trial, with respect to the onset of event of choice (at t = 0)
    trial_stop: decimal(10,6)  # (in second) end time of this trial, with respect to the onset of event of choice (at t = 0) 
    cue_start: decimal(10,6)  # (in second) cue onset of this trial, with respect to the onset of event of choice (at t = 0) 
    cue_end: decimal(10,6)  # (in second) cue end of this trial, with respect to the onset of event of choice (at t = 0) 
    pole_in: decimal(10,6)  # (in second) pole in of this trial, with respect to the onset of event of choice (at t = 0) 
    pole_out: decimal(10,6)  # (in second) pole out of this trial, with respect to the onset of event of choice (at t = 0) 
    """


@schema
class TrialSegmentedExtracellular(dj.Computed):
    definition = """
    -> acquisition.ExtracellularAcquisition
    -> acquisition.TrialSet.Trial
    -> TrialSegmentationSetting
    ---
    -> RealignedEvent
    """
    
    class Voltage(dj.Part):
        definition = """
        -> master
        ---
        segmented_voltage: longblob   
        """
    
    
@schema
class TrialSegmentedIntracellular(dj.Computed):
    definition = """
    -> acquisition.IntracellularAcquisition
    -> acquisition.TrialSet.Trial
    -> TrialSegmentationSetting
    ---
    -> RealignedEvent
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
    
    def make(self,key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (TrialSegmentationSetting & key).fetch1('event','pre_stim_duration','post_stim_duration')
        # get raw
        fs = (acquisition.IntracellularAcquisition.MembranePotential & key).fetch1('membrane_potential_sampling_rate')
        first_time_point = (acquisition.IntracellularAcquisition.MembranePotential & key).fetch1('membrane_potential_start_time')
        Vm_wo_spike = (acquisition.IntracellularAcquisition.MembranePotential & key).fetch1('membrane_potential_wo_spike')
        Vm_w_spike = (acquisition.IntracellularAcquisition.MembranePotential & key).fetch1('membrane_potential')
        # segmentation
        segmented_Vm_wo_spike, *aligned_events = perform_trial_segmentation(key, event_name, pre_stim_dur, post_stim_dur, Vm_wo_spike, fs, first_time_point)
        segmented_Vm_w_spike, *_ = perform_trial_segmentation(key, event_name, pre_stim_dur, post_stim_dur, Vm_w_spike, fs, first_time_point)
        
        # insert aligned events
        aligned_events = np.round(aligned_events,6)  # ensure float with atmost 6 decimal places
        events_dict = dict(zip(['trial_start','trial_stop','cue_start','cue_end','pole_in','pole_out'], aligned_events))
        RealignedEvent.insert1(events_dict, skip_duplicates=True)
        self.insert1({**key, **events_dict}) 
        
        # insert
        self.MembranePotential.insert1(dict(key,
                                       segmented_mp = segmented_Vm_w_spike,
                                       segmented_mp_wo_spike = segmented_Vm_wo_spike))
        print(f'Perform trial-segmentation of membrane potential for trial: {key["trial_id"]}')
        
        # -- current injection --
        fs = (acquisition.IntracellularAcquisition.CurrentInjection & key).fetch1('current_injection_sampling_rate')
        first_time_point = (acquisition.IntracellularAcquisition.CurrentInjection & key).fetch1('current_injection_start_time')
        current_injection = (acquisition.IntracellularAcquisition.CurrentInjection & key).fetch1('current_injection')
        segmented_current_injection, *_ = perform_trial_segmentation(key, event_name, pre_stim_dur, post_stim_dur, current_injection, fs, first_time_point)
        # insert
        self.CurrentInjection.insert1(dict(key, segmented_current_injection = segmented_current_injection))
        print(f'Perform trial-segmentation of current injection for trial: {key["trial_id"]}')
    
    
@schema     
class TrialSegmentedBehavior(dj.Computed):   
    definition = """
    -> acquisition.BehaviorAcquisition
    -> acquisition.TrialSet.Trial
    -> TrialSegmentationSetting
    ---
    -> RealignedEvent
    """
    
    class LickTrace(dj.Part):
        definition = """
        -> master
        ---
        segmented_lt_left: longblob   
        segmented_lt_right: longblob
        """   
        
    def make(self,key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (TrialSegmentationSetting & key).fetch1('event','pre_stim_duration','post_stim_duration')
        # get raw
        fs = (acquisition.BehaviorAcquisition.LickTrace & key).fetch1('lick_trace_sampling_rate')
        first_time_point = (acquisition.BehaviorAcquisition.LickTrace & key).fetch1('lick_trace_start_time')
        lt_left = (acquisition.BehaviorAcquisition.LickTrace & key).fetch1('lick_trace_left')
        lt_right = (acquisition.BehaviorAcquisition.LickTrace & key).fetch1('lick_trace_right')
        # segmentation
        segmented_lt_left, *aligned_events = perform_trial_segmentation(key, event_name, pre_stim_dur, post_stim_dur, lt_left, fs, first_time_point)
        segmented_lt_right, *_ = perform_trial_segmentation(key, event_name, pre_stim_dur, post_stim_dur, lt_right, fs, first_time_point)
        
        # insert aligned events
        aligned_events = np.round(aligned_events, 6)  # ensure float with atmost 6 decimal places
        events_dict = dict(zip(['trial_start','trial_stop','cue_start','cue_end','pole_in','pole_out'], aligned_events))
        RealignedEvent.insert1(events_dict, skip_duplicates=True)
        self.insert1({**key, **events_dict}) 
        
        # insert
        self.LickTrace.insert1(dict(key,
                                       segmented_lt_left = segmented_lt_left,
                                       segmented_lt_right = segmented_lt_right))
        print(f'Perform trial-segmentation of lick traces for trial: {key["trial_id"]}')
    
    
@schema
class TrialSegmentedPhotoStimulus(dj.Computed):
    definition = """
    -> acquisition.PhotoStimulation
    -> acquisition.TrialSet.Trial
    -> TrialSegmentationSetting
    ---
    -> RealignedEvent
    segmented_photostim: longblob
    """
    
    def make(self,key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (TrialSegmentationSetting & key).fetch1('event','pre_stim_duration','post_stim_duration')
        # get raw
        fs = (acquisition.PhotoStimulation & key).fetch1('photostim_sampling_rate')
        first_time_point = (acquisition.PhotoStimulation & key).fetch1('photostim_start_time')
        photostim_timeseries = (acquisition.PhotoStimulation & key).fetch1('photostim_timeseries')
        # segmentation
        segmented_photostim, *aligned_events = perform_trial_segmentation(key, event_name, pre_stim_dur, post_stim_dur, photostim_timeseries, fs, first_time_point)
        
        # insert aligned events
        aligned_events = np.round(aligned_events, 6)  # ensure float with atmost 6 decimal places
        events_dict = dict(zip(['trial_start','trial_stop','cue_start','cue_end','pole_in','pole_out'], aligned_events))
        RealignedEvent.insert1(events_dict, skip_duplicates=True)
        self.insert1( dict({**key, **events_dict}, segmented_photostim = segmented_photostim)) 

        print(f'Perform trial-segmentation of photostim for trial: {key["trial_id"]}')
    
    
@schema
class TrialSegmentedUnitSpikeTimes(dj.Computed):
    definition = """
    -> acquisition.UnitSpikeTimes
    -> acquisition.TrialSet.Trial
    -> TrialSegmentationSetting
    ---
    -> RealignedEvent
    segmented_spike_times: longblob
    """

    def make(self,key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (TrialSegmentationSetting & key).fetch1('event','pre_stim_duration','post_stim_duration')
        
        # get event time
        if event_name == 'start_time' or event_name == 'stop_time':
            event_time_point = (acquisition.TrialSet.Trial & key).fetch1(event_name)
        else:
            try:
                event_time_point = (acquisition.TrialSet.CuePoleTiming & key).fetch1(event_name)
            except Exception as e:
                print(f'Error extracting event type: {event_name}\n\tMsg: {str(e)}')
                return
        # handling the case where the event-of-interest is NaN
        if np.isnan(event_time_point) or event_time_point is None:
            print(f'Invalid event time (NaN) for unit: {key["unit_id"]} and trial: {key["trial_id"]}')
            return
            
        # check if pre/post stim dur is within start/stop time
        trial_start, trial_stop = (acquisition.TrialSet.Trial & key).fetch1('start_time','stop_time')
        if event_time_point - pre_stim_dur < trial_start:
            print('Warning: Out of bound prestimulus duration, set to 0')
            pre_stim_dur = 0
        if event_time_point + post_stim_dur > trial_stop:
            print('Warning: Out of bound poststimulus duration, set to trial end time')
            post_stim_dur = trial_stop - event_time_point
            
        # get raw & segment
        spike_times = (acquisition.UnitSpikeTimes & key).fetch1('spike_times')
        segmented_spike_times = spike_times[ (spike_times >= (event_time_point - pre_stim_dur)) &  (spike_times <= (event_time_point + post_stim_dur))]

        # recompute other event timing with respect to the time-lock event (t=0)
        cue_start, cue_end, pole_in, pole_out = (acquisition.TrialSet.CuePoleTiming & key).fetch1('cue_start_time','cue_end_time','pole_in_time','pole_out_time')
        aligned_events = [trial_start, trial_stop, cue_start, cue_end, pole_in, pole_out] - event_time_point
        
        # insert aligned events
        aligned_events = np.round(aligned_events, 6)  # ensure float with atmost 6 decimal places
        events_dict = dict(zip(['trial_start','trial_stop','cue_start','cue_end','pole_in','pole_out'], aligned_events))
        RealignedEvent.insert1(events_dict, skip_duplicates=True)
        self.insert1(dict({**key, **events_dict}, segmented_spike_times = segmented_spike_times))
        print(f'Perform trial-segmentation of spike times for unit: {key["unit_id"]} and trial: {key["trial_id"]}')


def perform_trial_segmentation(trial_key, event_name, pre_stim_dur, post_stim_dur, data, fs, first_time_point):
        # get event time
        if event_name == 'start_time' or event_name == 'stop_time':
            event_time_point = (acquisition.TrialSet.Trial & trial_key).fetch1(event_name)
        else:
            try:
                event_time_point = (acquisition.TrialSet.CuePoleTiming & trial_key).fetch1(event_name)
            except Exception as e:
                print(f'Error extracting event type: {event_name}\n\tMsg: {str(e)}')
                return
        # handling the case where the event-of-interest is NaN
        if np.isnan(event_time_point) or event_time_point is None:
            print(f'Invalid event time (NaN)')
            return
        # check if pre/post stim dur is within start/stop time
        trial_start, trial_stop = (acquisition.TrialSet.Trial & trial_key).fetch1('start_time','stop_time')
        if event_time_point - pre_stim_dur < trial_start:
            print('Warning: Out of bound prestimulus duration, set to 0')
            pre_stim_dur = 0
        if event_time_point + post_stim_dur > trial_stop:
            print('Warning: Out of bound poststimulus duration, set to trial end time')
            post_stim_dur = trial_stop - event_time_point

        event_sample_point = (event_time_point - first_time_point) * fs
        sample_points_to_extract = np.arange(event_sample_point - pre_stim_dur * fs, event_sample_point + post_stim_dur * fs + 1)
        segmented_data = data[sample_points_to_extract.astype(int)]
        
        # recompute other event timing with respect to the time-lock event (t=0)
        cue_start, cue_end, pole_in, pole_out = (acquisition.TrialSet.CuePoleTiming & trial_key).fetch1('cue_start_time','cue_end_time','pole_in_time','pole_out_time')
        
        trial_start = trial_start - event_time_point
        trial_stop = trial_stop - event_time_point
        cue_start = cue_start - event_time_point
        cue_end = cue_end - event_time_point
        pole_in = pole_in - event_time_point
        pole_out = pole_out - event_time_point      
        
        return segmented_data, trial_start, trial_stop, cue_start, cue_end, pole_in, pole_out
       
