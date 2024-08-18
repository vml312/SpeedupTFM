"""
Analysis of the subtitle file

With the subtitle file resulting from the inaSpeechSegmenter analysis or with the subtitle file entered (depending on the option chosen), the subtitle file is checked for errors and 
a new srt file is created (with the format of the speech or non-speech subtitles (voice or else)).

The first phase is to fill the new file, if there are subtitles in a time period, the interval is created with the 'speech' tag. On the other hand, if there are no subtitles in the 
interval, the 'no speech' tag is assigned. This is done in the file ''voice-else_subs.srt''.
If in the 'speech' to 'non-speech' transition, the 'non-speech' interval lasts less than one second, it is not separated, it remains as 'speech'.

The second phase compresses this file, joining the consecutive speech and non-speech fragments, generating the file ''compr_subs.srt''.

Finally, the total number of fragments to be generated is determined and this value is returned.
"""

import os
import re
import pysrt

## Subtitles are grouped together if they are separated by less than this value (seconds)
# It is the maximum difference between subtitles without being grouped together (seconds)
N_SEGS_THRESHOLD = 1 

##
# @brief Function that applies correction logic for n_segs_threshold.
# @param n_segs_threshold: The maximum difference between subtitles without being grouped together in seconds.
##
def correct_segs_threshold(n_segs_threshold):
    try:
        n_segs_threshold = float(n_segs_threshold)
    except:
        print(f"n_segs_threshold is not a float number. Now n_segs_threshold: {N_SEGS_THRESHOLD} seconds")
        n_segs_threshold = N_SEGS_THRESHOLD
        
    if not (N_SEGS_THRESHOLD/4) <= n_segs_threshold <= (N_SEGS_THRESHOLD*2):
        print(f"n_segs_threshold is not in the recommended range [{N_SEGS_THRESHOLD/2} {N_SEGS_THRESHOLD*2}].")
    return n_segs_threshold

##
# @brief  Fills the new subtitle file with the speech and non-speech subtitles.
# @param file_name   The name of the subtitle file.
# @param n_segs_threshold   The maximum difference between subtitles without being grouped together in seconds.
##
def fill_srt(file_name, n_segs_threshold):
    subs = pysrt.open(file_name)
    try:
        file = open("kframes.txt", "r")
    except FileNotFoundError:
        print("File not found")
    line = file.readline()
    firstkframe = float(line.split(",")[0])
        
    last_hour = int(firstkframe / 3600)
    last_minutes = int((float(firstkframe / 3600) - last_hour) * 60)
    last_seconds = ((float(firstkframe / 3600) - last_hour) * 60 - last_minutes) * 60
    last_end = [int(last_hour), int(last_minutes), float(last_seconds)]  # h/min/s

    index = 1
    with open("voice-else_subs.srt", 'w') as output:
        for sub in subs:
            content = str(sub)
            content = content.splitlines()

            start_h = int(re.findall(r'(\d+\d+):', content[1])[0])
            start_min = int(re.findall(r':(\d+\d+):', content[1])[0])
            start_s = re.findall(r':(\d+\d+,\d+\d+\d+)', content[1])[0]
            start_s = float(start_s.replace(',', '.'))

            end_h = int(re.findall(r'(\d+\d+):', content[1])[2])
            end_min = int(re.findall(r':(\d+\d+):', content[1])[1])
            end_s = re.findall(r':(\d+\d+,\d+\d+\d+)', content[1])[1]
            end_s = float(end_s.replace(',', '.'))

            current_start = [start_h, start_min, start_s]
            current_end = [end_h, end_min, end_s]

            if current_start == last_end:
                output.write(str(index) + '\n' + content[1] + '\n' + "voice" + '\n\n')
                index += 1
                last_end = current_end
            else:
                # we have a gap between last end and current start => if the gap is longer than  %n_segs_threshold% seconds => separate it
                gap_duration = (start_h * 3600 + start_min * 60 + start_s) - (last_end[0] * 3600 + last_end[1] * 60 +
                                                                              last_end[2])
                if gap_duration > n_segs_threshold:
                    seconds1 = "{:06.3f}".format(last_end[2]).replace('.', ',')
                    seconds2 = "{:06.3f}".format(current_start[2]).replace('.', ',')
                    new_content = f'{last_end[0]:02}:{last_end[1]:02}:{seconds1} --> {current_start[0]:02}:{current_start[1]:02}:{seconds2}'
                    output.write(str(index) + '\n' + new_content + '\n' + "else" + '\n\n')
                    index += 1
                    # after writing the gap info, we'll also write the current object
                    output.write(str(index) + '\n' + content[1] + '\n' + "voice" + '\n\n')
                    index += 1
                    last_end = current_end

                else:
                    # special case for first subtitle
                    if current_start == [0, 0, 0]:
                        if current_end[0] <= last_end[0] and current_end[1] <= last_end[1] and current_end[2] <= \
                                last_end[2]:
                            print("end time < start time -> this output was eliminated and replaced")
                    else:
                        seconds1 = "{:06.3f}".format(last_end[2]).replace('.', ',')
                        seconds2 = "{:06.3f}".format(current_end[2]).replace('.', ',')
                        new_content = f'{last_end[0]:02}:{last_end[1]:02}:{seconds1} --> {current_end[0]:02}:{current_end[1]:02}:{seconds2}'
                        output.write(str(index) + '\n' + new_content + '\n' + "voice" + '\n\n')
                        index += 1
                        last_end = current_end

    # for the last fragment - final index  
    with open('kframes.txt', 'r') as f:
        last_line = f.readlines()[-1]
    lastkeyframe = float(last_line.split(",")[0])

    final_hour = int(lastkeyframe / 3600)
    final_minutes = int((float(lastkeyframe / 3600) - final_hour) * 60)
    final_seconds = ((float(lastkeyframe / 3600) - final_hour) * 60 - final_minutes) * 60
    final_time = [int(final_hour), int(final_minutes), float(final_seconds)]  # h/min/s
    if last_end != final_time:
        with open("voice-else_subs.srt", 'a') as output:
            seconds1 = "{:06.3f}".format(last_end[2]).replace('.', ',')
            seconds2 = "{:06.3f}".format(final_time[2]).replace('.', ',')
            new_content = f'{last_end[0]:02}:{last_end[1]:02}:{seconds1} --> {final_time[0]:02}:{final_time[1]:02}:{seconds2}'
            output.write(str(index) + '\n' + new_content + '\n' + "else" + '\n\n')
    index += 1

    return

