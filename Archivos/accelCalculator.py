
"""
Obtaining final speech/non-speech fragments and their acceleration

This is the fundamental block of the improvement made. It is divided into obtaining the acceleration of speech fragments and non-speech fragments, 
in addition to correcting the parameters received from the configuration file if they have an accelerations is that we have the durations of each 
fragment, whether it is speech or non-speech and the acceleration factor.
"""

import pysubs2

import motionAccelerations
import voiceAccelerations

## Language in which the subtitles are in
LANGUAGE_PREFIX = 'es' 

## Decimals to be rounded off in csv
N_DECIMALS = 4 

## Decimals to be rounded off in srt for acceleration factor in voice
N_DECIMALS_ACC = 3

## Minimum estimated speed in phonemes/second considered acceptable
MIN_SPEED = 4

## Maximum estimated speed in phonemes/second considered acceptable
MAX_SPEED = 20 

## Minimum number of subtitles considered acceptable
N_SUBTITLES_MIN = 50

## Maximum voice acceleration (range 1.6-1.8)
ACC_VOICE_MAX = 1.7

## Minimum voice acceleration (range 1-1.2)
ACC_VOICE_MIN = 1

## Maximum motion acceleration (range 8-12)
ACC_MOTION_MAX = 10

## Minimum motion acceleration (range 1-4)
ACC_MOTION_MIN = 1

## Minimum duration of video segmented (range 1-2 seconds)
MIN_VIDEO_DURATION = 1

## Maximum duration of scene accelerated (range 0.5 - 1 seconds)
MIN_ACC_SCENE_DURATION = 0.5

## To reduce processing time, optical flow is calculated every %FRAME_SKIP% frames 
FRAME_SKIP = 5 

## Voice constant acceleration if INA is selected, no subtitle analysis to calculate acceleration
ACC_VOICE_INA = (ACC_VOICE_MAX + ACC_VOICE_MIN)/2 

## Motion constant acceleration if there is only voice to process (e.g. a podcast)
ACC_MOTION_CONSTANT = ACC_MOTION_MAX

##
# @brief Function that gets the list of voice accelerations
# @param voice_else_srt: The file with the voice and else subtitles
# @param film_srt: The file with the film subtitles
# @param input_path: The path where the files are stored
# @param target_min_speed: The minimum target speed
# @param target_max_speed: The maximum target speed
# @param reference: The reference to calculate the acceleration
# @param acc_max: The maximum acceleration
# @param acc_min: The minimum acceleration
##
def voice_speed_list(voice_else_srt, film_srt, input_path, 
                     target_min_speed, target_max_speed, reference, acc_max, acc_min, n_segs_threshold):

    subs= pysubs2.load(voice_else_srt, encoding= 'UTF-8', format= 'srt')
    
    if reference == "ina":
        for sub in subs:
            if sub.text == "voice":
                sub.text += str(round(1/ACC_VOICE_INA, N_DECIMALS_ACC))
    else:
        srt_name = film_srt[:-4]
        df = voiceAccelerations.main(srt_name, LANGUAGE_PREFIX, N_DECIMALS, 
                                     n_segs_threshold, MIN_SPEED, MAX_SPEED, N_SUBTITLES_MIN, input_path)
        
        # Runs after having the dataframe in case there are errors in assigning mean or max values.
        target_min_speed, target_max_speed = correct_target_speed_voice(df, target_min_speed, target_max_speed)
        
        # Run after having the target_speed corrected if it had to be corrected.
        df = voiceAccelerations.acc_calculate_csv_format(film_srt[:-4], df, 
                                                         target_min_speed, target_max_speed, N_DECIMALS, input_path)

        for sub in subs:
            if sub.text == "voice":
                start_s   = sub.start/1000
                end_s   = sub.end/1000
                
                current_acc = 0
                n_voice_subs_1s = 0
                i = 1  
                while i <= len(df) and df.loc[i, 'end-time-s']<= end_s:
                    if df.loc[i, 'start-time-s']>= start_s and df.loc[i, 'end-time-s']<= end_s:
                        current_acc += df.loc[i, 'acceleration-factor-1s']
                        n_voice_subs_1s += 1
                    i += 1

                acc = round(n_voice_subs_1s/current_acc, N_DECIMALS_ACC)
                # acc < 0.1 (10x)
                if acc < 1/acc_max:
                    print("acc: " + str(round(1/acc, N_DECIMALS_ACC)) + ", acc > acc_max, acc_max: " + str(acc_max))
                    acc = 1/acc_max
                # acc > 1 (1x)
                if acc > 1/acc_min:
                    print("acc: " + str(round(1/acc, N_DECIMALS_ACC)) + ", acc < acc_min, acc_min: " + str(acc_min))
                    acc = 1/acc_min

                sub.text += str(round(acc, N_DECIMALS_ACC))
    
    subs.save(voice_else_srt[:-4]+"_acc.srt")
    
    return target_min_speed, target_max_speed

