"""
Acceleration of the original subtitle file (accelerate_srt)

The actual operation of the file has the following srt files as input:
1. Use "compr_subs_acc.srt" to get all the trimmed video fragments.
2. Use "pelicula.srt" to have the text of each subtitle.
3. Use "voice-else_subs.srt" to have the text of each subtitle and differentiate between voice and else more easily than with "pelicula.srt".

The operation is as follows:
1. Calculation of reduction factor: Dividing the sum of MPEG-TS fragments duration by the whole video, when the concatenation is done this number is equal to 1, but when the 
adjustment is done to a time entered by keyboard this value is far from 1, because when this acceleration is done the subtitle times are not taken into account.

2. Creation of the base subtitle file to create the accelerated file: First the speech subtitles are inserted in ''voice_else.srt'' and then the non-speech subtitles in 
''compr_subs_acc.srt''. The reason is that in the first one the speech subtitles are not compressed, and in the second one there are more non-speech fragments because it has been 
analysed if they have different acceleration.

3. Obtaining a list of percentages of duration of each speech subtitle. To divide the speech subtitles in the file where the speech subtitles are compressed by 1 if they are separated
by less than 1 second, the percentage is found and then the accelerated time is found.

4. Time modification of the file created in step 3. The times are created by adding the durations of the MPEG-TS files, which are accelerated files, to each speech fragment 
corresponds the subtitles it had without acceleration in the original subtitle file. The expressions are the following:

duration_speedup = mp4_duration(f"{count+1}.ts")*1000*percentage_duration_list[ult_ind]/reduction_factor
accelerated_voice_else_subs[ult_ind].start = start
accelerated_voice_else_subs[ult_ind].end = start + duration_speedup

And therefore, when a speech fragment has more than one speech subtitle, the list of duration percentages will have a value other than 1 for that index, making it match the original with a minimum offset. The start 
and end times are therefore calculated as below.

6. Removal of non-speech subtitles. Speech and non-speech times have been accelerated above because the TS files are of both types, therefore only the speech ones are kept, to save 
the final product.
"""

import pysubs2
import re
import os
import subprocess

##
# @brief  Extracts the duration of the input video with ffmpeg.
# In other functions, duration is calculated with the number of frames and frame rate, but here it can`t be done like that because the input may be a mp4 with no video track (podcast).`
# @param filename   The input filename to determine exact duration.
# @return  The duration of the input video in seconds.
##
def mp4_duration(filename):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
         filename], capture_output=True, text=True)
    duration = float(result.stdout.strip())
    return duration

## 
# @brief  Accelerates the original subtitle file.
# @param input_path   The path where the files are stored.
# @param srt_file   The original subtitle file.
# @param voice_else_srt   The subtitle file with the voice and else subtitles.
# @param compr_acc_srt   The subtitle file with the compressed subtitles.
# @param new_name   The name of the new subtitle file.
# @param speedup_video_name   The name of the speedup video.
##
def main(input_path, srt_file, voice_else_srt, compr_acc_srt, new_name, speedup_video_name):
    # Starting from compr_subs_acc
    os.chdir(input_path)
    
    acc_subs = pysubs2.load(compr_acc_srt, encoding = "UTF-8", format_= "srt")
    srt_subs = pysubs2.load(srt_file, encoding = "UTF-8", format_= "srt")
    voice_else_subs = pysubs2.load(voice_else_srt, encoding = "UTF-8", format_= "srt")
    
    duration = 0
    for count, sub in enumerate(acc_subs):
        duration += mp4_duration(f"{count+1}.ts")
        
    duration_summarised = mp4_duration(speedup_video_name)
    
    reduction_factor = duration / duration_summarised
    
    #############################################
    # Add voice from compr_subs_acc to voice_else
    
    elsepattern = "^else"
    list_voiceelse_subs_filtered = [sub for sub in voice_else_subs if not re.search(elsepattern, sub.text)]
    
    accelerated_voice_else_subs = pysubs2.SSAFile()
    
    for sub in list_voiceelse_subs_filtered:
        accelerated_voice_else_subs.append(sub)
        
    #############################################
    # Add else from compr_subs_acc to voice_else
    list_voiceelse_subs_filtered = [sub for sub in acc_subs if re.search(elsepattern, sub.text)]
    
    for sub in list_voiceelse_subs_filtered:
        accelerated_voice_else_subs.append(sub)
        
    accelerated_voice_else_subs.sort()
    
    #############################################
    # List of the percentage of duration of each voice subtitle.
    # If else, set to 0
    
    pattern = "^voice(d+(.d+))?"
    start = 0
    ult_ind = 0
    percentage_duration_list = []
    for count,sub in enumerate(acc_subs):
        match = re.search(pattern, sub.text)
        if match:
            flag_voice = 0
            for i in range(ult_ind, len(voice_else_subs)):
                if voice_else_subs[i].text == "voice":
                    percentage_duration_list.append(voice_else_subs[i].duration/sub.duration)
                    flag_voice = 1
                    ult_ind = i+1
                elif flag_voice:
                    ult_ind = i+1
                    break
        else:
            percentage_duration_list.append(1)

    #############################################
    # Time correction of voice_else_subs
    # The start and end times are corrected to the new duration, the accelerated times
    
    # pattern = "^voice(d+(.d+))?"
    start = 0
    ult_ind = 0
    for count,sub in enumerate(acc_subs):
        # duration_original = sub.duration
        duration_speedup = mp4_duration(f"{count+1}.ts")*1000*percentage_duration_list[ult_ind]/reduction_factor
        accelerated_voice_else_subs[ult_ind].start = start
        accelerated_voice_else_subs[ult_ind].end = start + duration_speedup
        start += duration_speedup
        
        if percentage_duration_list[ult_ind] != 1:
           while percentage_duration_list[ult_ind+1] != 1 and ult_ind < len(percentage_duration_list):
               ult_ind += 1
               duration_speedup = mp4_duration(f"{count+1}.ts")*1000*percentage_duration_list[ult_ind]/reduction_factor
               accelerated_voice_else_subs[ult_ind].start = start
               accelerated_voice_else_subs[ult_ind].end = start + duration_speedup
               start += duration_speedup
       
        ult_ind += 1
    
    #############################################
    # Keep voice only
    # Remove the else subtitles from the final file
    
    elsepattern = "^else"
    list_voiceelse_subs_filtered = [sub for sub in accelerated_voice_else_subs if not re.search(elsepattern, sub.text)]
    
    accelerated_subs = pysubs2.SSAFile()
    
    for sub in list_voiceelse_subs_filtered:
        accelerated_subs.append(sub)
        
    for count, sub in enumerate(accelerated_subs):
        sub.text = srt_subs[count].text
    
    accelerated_subs.save(new_name)
    
    return 1