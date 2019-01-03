import os
from datetime import datetime
import re

import h5py as h5
import numpy as np

from . import reference, acquisition


# datetime format - should probably read this from a config file and not hard coded here
datetimeformat_ymdhms = '%Y-%m-%d %H:%M:%S'
datetimeformat_ymd = '%Y-%m-%d'

def parse_prefix(line):
    cover = len(datetime.now().strftime(datetimeformat_ymdhms))
    try:
        return datetime.strptime(line[:cover], datetimeformat_ymdhms)
    except Exception as e:
        msg = f'Error:  {str(e)} \n'
        cover = len(datetime.now().strftime(datetimeformat_ymd))
        try:
            return datetime.strptime(line[:cover], datetimeformat_ymd)
        except Exception as e:
            print(f'{msg}\t{str(e)}\n\tReturn None')
            return None    


def find_session_matched_nwbfile(sess_data_dir, animal_id, date_of_experiment):
        ############## Dataset #################
        sess_data_files = os.listdir(sess_data_dir)
        which_data = re.search('extracellular|whole_cell',sess_data_dir).group()
        # Search the filenames to find a match for "this" session (based on key)
        sess_data_file = None
        for s in sess_data_files:
            try:
                temp_nwb = h5.File(os.path.join(sess_data_dir,s), 'r')
            except:
                print(f'!!! error load file: {s}')   
                continue
            # read subject_id out of this file
            subject_id = temp_nwb['general']['subject']['subject_id'].value.decode('UTF-8')
            
            # -- session_time - due to error in extracellular dataset (session_start_time error), need to hard code here...
            if which_data == 'whole_cell':  # case: whole cell
                session_start_time = temp_nwb['session_start_time'].value
                session_start_time = parse_prefix(session_start_time)
            elif which_data == 'extracellular':# case: extracellular
                identifier = temp_nwb['identifier'].value
                session_start_time = re.split(';\s?',identifier)[-1].replace('T',' ')
                session_start_time = parse_prefix(session_start_time) 
            
            # compare key with extracted info from this file
            if (animal_id == subject_id) and (date_of_experiment == session_start_time):
                # if true, meaning the current "nwb" variable is a match with this session
                sess_data_file = s
                break
            temp_nwb.close()
                    
        # If session not found from dataset, break
        if sess_data_file is None:
            print(f'Session not found! - Subject: {animal_id} - Date: {date_of_experiment}')
            return None
        else: 
            print(f'Found datafile: {sess_data_file}')
            return sess_data_file
 

def segment_trial_based(trial_key, event_name, pre_stim_dur, post_stim_dur, data, fs, first_time_point):
        # get event time
        if event_name == 'start_time' or event_name == 'stop_time':
            event_time_point = (acqusition.TrialSet.Trial & trial_key).fetch1(event_name)
        else:
            try:
                event_time_point = (acqusition.TrialSet.CuePoleTiming & trial_key).fetch1(event_name)
            except Exception as e:
                print(f'Error extracting event type: {event_name}\nMsg: {str(e)}')
                return
        # check if pre/post stim dur is within start/stop time
        trial_start, trial_stop = (acqusition.TrialSet.Trial & trial_key).fetch1('start_time','stop_time')
        if event_time_point - pre_stim_dur < trial_start:
            print('Warning: Out of bound prestimulus duration, set to 0')
            pre_stim_dur = 0
        if event_time_point + post_stim_dur > trial_stop:
            print('Warning: Out of bound poststimulus duration, set to trial end time')
            post_stim_dur = trial_stop - event_time_point

        event_sample_point = (event_time_point - first_time_point) * fs
        sample_points_to_extract = np.arange(event_sample_point - pre_stim_dur * fs, event_sample_point - post_stim_dur * fs + 1)
        segmented_data = data[sample_points_to_extract]
        
        # recompute other event timing with respect to the time-lock event (t=0)
        cue_start, cue_end, pole_in, pole_out = (acqusition.TrialSet.CuePoleTiming & trial_key).fetch1('cue_start_time','cue_end_time','pole_in_time','pole_out_time')
        trial_start = trial_start - event_time_point
        trial_stop = trial_stop - event_time_point
        cue_start = cue_start - event_time_point
        cue_end = cue_end - event_time_point
        pole_in = pole_in - event_time_point
        pole_out = pole_out - event_time_point
        
        return segmented_data, trial_start, trial_stop, cue_start, cue_end, pole_in, pole_out
       
        