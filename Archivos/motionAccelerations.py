"""
Non-speech acceleration

The non-speech acceleration shall be found on the basis of the optical flow, which is the variation between consecutive frames, i.e. the variation between consecutive frames. The 
maximum flow of all non-speech fragments has been considered to correspond to the minimum acceleration (acc_motion_min), while the minimum corresponds to the maximum acceleration 
(acc_motion_max). A large number of films from different genres, directors and years of release could have been analysed, but this option has been chosen as it is simpler and 
there are motion acceleration setting parameters.

Unlike voice acceleration, motion acceleration cannot be calculated with velocities because it is not a concrete magnitude, they are unitless values whose value is relative, a unit 
could be defined obtaining a maximum, although it is not considered appropriate. In this process all the non-speech fragments that appear in ''compr_subs.srt'' will be analysed.

"""

import cv2
import numpy as np
import os
import pandas as pd
import pysubs2

import format_ffmpeg_scene_cut

## Parameter as threshold to detect scene cuts, range {0 1}, the lower it is, the lower the threshold
SCENE_CUT_THRESHOLD = 0.2

## High percentile value is taken at 80%
PERCENTAGE_HIGH = 80

## Low percentile value is taken at 20%
PERCENTAGE_LOW = 20

## Decimals to be rounded off in srt for acceleration factor in motion
N_DECIMALS_ACC = 3

##
# @brief  Extracts the duration of the input video in frames.
# @param filename   The input filename to determine exact duration from number of frames and fps.
# @return  The duration of the input video in seconds.
# @return  The number of frames in the video.
# @return  The frames per second of the video.
##
def mp4_duration_frames(filename):
    video = cv2.VideoCapture(filename)

    frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = video.get(cv2.CAP_PROP_FPS) 
    duration = frame_count / fps

    return duration, frame_count, fps

