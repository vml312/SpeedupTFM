"""
Get shot changes between scenes in the input video file.

It has a threshold, which is the value used to determine whether a shot change is significant or not. If the shot change is greater than the threshold, 
it is considered a scene change.

This value is between 0 and 1. It is currently set to 0.2, as this is considered a reasonable value for a film without an excessive amount of shot changes.

The ffmpeg output file is stored in the file ''{name}scenesORIG.dep'' and the ffmpeg output file is stored in the file ''{name}shotsORIG.dep''.
"""

import subprocess
import re
import cv2
import os

##
# @brief  Extracts the duration of the input video in frames.
# @param filename   The input filename to determine exact duration from number of frames and fps.
# @return  The duration of the input video in seconds.
##
def mp4_duration_frames(filename):
    video = cv2.VideoCapture(filename)

    frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = video.get(cv2.CAP_PROP_FPS) 
    duration = frame_count / fps

    return duration

##
# @brief  Extracts the scene cuts from the ffmpeg output file.
#         The output file is created by ffmpeg when the scene cut detection filter is applied.
# @param filename   The name of the file where the ffmpeg output is stored.
# @param duration   The duration of the input video.
# @return  A list with the times of the scene cuts.
##
def format_scenes_output(filename, duration):
    times_scene_cuts = []
    pattern = re.compile(r"pts_time:(\d+\.\d+)")
    
    with open(filename, 'r', encoding= 'UTF-8') as file:
        for line in file:        
            match = pattern.findall(line)
            if match:    
                times_scene_cuts.append(float(match[0]))
                
    times_scene_cuts.append(duration)
    
    return times_scene_cuts

##
# @brief  Main function of the script.
# @param path   The path where the video is stored.
# @param file   The name of the video file.
# @param threshold   The threshold value used to determine whether a shot change is significant or not.
# @return  A list with the times of the scene cuts.
##
def main(path, file, threshold):
    current_directory = os.getcwd()
    if path != os.getcwd():
        os.chdir(path)
        
    name = file[:-4]  

    ffmpeg_command = [
        "ffmpeg.exe",
        "-i", file,
        "-filter_complex", f"select='gt(scene,{threshold})',metadata=print:file={name}scenesORIG.dep",
        "-vsync", "vfr",
        "-y", f"dep{file}",
        "2>", f"{name}shotsORIG.dep"
    ]
    
    # Execute the command
    try:
        subprocess.run(ffmpeg_command, check=True, shell=True)
        times_scene_cuts = format_scenes_output(f"{name}scenesORIG.dep", mp4_duration_frames(file))
    except subprocess.CalledProcessError as e:
        print("An error occurred while executing the command:", e)
      
    if path != current_directory:
        os.chdir(current_directory)

    return times_scene_cuts