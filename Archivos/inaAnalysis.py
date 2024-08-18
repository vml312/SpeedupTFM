"""
Analysis of InaSpeechSegmenter

This model returns at each video instant a tag among the following: 'noEnergy', 'male', 'female', 'noise', 'music'.

A text file is created with the results (inaSpeech_results.txt) and then a subtitle file is created with the above text and the appropriate format (inaSpeech_subs.srt).

An srt file is created with the determined speech/non-speech results and the process continues.

"""

import os
from inaSpeechSegmenter import Segmenter

##
# @brief  Extracts the statistics from the input video.
# @param movie_path   The path where the video is stored.
# @param file_name   The name of the video file.
##
def extract_statistics(movie_path, file_name):

    input_path = os.path.join(movie_path, file_name)
    seg = Segmenter()
    total_segmentation = seg(input_path)

    with open(os.path.join(movie_path, "inaSpeech_results.txt"), "w") as file:
        for input_det in total_segmentation:
            label, start_time, end_time = input_det
            line = f"{label}: {start_time} --> {end_time}"
            file.write(line + '\n')

    index = 0
    with open(os.path.join(movie_path, "inaSpeech_subs.srt"), "w") as file:
        for input_det in total_segmentation:
            label, start_time, end_time = input_det
            if 'male' in label.strip():
                text = label

                hour = int(start_time / 3600)
                minutes = int((float(start_time / 3600) - hour) * 60)
                seconds = ((float(start_time / 3600) - hour) * 60 - minutes) * 60
                seconds = "{:06.3f}".format(seconds)
                start = f'{hour:02}:{minutes:02}:{seconds}'.replace('.', ',')

                hour = int(end_time / 3600)
                minutes = int((float(end_time / 3600) - hour) * 60)
                seconds = ((float(end_time / 3600) - hour) * 60 - minutes) * 60
                seconds = "{:06.3f}".format(seconds)
                end = f'{hour:02}:{minutes:02}:{seconds}'.replace('.', ',')

                index += 1
                line = f"{index}\n{start} --> {end}\n{text}\n"
                file.write(line + '\n')
    return

##
# @brief Main function of the script.
# @param movie_path   The path where the video is stored.
# @param movie_name   The name of the video file.
##
def main(movie_path, movie_name):
    extract_statistics(movie_path, movie_name)