##
# @brief  Function that creates a dense optical flow field to calculate magnitudes from the video.
# @param video_name   The name of the video file.
# @param frame_skip   The number of frames to skip.
# @return  The list of the magnitudes of the optical flow.
##
def optical_flow_dense_from_video(video_name, frame_skip):
    cap = cv2.VideoCapture(video_name)
    # Get the first frame
    ret, frame1 = cap.read()
    # Convert the frame to grayscale
    prvs = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    
    mag_list = []
    frame_count = 0
    while True:
        # Read the next frame
        ret, frame2 = cap.read()
        if not ret:
            break
        frame_count += 1 

        if frame_skip:
            if frame_count % frame_skip != 0:
                continue
        # Convert the frame to grayscale
        next_frame = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        # Calculates dense optical flow by Farneback method
        flow = cv2.calcOpticalFlowFarneback(prvs, next_frame, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        # Computes the magnitude and angle of the 2D vectors
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        # Define the window size for the moving average
        window_size = 15
        step_size = 5  # Step size for moving window
        mean_mags = []  # To store the calculated mean magnitudes
        # Apply the moving average
        for i in range(0, magnitude.shape[0] - window_size, step_size):
            # Define the moving window
            window = magnitude[i : i + window_size]
            # Calculate the mean of the window
            mean_mag = np.mean(window)
            mean_mags.append(mean_mag)  # Store the mean magnitude
        # Analyze the mean magnitudes to identify high-motion regions
        if len(mean_mags)>0:
            high_motion_threshold = np.percentile(mean_mags, 90)  # Example threshold
            high_motion_windows = [mag for mag in mean_mags if mag > high_motion_threshold]
            mean95 = np.mean(high_motion_windows)
            mag_list.append(mean95)

        prvs = next_frame
    # Release the video capture and close all windows
    cap.release()
    cv2.destroyAllWindows()

    return mag_list

##
# @brief Calculate the optical flow parameters from all the else fragments:
# Every %frame_skip% frames, the optical flow is calculated, parameters are appended to a dataframe for statistics.
# After processing each fragment, percentile high and low values are calculated and the maximum and minimum acceleration values are assigned to the dataframe.
# @param path   The path where the video files are stored.
# @param videos_order   The list of the video files in order by number.
# @param frame_skip   The number of frames to skip.
# @param acc_max   The maximum acceleration.
# @param acc_min   The minimum acceleration.
# @return  The dataframe with the optical flow values.
# 
def calculate_opticalflow_parameters_df(path, videos_order, frame_skip, acc_max, acc_min):
    
    columns= pd.Series(["magnitude","n-frame", "time-s", "percentile-high", "percentile-low", "acc", "acc-max", "acc-min", "rem-time-s"])
    df = pd.DataFrame(columns= columns)
    
    count_df = 0
    
    for count_vid, vid in enumerate(videos_order):
        filer = os.path.join(path, vid)
        lista = optical_flow_dense_from_video(filer, frame_skip)
        
        duration, frame_count, fps = mp4_duration_frames(filer)
        
        for count, value in enumerate(lista):
            if frame_skip:
                n_frame = frame_skip + count * (frame_skip)
            else:
                n_frame = count
                
            df.loc[count_df, "n-frame"] = n_frame
            df.loc[count_df, "time-s"] = df.loc[count_df, "n-frame"]/fps
            df.loc[count_df, "magnitude"] = value
            df.loc[count_df, "rem-time-s"] = duration - df.loc[count_df, "time-s"]
            df.loc[count_df, "n-video"] = count_vid
            count_df += 1

    percentile_high = df["magnitude"].quantile(PERCENTAGE_HIGH/100)
    percentile_low = df["magnitude"].quantile(PERCENTAGE_LOW/100)
    
    df.loc[0, "percentile-high"] = percentile_high
    df.loc[0, "percentile-low"] = percentile_low
    df.loc[0, "acc-min"] = acc_min
    df.loc[0, "acc-max"] = acc_max
    
    return df

##
# @brief  Get the acceleration from the limits
# @param value   The value to get the acceleration from
# @param acc_max   The maximum acceleration
# @param acc_min   The minimum acceleration
# @param value_max   The maximum value
# @param value_min   The minimum value
# @return  The acceleration
##
def get_acc_from_limits(value, acc_max, acc_min, value_max, value_min):
    acc = acc_max - ((acc_max - acc_min)/(value_max - value_min))*(value - value_min)
    if np.isneginf(acc) or np.isposinf(acc) or np.isnan(acc):
        acc = acc_max
    return acc

##
# @brief  This function finds sub-segments within the original video fragment, the procedure has been to calculate the average of the flow # every ''duration_video_min'', if it is in
# one state and exceeds the opposite limit, it changes state and calculates its acceleration. Apart from these two actions, an order number ''acc-interval'' is assigned which defines
# the interval number found. With this step, the accelerations have been calculated from the optical flow.
# @param df   The dataframe with the optical flow values
# @param min_video_duration   The minimum video duration
# @param percentile_high   The high percentile value
# @param percentile_low   The low percentile value
# @param acc_max   The maximum acceleration
# @param acc_min   The minimum acceleration
# @param value_max   The maximum value
# @param value_min   The minimum value
# @return  The dataframe with the calculated accelerations
# @return  The error value
##
def time_series_subsegments(df, min_video_duration, percentile_high, percentile_low, acc_max, acc_min, value_max, value_min):
    state = "low"
    error = 0
    
    #Error due to large frame_skip or badly cropped video
    if len(df) > 1:
        time_between_frames = df.loc[1, "time-s"] - df.loc[0, "time-s"]
        
        n_frames_is_threshold = int(min_video_duration/time_between_frames)
        
        mag_of_frames_in_interval = [0 for i in range(n_frames_is_threshold)] #average_motion = n_frames_is_threshold*[0]
    
        acc_interval = 0
        
    elif len(df) == 1:
        df["acc"] = acc_min
        error = 1
        return df, error
    
    if len(df) <= n_frames_is_threshold:
        acc = get_acc_from_limits(df["magnitude"].mean(), acc_max, acc_min, value_max, value_min)
        df["acc"] = acc_min
        error = 1
        return df, error
    
    for i in df.index:

        mag_of_frames_in_interval[i%n_frames_is_threshold] = df.loc[i, "magnitude"]
        
        av_motion = np.mean(mag_of_frames_in_interval)
        
        if i < n_frames_is_threshold:
            df.loc[i, "acc-interval"] = acc_interval
            continue
        elif i == n_frames_is_threshold:
            acc = get_acc_from_limits(av_motion, acc_max, acc_min, value_max, value_min)
            df.loc[0:n_frames_is_threshold-1, "acc"] = acc
        elif state == "low":
            if av_motion > percentile_high and df.loc[i, "rem-time-s"]>=min_video_duration:
                acc = get_acc_from_limits(av_motion, acc_max, acc_min, value_max, value_min)
                state = "high"
                acc_interval += 1
            else:
                acc = df.loc[i-1, "acc"]
        elif state == "high":
            if av_motion < percentile_low and df.loc[i, "rem-time-s"]>=min_video_duration:
                acc = get_acc_from_limits(av_motion, acc_max, acc_min, value_max, value_min)
                state = "low"
                acc_interval += 1
            else:
                acc = df.loc[i-1, "acc"]
        df.loc[i, "acc"] = acc
        df.loc[i, "acc-interval"] = acc_interval
    
    return df, error

##
# @brief  This function calculates the average of all the accelerations that are part of a scene, so that the duration of the accelerated scenes is still greater than the parameter
# entered in the configuration file (''min_video_duration''), and there aren't too many different acceleration values.
# @param df   The dataframe with the optical flow values
# @return  The dataframe with the corrected accelerations
##
def correct_acc_min_video_duration(df):
    for value in df["acc-interval"]:
        new_acc = df.loc[df["acc-interval"] == value, "acc"].mean()
        df.loc[df["acc-interval"] == value, "acc"] = new_acc
    return df
    
##
# @brief Acceleration correction for plane changes: If the previous process (time_series_subsegments) returns an error signal for having fewer frames than necessary to process the 
# stream, the minimum acceleration is assigned to this video fragment. If it does not, the procedure continues and enters a function (correct_acc_min_video_duration) to correct the 
# acceleration according to the existing plane changes.

# First, the program format_ffmpeg_scene_cut is run to obtain the changes of scene of the video and each scene is assigned its number in the ''interval'' column. The acceleration
# of each processed frame is then adjusted so that the duration of the accelerated scenes is greater than the parameter entered in the configuration file (''min_acc_scene_duration'')
# Since the correction has potentially varied the acceleration value of all the frames in them, the average of all the accelerations that are part of a scene is taken (correct_acc_min_video_duration)
# @param path   The path where the video files are stored
# @param filename   The name of the video file
# @param scene_cut_threshold   The threshold to detect scene cuts
# @param df   The dataframe with the optical flow values
# @param min_acc_scene_duration   The minimum accelerated scene duration
# @return  The dataframe with the corrected accelerations
##
def correct_acc_from_scene_cuts(path, filename, scene_cut_threshold, df, min_acc_scene_duration):
    
    scene_cut_times = format_ffmpeg_scene_cut.main(path, filename, scene_cut_threshold)
    
    #Time case is 0.101 and skipping 5 frames, first time is 0.2
    if df.loc[0, "time-s"]>scene_cut_times[0]:
        scene_cut_times[0] = df.loc[0, "time-s"]
    
    index_df = 0
    interval_time=0
    
    for count, left_interval in enumerate(scene_cut_times):
        while index_df < len(df) and df.loc[index_df, "time-s"]<=left_interval: 
            df.loc[index_df, "interval"] = count
            index_df += 1
        
        interval_duration = left_interval - interval_time
        acc_interval = df.loc[df["interval"] == count, "acc"]
        mean_acc_interval = acc_interval.mean()
        
        interval_time_acc = interval_duration/mean_acc_interval
        interval_time = left_interval
    
        if interval_time_acc < min_acc_scene_duration:
            scale_factor = min_acc_scene_duration / interval_time_acc
            df.loc[df["interval"] == count, "acc"] = acc_interval/scale_factor
 
    #Correct possible errors of less than min_video_duration, average set of accelerations
    df = correct_acc_min_video_duration(df)
    
    return df

## 
# @brief  This function corrects the acceleration values of the groups of frames that have the same inverse acceleration value.
# It is done this way because video part of file is accelerated with inverse value of acceleration factor in ffmpeg.
# @param df   The dataframe with the optical flow values
# @return  The dataframe with the corrected accelerations
##
def correct_groups_acc_interval(df):
    ##If acc's inverse value rounded to 2 decimals it's the same, the previous one is kept, otherwise it changes.
    previous_acc = df.loc[0, 'acc']
    previous_acc_interval = df.loc[0, 'acc-interval']

    for i in range(1, len(df)):
        current_acc = df.loc[i, 'acc']
    
        previous_acc_inverse = round(1/previous_acc, N_DECIMALS_ACC)
        current_acc_inverse  = round(1/current_acc, N_DECIMALS_ACC)
    
        if previous_acc_inverse == current_acc_inverse:
            df.loc[i, 'acc-interval'] = previous_acc_interval
            df.loc[i, 'acc'] = previous_acc
        else:
            previous_acc = current_acc
            previous_acc_interval = df.loc[i, 'acc-interval']
    
    return df
    
##
# @brief  This function creates a new srt file with the acceleration values of the non-speech fragments.
# Once all the processing is done for each fragment, the acceleratetion of the new fragment is added at the end of the file with the format ''else(\d.\d\d)''.
# @param path   The path where the video files are stored
# @param srt_file   The original subtitle file
# @param frame_skip   The number of frames to skip
# @param min_acc_scene_duration   The minimum accelerated scene duration
# @param min_video_duration   The minimum video duration
# @param acc_max   The maximum acceleration
# @param acc_min   The minimum acceleration
# @param videos_order   The list of the video files in order by number
##
def srt_generator(path, srt_file, frame_skip, min_acc_scene_duration, min_video_duration, acc_max, acc_min, 
                  videos_order, flag_podcast, acc_constant):

     subs = pysubs2.load(srt_file, encoding= 'UTF-8', format_= 'srt')
     
     if flag_podcast:
        for sub in subs:
            if sub.text == "else":
                sub.text+=str(round(1/acc_constant, N_DECIMALS_ACC))
     else:
         list_sub_times=[]
         
         for sub in subs:
             if sub.text == "else":
                 list_sub_times.append([sub.start/1000, sub.end/1000])
                 subs.remove(sub)
         
         df_total = calculate_opticalflow_parameters_df(path, videos_order, frame_skip, acc_max, acc_min)
         percentile_high = df_total.loc[0, "percentile-high"]
         percentile_low = df_total.loc[0, "percentile-low"]
         value_max = max(df_total["magnitude"])
         value_min = min(df_total["magnitude"])
         
         for count, vid in enumerate(videos_order):
    
             df = df_total[df_total["n-video"]==count].copy().reset_index(drop=True)
             
             df, error = time_series_subsegments(df, min_video_duration, percentile_high, percentile_low, acc_max, acc_min, 
                                                 value_max, value_min)
             
             start_time = list_sub_times[count][0]
             end_time = list_sub_times[count][1]
             
             if not error:
                 df = correct_acc_from_scene_cuts(path, vid, SCENE_CUT_THRESHOLD, df, min_acc_scene_duration)
                 df = correct_groups_acc_interval(df)

                 groups = df['acc-interval'].unique()
                 df["time-s"]+=start_time
                 
                 for i, group in enumerate(groups):
                     
                     group_max = df[df['acc-interval'] == group]['time-s'].max()
                     
                     acc = max(df[df['acc-interval'] == group]['acc'].unique())
             
                     if i == 0:
                         min_time = start_time
                     else:
                         min_time = df[df['acc-interval'] == groups[i - 1]]['time-s'].max()
                     if i == len(groups) - 1:
                         max_time = end_time 
                     else:
                         max_time = group_max
                     
                     acc_div = round(1/acc, N_DECIMALS_ACC)
                     if acc_div > (1/acc_min):
                         acc_div = 1/acc_min
                     subs.append(pysubs2.SSAEvent(start = pysubs2.make_time(s=min_time), end=pysubs2.make_time(s=max_time), text=f"else{acc_div}"))
         
             else:
                 acc = df.loc[0, "acc"]
                 acc_div = round(1/acc, N_DECIMALS_ACC)
                 if acc_div > (1/acc_min):
                     acc_div = 1/acc_min
                 subs.append(pysubs2.SSAEvent(start = pysubs2.make_time(s=start_time), end=pysubs2.make_time(s=end_time), text=f"else{acc_div}"))
        
     subs.sort()
     subs.save(srt_file)
     return 1

##
# @brief  Main function of the script.
# @param path   The path where the video files are stored.
# @param srt_file   The original subtitle file.
# @param frame_skip   The number of frames to skip.
# @param acc_max   The maximum acceleration.
# @param acc_min   The minimum acceleration.
# @param min_acc_scene_duration   The minimum accelerated scene duration.
# @param min_video_duration   The minimum video duration.
##
def main(path, srt_file, frame_skip, acc_max, acc_min, min_acc_scene_duration, min_video_duration, flag_podcast, acc_constant):
    
    files = os.listdir(path)
    videos = []
    
    for n_file in files:
        if n_file[-4:]==".mp4":
            # if n_file[-9:-4]=="voice" or n_file[0:3]=="dep": # To ensure there are no previous files from other processing
            #     os.remove(path + '/' + n_file)
            if n_file[-8:-4]=="else": # To select only else fragments
                videos.append(n_file)
                
    # Video order by number (\d+else.mp4)
    videos_order = sorted(videos, key=lambda x: int(x.split("else")[0]))
    
    srt_generator(path, srt_file, frame_skip, min_acc_scene_duration, min_video_duration, acc_max, acc_min, videos_order, 
                  flag_podcast, acc_constant)
    
    files = os.listdir(path)
            
    for n_file in files:
        if n_file[-4:]==".mp4":
            if n_file[-4:]==".dep" or n_file[0:3]=="dep":
                os.remove(path + '/' + n_file)
                
    return 1
    