##
# @brief Function that applies correction logic for target_speed of voice
# @param df: The dataframe with the mean speed and max speed of voice subtitles
# @param target_min_speed: The minimum target speed
# @param target_max_speed: The maximum target speed
##
def correct_target_speed_voice(df, target_min_speed, target_max_speed):

    try:
        target_min_speed = float(target_min_speed)
    except:
        target_min_speed = df.loc[1, 'mean-speed-1s']
        print("target_min_speed is not a float number. Now target_min_speed:", target_min_speed)
    try:
        target_max_speed = float(target_max_speed)
    except:
        target_max_speed = df.loc[1, 'max-speed-1s']
        print("target_max_speed is not a float number. Now target_max_speed:", target_max_speed)

    if target_max_speed < target_min_speed:
        print("Warning: target_max_speed < target_min_speed. Results won't be as expected")
    if target_max_speed <= 0:
        target_max_speed = df.loc[1, 'max-speed-1s']
        print(f"Error: target_max_speed <= 0. Now target_max_speed: {target_max_speed}")
    if target_min_speed <= 0:
        target_min_speed = df.loc[1, 'mean-speed-1s']
        print(f"Error: target_min_speed <= 0. Now target_min_speed: {target_min_speed}")

    return round(target_min_speed, 1), round(target_max_speed, 1)

##
# @brief Function that applies correction logic for voice acceleration
# @param acc_voice_max: The maximum voice acceleration
# @param acc_voice_min: The minimum voice acceleration
##
def correct_acc_voice(acc_voice_max, acc_voice_min):

    try:
        acc_voice_max = float(acc_voice_max)
    except:
        print(f"acc_voice_max is not a float number. Now acc_voice_max: {ACC_VOICE_MAX}")
        acc_voice_max = ACC_VOICE_MAX
    try:
        acc_voice_min = float(acc_voice_min)
    except:
        print(f"acc_voice_min is not a float number. Now acc_voice_max: {ACC_VOICE_MIN}")
        acc_voice_min = ACC_VOICE_MIN
        
    if acc_voice_max < acc_voice_min:
        print("Warning: acc_voice_max < acc_voice_min")
    if acc_voice_max <= 0:
        print(f"Error: acc_voice_max <= 0. Now acc_voice_max: {ACC_VOICE_MAX}")
        acc_voice_max = ACC_VOICE_MAX
    if acc_voice_min <= 0:
        print(f"Error: acc_voice_min <= 0. Now acc_voice_min: {ACC_VOICE_MIN}")
        acc_voice_min = ACC_VOICE_MIN
        
    return acc_voice_max, acc_voice_min

##
# @brief Function that applies correction logic for motion acceleration
# @param acc_motion_max: The maximum motion acceleration
# @param acc_motion_min: The minimum motion acceleration
##
def correct_acc_motion(acc_motion_max, acc_motion_min):

    try:
        acc_motion_max = float(acc_motion_max)
    except:
        print(f"acc_motion_max is not a float number. Now acc_motion_max: {ACC_MOTION_MAX}")
        acc_motion_max = ACC_MOTION_MAX
    try:
        acc_motion_min = float(acc_motion_min)
    except:
        print(f"acc_motion_min is not a float number. Now acc_motion_min: {ACC_MOTION_MIN}")
        acc_motion_min = ACC_MOTION_MIN
        
    if acc_motion_max < acc_motion_min:
        print("Warning: acc_motion_max < acc_motion_min")
    if acc_motion_max <= 0:
        print(f"Error: acc_motion_max <= 0. Now acc_motion_max: {ACC_MOTION_MAX}")
        acc_motion_max = ACC_MOTION_MAX
    if acc_motion_min <= 0:
        print(f"Error: acc_motion_min <= 0. Now acc_motion_min: {ACC_MOTION_MIN}")
        acc_motion_min = ACC_MOTION_MIN
        
    return acc_motion_max, acc_motion_min

