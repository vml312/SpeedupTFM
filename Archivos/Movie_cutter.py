"""
Splitting the file into speech/non-speech fragments

With the subtitle file generated by Format_srt, a copy of the original film is created, transforming all the frames into keyframes, thus splitting the film according to the 
separations defined in the srt file.

In the total process this program will be executed twice, the first time it will cut the ''non-speech'' fragments of the film according to the original srt, as the speech fragments 
are not necessary because the others are going to be analysed to make more divisions in these if necessary.

Then, from this copy, all partitions in transitions between speech and non-speech intervals are made in one file (''splitmovie.bat'').
"""

import os
import subprocess
import pysrt

##
# @brief Splits the video file into fragments.
# @param movie_path   The path where the video is stored.
# @param movie_name   The name of the video file.
# @param srt_file   The name of the subtitle file.
# @param flag_only_else   Flag to determine if only the speech fragments are kept.
##
def fragmentation(movie_path, movie_name, srt_file, flag_only_else, flag_podcast):
    # inputs: file containing the desired timestamps of the fragments, srt format
    os.chdir(movie_path)
    
    if not flag_podcast:
        ##### make a copy of the original movie where all frames become keyframes
        allkframes = 'output_with_all_keyframes.mkv'
    else:
        allkframes = movie_name
    
    if not os.path.exists(os.path.join(movie_path, allkframes)):
        command = f'ffmpeg -y -i {movie_name} -c:v libx264 -x264opts keyint=1:no-scenecut -crf 18 -c:a aac {allkframes}'
        with open('ffmpeg_command.bat', 'w') as bat_file:
            bat_file.write(command)
        subprocess.call(['ffmpeg_command.bat'], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print(f"{allkframes} already exists")
        
    with open("splitmovie.bat", 'w') as output:
        try:
            subs = pysrt.open(srt_file)
            for sub in subs:
                if flag_only_else:
                    if sub.text != "voice":
                        start_point = sub.start.hours * 3600 + sub.start.minutes * 60 + sub.start.seconds + round(sub.start.milliseconds/1000,3)  # in seconds for ffmpeg
                        end_point = sub.end.hours * 3600 + sub.end.minutes * 60 + sub.end.seconds + round(sub.end.milliseconds/1000,3)
                        output.write(f'ffmpeg -y -i {allkframes} -ss {start_point} -to {end_point} -c copy {sub.index}{sub.text}.mp4\n')
                else:
                    start_point = sub.start.hours * 3600 + sub.start.minutes * 60 + sub.start.seconds + round(sub.start.milliseconds/1000,3)  # in seconds for ffmpeg
                    end_point = sub.end.hours * 3600 + sub.end.minutes * 60 + sub.end.seconds + round(sub.end.milliseconds/1000,3)
                    output.write(f'ffmpeg -y -i {allkframes} -ss {start_point} -to {end_point} -c copy {sub.index}{sub.text}.mp4\n')

        except FileNotFoundError:
            print("File not found")

    batpath = os.path.join(movie_path, "splitmovie.bat")
    subprocess.call(batpath, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) #need to run it through the Windows command interpreter (cmd.exe) because win32 cannot execute it directly
    #/c tells the program to open cmd.exe and close it after the command from splitmovie.bat is ran

    return

## 
# @brief Main function.
# @param movie_path   The path where the video is stored.
# @param movie_name   The name of the video file.
# @param srt_file   The name of the subtitle file.
# @param flag_only_else   Flag to determine if only the speech fragments are kept.
##
def main(movie_path, movie_name, srt_file, flag_only_else, flag_podcast):
    fragmentation(movie_path, movie_name, srt_file, flag_only_else, flag_podcast)

