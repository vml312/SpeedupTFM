"""
Acceleration of video clips

It has five phases and checks of correct functioning, because if it is a podcast, the video track is empty and processing should be different.

    1. Creation of a copy of the received fragment.

    2. Separation of image and sound into two files to perform the acceleration separately.

    3. Acceleration of the image: This file is accelerated with the selected speed factor and saved in a temporary file. With this product, the duration of the product of old duration and 
    speed factor is rounded off to get the exact result. 

    4. Sound acceleration: The audio file is accelerated by the input factor.

    5. Finally, both files are combined to have the final accelerated fragment with image and sound, and the temporary files are deleted.
"""

import re
import subprocess
import os
import shutil

## 
# @brief Function to remove a file
# @param filename The name of the file to be removed
##
def REMOVEFILE(filename):
    try:
        os.remove(filename)
    except OSError:
        pass
    return
    
##
# @brief Function to delete temporary files
#
# .
##
def deleteTempFiles():
    REMOVEFILE('copy.mp4')
    REMOVEFILE('audio.mp3')
    REMOVEFILE('video.mp4')
    REMOVEFILE('temp.mp4')
    REMOVEFILE('final.mp4')
    REMOVEFILE('final.mp3')
    return

##
# @brief Function to extract the name of the file
# @param file_path The path of the file
# @return The name of the file
##
def name(file_path):
    # substract file_name from file_path:
    file_name = re.findall(r'(\w+\.(?:mp4))', file_path)[0]
    return file_name

##
# @brief Function to accelerate the video
# @param file_path The path of the file
# @param speed_factor The acceleration factor
##
def speed(file_path, speed_factor):

    file_name = name(file_path)

    subprocess.run(['ffmpeg', '-y', '-i', file_name, '-codec', 'copy', 'copy.mp4'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # creating a .mp4 copy of the file

    # separate mp3 and mp4 - both must be accelerated
    subprocess.run(['ffmpeg', '-y', '-i', 'copy.mp4', 'audio.mp3'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result = subprocess.run(['ffmpeg', '-y', '-i', 'copy.mp4', '-c:v', 'copy', '-an', 'video.mp4'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # If copy of video without sound cannot be made, it may be because video track is empty, it is highly likely a podcast
    flag_podcast = False
    if result.returncode == 1:
        flag_podcast = True
        shutil.copyfile("copy.mp4", "video.mp4")
        
##### 1. Video part -> apply video filter -> speed set according to the speed_factor #####
    result = subprocess.run(['ffmpeg', '-y', '-i', 'video.mp4', '-filter:v', f'setpts={speed_factor}*PTS', 'temp.mp4'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Usually associated with flag_podcast, this usually does not the acceleration but neither generates errors
    if result.returncode == 1:
        shutil.copyfile("video.mp4", "temp.mp4")
        
    # trim the obtained video -> its duration = old_duration * speed_factor
    old_duration = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
         'copy.mp4'], capture_output=True, text=True)
    old_duration = float(old_duration.stdout.strip())
    speed_f = float(speed_factor)
    new_duration = old_duration * speed_f
    subprocess.run(['ffmpeg', '-y', '-i', 'temp.mp4', '-to', str(new_duration), '-c', 'copy', 'final.mp4'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
##### 2. Audio part #####
    subprocess.run(['ffmpeg', '-y', '-i', 'audio.mp3', '-af', f'atempo={1/speed_f}', 'final.mp3'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Check possible errors if it is a podcast
    actual_duration_check_result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
         'final.mp4'], capture_output=True, text=True)
    actual_duration_check = float(actual_duration_check_result.stdout.strip())
    
    # It is wrong when distance from old duration to actual is lower than difference between new duration and actual, and flag was up.
    if (abs(actual_duration_check - old_duration) < abs(actual_duration_check - new_duration)) and flag_podcast:
        os.unlink("final.mp4")
        subprocess.run(f"ffmpeg -f lavfi -i color=c=black:s=1280x720:r=1 -c:v libx264 -crf 0 -t {new_duration} final.mp4")
        
##### 3. Combine audio & video #####
    # When audio is really small (13 ms, else=1.3s acc=0.1) mp3 is corrupted, solution is to just create the silent video
    result = subprocess.run(['ffmpeg', '-y', '-i', 'final.mp4', '-i', 'final.mp3', '-c:v', 'copy', '-c:a', 'aac', '-async', '1', 'finalRESULT.mkv'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if result.returncode == 1:
        result2 = subprocess.run(['ffmpeg', '-y', '-i', 'final.mp4', '-c:v', 'copy', 'finalRESULT.mkv'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result2.returncode == 0:
            print(f"Error: ffmpeg returned non-zero exit status {result.returncode}. \n ({file_name[:-4]}.mp3 probably corrupted, too small with acc {speed_factor})")
        else:
            os.rename('final.mp4', 'finalRESULT.mkv')
            print(f"Error: ffmpeg returned non-zero exit status {result.returncode} again. \n ({file_name[:-4]}.mp4 probably corrupted, too small with acc {speed_factor})")
        
    deleteTempFiles()
    return

##
# @brief Main function with no arguments, because they are in the configuration speed file (configurationSpeed.txt)
#
# .
##
def main():
    #configuration file usage
    with open("configurationSpeed.txt", 'r', encoding='utf8', newline='\r\n') as input:
        data = []
        lines = input.read().splitlines()
        for line in lines:
            data.append(line.split("=")[1])
        file_path = data[0]
        choice = data[1]
        speed_factor = float(data[2])
        length = float(data[3])
    
    if choice == "speed":
        if float(speed_factor) == 0.0:
            print("Invalid speed factor!")
        speed(file_path, speed_factor)
    
    elif choice == "length":
        if float(length) == 0.0:    #input expressed in minutes
            print("Invalid length!")
        length = float(length)
        length = length*60 + 1  #convert to seconds + 1s
        old_duration = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
             name(file_path)], capture_output=True, text=True)
        old_duration = float(old_duration.stdout.strip())
        speed_factor = length/old_duration
        speed(file_path, speed_factor)
    
    else:
        print("Error when selecting input option")
        
    return