##
# @brief Function that applies correction logic for min_video_duration and min_acc_scene_duration
# @param min_video_duration: The minimum video duration
# @param min_acc_scene_duration: The minimum accelerated scene duration
# @param n_segs_threshold: The maximum difference between subtitles without being grouped together in seconds
##
def correct_duraciones(min_video_duration, min_acc_scene_duration, n_segs_threshold):

    try:
        min_video_duration = float(min_video_duration)
    except:
        print(f"min_video_duration is not a float number. Now min_video_duration: {MIN_VIDEO_DURATION} seconds")
        min_video_duration = MIN_VIDEO_DURATION
    try:
        min_acc_scene_duration = float(min_acc_scene_duration)
    except:
        print(f"min_acc_scene_duration is not a float number. Now min_acc_scene_duration: {MIN_ACC_SCENE_DURATION} seconds")
        min_acc_scene_duration = MIN_ACC_SCENE_DURATION
        
    if min_video_duration < min_acc_scene_duration:
        print("Error/Warning: min_video_duration < min_acc_scene_duration")
    if min_video_duration <= 0:
        print(f"Error: min_video_duration <= 0. Now min_video_duration: {MIN_VIDEO_DURATION} seconds")
        min_video_duration = MIN_VIDEO_DURATION
    if min_acc_scene_duration <= 0:
        print(f"Error: min_acc_scene_duration <= 0. Now min_acc_scene_duration: {MIN_ACC_SCENE_DURATION} seconds")
        min_acc_scene_duration = MIN_ACC_SCENE_DURATION

    if min_video_duration > n_segs_threshold:
        print(f"Warning: min_video_duration > n_segs_threshold. n_segs_threshold: {n_segs_threshold} seconds, acceleration will not be computed as it should, because there may be fragments whose duration is shorter than min_video_duration.\n")
        
    return min_video_duration, min_acc_scene_duration

##  
# @brief Main function that calculates the acceleration of the voice and the motion
# @param input_path: The path where the files are stored
# @param voice_else_srt: The subtitle file with the voice and else subtitles
# @param film_srt: The subtitle file with the film subtitles
# @param target_min_speed: The minimum target speed
# @param target_max_speed: The maximum target speed
# @param reference: The reference of processing (ina or srt), if it is ina, the voice acceleration is calculated with a constant value, if it is srt, motion and voice accelerations must be calculated.
# @param acc_voice_max: The maximum voice acceleration
# @param acc_voice_min: The minimum voice acceleration
# @param acc_motion_min: The minimum motion acceleration
# @param acc_motion_max: The maximum motion acceleration
# @param min_acc_scene_duration: The minimum accelerated scene duration
# @param min_video_duration: The minimum video duration
# @param n_segs_threshold: The maximum difference between subtitles without being grouped together in seconds
# @param flag_podcast: Flag to indicate if the input is a podcast, if it is, the motion acceleration is calculated with a constant value (%ACC_MOTION_CONSTANT%)
# @return target_min_speed: The minimum target speed potentially corrected
# @return target_max_speed: The maximum target speed potentially corrected
##
def main(input_path, voice_else_srt, film_srt, target_min_speed, target_max_speed, reference, acc_voice_max, 
         acc_voice_min, acc_motion_min, acc_motion_max, min_acc_scene_duration, min_video_duration, n_segs_threshold, flag_podcast):

    new_voice_else_srt = voice_else_srt[:-4]+"_acc.srt"
    
    # If it is a podcast, the motion acceleration is calculated with a constant value and the duration of the video segments and the accelerated scenes aren´t used, there is no video track.
    if not flag_podcast:
        acc_motion_max, acc_motion_min = correct_acc_motion(acc_motion_max, acc_motion_min)
        min_video_duration, min_acc_scene_duration = correct_duraciones(min_video_duration, min_acc_scene_duration, n_segs_threshold)
    
    # If there is no subtitle file, there is no need to calculate the acceleration of the voice, it is calculated with a constant value %ACC_VOICE_INA%
    if not reference == "ina":
        acc_voice_max, acc_voice_min = correct_acc_voice(acc_voice_max, acc_voice_min)
    
    target_min_speed, target_max_speed = voice_speed_list(voice_else_srt, film_srt, input_path, target_min_speed, 
                                                          target_max_speed, reference, acc_voice_max, acc_voice_min, n_segs_threshold)
    
    motionAccelerations.main(input_path, new_voice_else_srt, FRAME_SKIP, acc_motion_max, acc_motion_min, 
                             min_acc_scene_duration, min_video_duration, flag_podcast, ACC_MOTION_CONSTANT)
    
    return target_min_speed, target_max_speed