##
# @brief  Compresses the subtitle file by merging together all consecutive voice subs.
# @param file_name   The name of the subtitle file.
##
def compress_srt(file_name):
    subs = pysrt.open(file_name)
    current_start = 0
    current_end = 0
    current_text = ""
    current_index = 0

    with open("compr_subs.srt", "w") as output_file:
        for sub in subs:
            if sub.text == current_text:
                current_end = sub.end
            else:
                if current_end != 0:
                    output_file.write(f"{current_index}\n")
                    output_file.write(f"{current_start} --> {current_end}\n")
                    output_file.write(f"{current_text}\n\n")
                current_start = sub.start
                current_end = sub.end
                current_text = sub.text
                current_index += 1

        if current_start != 0:
            output_file.write(f"{current_index}\n")
            output_file.write(f"{current_start} --> {current_end}\n")
            output_file.write(f"{current_text}\n\n")

    return

##
# @brief  Determines the total number of fragments to be generated.
# @param srt_file   The name of the subtitle file.
# @return  The total number of fragments to be generated.
##
def determine_index(srt_file):
    subs = pysrt.open(srt_file)
    index = len(subs)

    return index

##
# @brief  Main function.
# @param input_path   The path where the files are stored.
# @param main_path   The working directory path at the end of the process.
# @param srt_file   The name of the subtitle file.
# @param n_segs_threshold   The maximum difference between subtitles without being grouped together in seconds.
##
def main(input_path, main_path, srt_file, n_segs_threshold):

    os.chdir(input_path)

    # check if the parameter %n_segs_threshold% is correct
    n_segs_threshold = correct_segs_threshold(n_segs_threshold)
    
    # else-voice_subs.srt will contain the subtitles simplified to "voice" (for fragments with subs) and else (for fragments w/out subs, larger than 1s)
    fill_srt(srt_file, n_segs_threshold)
    srt_file = "voice-else_subs.srt"

    # compr_subs.srt will reduce the number of subtitles by merging together all consecutive voice subs
    compress_srt(srt_file)
    srt_file = "compr_subs.srt"

    # determine the total nr of fragments to be generated
    index = determine_index(srt_file)
    print("total nr of fragments to be generated: ", index)

    os.chdir(main_path)

    return n_segs_threshold
