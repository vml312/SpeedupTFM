"""
Joining the fragments to create the accelerated product

In this file, the first thing that is done is to transform all the fragments to MPEG-TS format ((Transport Stream) = a container format used for streaming media), it is a format 
used for live content, so a text file is created with all the consecutive fragments in order of the type '.ts' in the file concat.txt. 

With this file the final file is created, concatenating all these files.
"""

import os
import subprocess
import pysubs2

##
# @brief  Determines the total number of fragments to be generated.
# @param srt_file   The name of the subtitle file.
# @return  The total number of fragments to be generated.
##
def determine_index(srt_file):
    subs = pysubs2.load(srt_file, encoding = 'UTF-8', format_= 'srt')
    index = len(subs)
    return index

##
# @brief  Creates the final video file.
# @param index   The total number of fragments to be generated.
# @param current_path   The path where the files are stored.
##
def movie_maker(index, current_path):
    video_list = [f"{i}.mp4" for i in range(1, int(index) + 1)]
    temp_file_list = []
    concat_txt = os.path.join(current_path, 'concat.txt')

    with open(concat_txt, 'w') as output:
        for video in video_list:
            temp_file = os.path.join(current_path,
                                     f"{video[:-4]}.ts")  # [:-4] - to remove the last four characters from "video"
            terminalText=subprocess.run(
                ['ffmpeg', '-y', '-i', video, '-c', 'copy', '-bsf:v', 'h264_mp4toannexb', '-f', 'mpegts', temp_file], capture_output=True, text=True)
            # -bsf:v h264_mp4toannexb -> converts the video stream to the Annex B byte stream format required for MPEG-TS containers
            # -f mpegts -> set the output format to MPEG-TS (Transport Stream) = a container format used for streaming media
            if not os.path.isfile(temp_file):
                print("error executing "+str(['ffmpeg', '-y', '-i', video, '-c', 'copy', '-bsf:v', 'h264_mp4toannexb', '-f', 'mpegts', temp_file]))
                print(terminalText.stderr)
            else:            
                temp_file_list.append(temp_file)
                output.write(f"file '{temp_file}'\n")
    
    output_file = os.path.join(current_path, 'merged_video.mp4')
    textTerminal=subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_txt, '-c:a', 'copy', '-bsf:a', 'aac_adtstoasc', output_file], capture_output=True, text=True)
    if textTerminal.returncode != 0:     
        print(str(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_txt, '-c:a', 'copy', '-bsf:a','aac_adtstoasc', output_file])+" "+textTerminal.stderr)
    # '-bsf:a', 'aac_adtstoasc' -> bitstream filter, converts the audio stream to the ASC (Audio Specific Configuration) format required for MPEG-TS containers
    return

##
# @brief  Main function.
# @param input_path   The path where the files are stored.
# @param srt_file   The name of the subtitle file.
##
def main(input_path, srt_file):
    os.chdir(input_path)
    index = determine_index(srt_file)
    movie_maker(index, input_path)
    return