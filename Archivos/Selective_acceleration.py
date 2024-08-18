"""
Selective acceleration of fragments

In this program, for each file in the split of the complete file, the ''speedup'' program is called for each one, in order to accelerate that video with the acceleration 
corresponding to that fragment.

The file ''compr_subs.srt'' is used, it is the subtitle file that contains 'else' or 'voice', it does not have consecutive elements of the same type. For each file the 
speedup program is called for each file with the following arguments: directories, index and acceleration factor corresponding to its type.

The acceleration is extracted from the file name, because the names are those mentioned in the previous process ''(\d+)else(\d.\d+)'' or ''(\d+)voice(\d.\d+)''.
"""

import os
import shutil
import pysubs2
import re

##
# @brief  Determines the total number of fragments to be generated.
# @param voice_else_srt   The name of the subtitle file.
# @return  The total number of fragments to be generated.
##
def determine_index(voice_else_srt):
    subs = pysubs2.load(voice_else_srt, encoding = 'UTF-8', format_= 'srt')
    index = len(subs)
    return index

##
# @brief  Determines the acceleration of the file in the directory that matches the name and renames the file from ''(\d+)else(\d.\d+)'' or ''(\d+)voice(\d.\d+)''
# to ''(\d+)elseacc'' or ''(\d+)voiceacc''.
# @param name   The name of the file to be found.
# @param lista   The list of files in the directory.
# @return  The name of the file that matches the name.
##
def file_in_directory(name, lista):
    pattern = f"^{name}(\d+(\.\d+)?)\.mp4"
    for file in lista:
        match = re.search(pattern, file)
        if match is not None:
            new_name = name+"acc.mp4"
            os.rename(file, new_name)
            return new_name, float(match.group(1))
    return

##
# @brief  Selectively accelerates the fragments with acceleration found in ''(\d+)else(\d.\d+)'' or ''(\d+)voice(\d.\d+)'' where (\d.\d+) is the acceleration.
# @param speedup_path   The path where the files are stored.
# @param input_path   The path where the files are stored.
# @param index   The total number of fragments to be generated.
##
def selective_acc(speedup_path, input_path, index):
    # after the .mp4 files are created, the ones named {index}voice will have acc_rate = voice_speed and {index}else -> else_speed
    current_file = ""
    current_speed = -1
    os.chdir(input_path)
    files = os.listdir()

    for i in range(1, int(index) + 1):
        
        retVal_else = file_in_directory(f'{i}else', files)
        retVal_voice = file_in_directory(f'{i}voice', files)
        
        if retVal_else:
            current_file, current_speed = retVal_else
            
        elif retVal_voice:
            current_file, current_speed = retVal_voice

        else:
            print(i)
            raise Exception("\n--------Non-existent file--------\n")

        if current_file != "" and current_speed != -1:
            speedup_file(speedup_path, input_path, current_file, current_speed, f'{i}.mp4')
            
    return 1

##
# @brief  Accelerates the file with the speedup program.
# @param speedup_path   The path where the files are processed.
# @param current_path   The path where the files are stored.
# @param file_name   The name of the file to be accelerated.
# @param speed_rate   The acceleration factor.
# @param output_name   The name of the output file.
##
def speedup_file(speedup_path, current_path, file_name, speed_rate, output_name):
    shutil.copyfile(os.path.join(current_path, file_name), os.path.join(speedup_path, file_name))
    new_content = f"PATH={os.path.join(speedup_path, file_name)}\nOPTION=speed\nSPEED={speed_rate}\nLENGTH=3\n"
    os.chdir(speedup_path)
    with open("configurationSpeed.txt", 'w') as file:
        file.write(new_content)
    import speedup
    speedup.main()

    try:
        os.rename('finalRESULT.mkv', output_name)
        shutil.move(os.path.join(speedup_path, output_name), os.path.join(current_path, output_name))
    except FileNotFoundError:
        print(f"File not found finalRESULT.mkv {output_name}")
    except Exception as e:
        print(f"{e}: Error reading file")

    try:
        if os.path.exists(os.path.join(speedup_path, file_name)):
            os.remove(file_name)  # from root path
    except FileNotFoundError:
        print(f"File not found {file_name}")
        
    os.chdir(current_path)

    return 1

##
# @brief  Main function.
# @param main_path   The working directory path at the end of the process.
# @param input_path   The path where the files are stored.
# @param voice_else_srt   The name of the subtitle file.
##
def main(main_path, input_path, voice_else_srt):
    
    os.chdir(input_path)
    index = determine_index(voice_else_srt)
    selective_acc(main_path, input_path, index)
    
    return 1