"""
Obtaining results of male and female speech duration (OPTIONAL)

With the results of the inaSpeechSegmenter you can determine the percentage of 'male' and 'female' labels obtained by the recogniser.
"""

import os
import re
import shutil

from inaAnalysis import extract_statistics

##
# @brief  Extracts the duration of the film for female label, male label and non speech label (else).
# @param movie_name   The name of the movie.
# @return The duration of the voice part
# @return The duration of the non-speech part
# @return The duration of the female voice part
##
def extract_times(movie_name):
    duration_female = 0
    duration_voice = 0
    duration_else = 0
    # print('\nLabels and lengths of speaking fragments from:\n', movie_name, '\n')

    with open("VoiceElseDuration_before_after.txt", 'a') as output:
        output.write(f'Labels and lengths of speaking fragments from: {movie_name}\n')
        with open(f'inaSpeech_results_{movie_name[:-4]}.txt', 'r') as input:
            for line in input:
                start_time, end_time = tuple(re.findall(r'\d+\.\d*', line))
                duration = float(end_time) - float(start_time)
                if 'male' in line.strip() or 'female' in line.strip():
                    duration_voice += duration
                    if 'female' in line.strip():
                        duration_female += duration
                        # print("female: ", duration)
                        output.write(f"female: {duration}\n")
                    else:
                        # print("male: ", duration)
                        output.write(f"male: {duration}\n")
                else:
                    duration_else += duration
                    # print("else: ", duration)
                    output.write(f"else: {duration}\n")

    return duration_voice, duration_else, duration_female

##
# @brief Main function of the script, which extracts the statistics from the srt file generated by inaSpeechSegmenter from original movie and from summarized movie.
# The results are stored in the file VoiceElseDuration_before_after.txt.
# @param input_path   The path where the video is stored.
# @param movie_name   The name of the video file.
##
def main(input_path, movie_name):

    os.chdir(input_path)
    
    if not os.path.exists(os.path.join(input_path, "inaSpeech_results.txt")):
        extract_statistics(input_path, movie_name)
    os.rename(os.path.join(input_path, "inaSpeech_results.txt"),
              os.path.join(input_path, f'inaSpeech_results_{movie_name[:-4]}.txt'))
    
    extract_statistics(input_path, "merged_video.mp4")
    os.rename(os.path.join(input_path, "inaSpeech_results.txt"),
              os.path.join(input_path, "inaSpeech_results_merged_video.txt"))
    os.remove('inaSpeech_subs.srt')

    with open("VoiceElseDuration_before_after.txt", 'w') as output:
        output.write("")

    with open("VoiceElseDuration_before_after.txt", 'a') as output:
        original_times = tuple(extract_times(movie_name))
        to_print = f'\nOriginal movie (input = {movie_name}):\nvoice time = {original_times[0]}\nelse time = {original_times[1]}\nfemale time = {original_times[2]}\nmale time = {float(original_times[0]) - float(original_times[2])}'
        output.write(to_print)
        print(to_print)

        merged_times = tuple(extract_times("merged_video.mp4"))
        to_print = f'\n\nSummarized movie (output = merged_video.mp4): \nvoice time = {merged_times[0]} \nelse time = {merged_times[1]} \nfemale time = {merged_times[2]} \nmale time = {float(merged_times[0]) - float(merged_times[2])}'
        output.write(to_print)
        print(to_print)

    folder_name = "inaSpeechSegmenter_voice_else_analysis"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    new_path = os.path.join(input_path, folder_name)
    if os.path.exists(os.path.join(input_path, "inaSpeech_results_merged_video.txt")):
        shutil.move(os.path.join(input_path, "inaSpeech_results_merged_video.txt"), os.path.join(new_path, "inaSpeech_results_merged_video.txt"))
    if os.path.exists(os.path.join(input_path, f'inaSpeech_results_{movie_name[:-4]}.txt')):
        shutil.move(os.path.join(input_path, f'inaSpeech_results_{movie_name[:-4]}.txt'), os.path.join(new_path, f'inaSpeech_results_{movie_name[:-4]}.txt'))
    if os.path.exists(os.path.join(input_path, "VoiceElseDuration_before_after.txt")):
        shutil.move(os.path.join(input_path, "VoiceElseDuration_before_after.txt"), os.path.join(new_path, "VoiceElseDuration_before_after.txt"))

