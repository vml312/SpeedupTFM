 #!/usr/bin/env python -W ignore::DeprecationWarning
"""
Main script of the processing. It calls all the functions in the correct sequence to generate the movie accelerated.
It is usually called from a batch file and reads the arguments from configfile.txt and from the command line.
"""

import os
import sys
import re
import shutil
import subprocess
import time
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
# @brief  Generates a mp4 file from a mp3 file by creating a black screen with the same duration as the mp3 file.
# Then, the kframes.txt file is created with the start time and the end time, so it has the same format as if it was the result of the frame detection of a real mp4 file.
# @param folder_path   The path where the mp3 file is stored.
# @param movie_name   The name of the mp3 file.
##
def generate_mp4_from_mp3(folder_path, movie_name):
    with open(os.path.join(folder_path, "mp3tomp4.bat"), 'w') as output:
        new_movie_name = movie_name[:-4] + ".mp4"
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
             movie_name], capture_output=True, text=True)
        duration = float(result.stdout.strip())
        mp3tomp4_str = f"ffmpeg -f lavfi -i color=c=black:s=1280x720:r=1 -i {movie_name} -c:v libx264 -crf 0 -c:a copy -t {duration} -shortest {new_movie_name}"
        output.write(mp3tomp4_str)
    subprocess.call([os.path.join(folder_path, 'mp3tomp4.bat')], shell=True)
    with open(os.path.join(folder_path, "kframes.txt"), 'w') as output:
        output.write("0.000000,K_\n")
        output.write(f"{duration},K_\n")
    return

## 
# @brief  Script to detect all the frames of the movie. The times of the frames are stored in a file called "frames.txt". 
# @param folder_path   The path where the movie is stored.
# @param movie_name   The name of the movie.
##
def frame_detection(folder_path, movie_name):
    with open(os.path.join(folder_path, "framedetection.bat"), 'w') as output:
        output.write(
            f'ffprobe -loglevel error -select_streams v:0 -show_entries packet=pts_time,flags -of csv=print_section=0 {os.path.join(folder_path, movie_name)}\n')

    batpath = os.path.join(folder_path, "framedetection.bat")
    f = open(os.path.join(folder_path, "frames.txt"), 'w')
    subprocess.call([f'{batpath}'], stdout=f)

    with open(os.path.join(folder_path, "frames.txt"), 'r') as inputl:
        with open(os.path.join(folder_path, "kframes.txt"), 'w') as output:
            for line in inputl:
                if "K" in line.strip("\n"):
                    output.write(line)
                    
    return 

##
# @brief Main script of the processing. It calls all the functions in the correct sequence to generate the movie accelerated.
# It is usually called from a batch file and reads the arguments from configfile.txt and from the command line.
##
def main():
    with open("configfile.txt", 'r', encoding='utf8', newline='\r\n') as file:
        initial_content = file.read()
    content_lines = initial_content.splitlines()
    content_lines = "\n".join(content_lines)

    with open("configfile.txt", 'r', encoding='utf8', newline='\r\n') as file:
        data = []
        lines = file.read().splitlines()
        for line in lines:
            if line.startswith('#') or not line.strip():
                continue
            data.append(line.split("=")[1])
            
        input_path = data[0]
        main_path = data[1]
        movie_name = data[2]
        target_min_speed = data[3]
        target_max_speed = data[4]
        acc_voice_max=data[5]
        acc_voice_min=data[6]
        acc_motion_max=data[7]
        acc_motion_min=data[8]
        min_video_duration=data[9]
        min_acc_scene_duration=data[10]
        n_segs_threshold=data[11]

    if len(sys.argv) == 2:
        original_title = str(sys.argv[1]) 
    else:
        original_title = movie_name[:-4]
        
    reference = input(
        "Choose the desired reference for splitting the movie:\n inaSpeechSegmenter results (type ina) of subtitle file (type srt): ")
    if reference != 'srt' and reference != 'ina':
        raise Exception("Invalid input - reference choice")
    
    # Detection of podcast and if it is, change of the podcast flag to True
    flag_podcast = False
    
    if re.search(r'(\w+\.(?:mp3|m4a|wav|flac|aac|ogg|wma|alac|aiff|ape|opus))', movie_name):
        flag_podcast = not flag_podcast
        
    # First step either for mp3 or mp4 files provided
    if flag_podcast:
        print("\nBeginning processing of the mp3 file provided.\n")
        generate_mp4_from_mp3(input_path, os.path.join(input_path, movie_name))
    else:
        print("\nBeginning processing of the mp4 file provided.\n")
        frame_detection(input_path, os.path.join(input_path, movie_name))

    # Variable to count the steps completed
    n_step = 1    

    if reference == 'srt':
        srt_file='pelicula.srt'
#        srt_file = input("Provide the .srt track and enter its name or provide a video with one track - the program will automatically substract it\nEnter the name of the srt file or - : ")
        if len(re.findall(r'(\w+).srt', os.path.join(input_path, srt_file))) == 0 and srt_file != '-':
            raise Exception("Invalid input - srt choice")
        if srt_file == '-':
            # in this case, we'll find the sub track with ffmpeg
            subprocess.run(['ffmpeg', '-i', os.path.join(input_path, movie_name), '-map', '0:s:0', os.path.join(input_path, 'subs.srt')])
            srt_file = os.path.join(input_path, 'subs.srt')

    elif reference == 'ina':
        import inaAnalysis
        print('In this case, an analysis based on the inaSpeechSegmenter will be performed to detect the fragments with noise/music/silence and voice content')
        try:
            result = inaAnalysis.main(input_path, movie_name)
            print("Script output:", result)
        except Exception as e:
            print("An error occurred:", e)

        # in the srt format, the male/female lines are reduced to voice, and noise/music/silence to else
        srt_file = 'inaSpeech_subs.srt'
        print(f"\n------- Step {n_step}: choosing reference and generating srt files --> COMPLETE ------\n")
        n_step+=1
    
    
    start_time = time.time()
    import Format_srt
    #format the srt file (original subs or ina srt output) into a simplified version
    try:
        n_segs_threshold = Format_srt.main(input_path, main_path, srt_file, n_segs_threshold)
    except Exception as e:
        print("An error occurred:", e)
    
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Format_srt execution time: {execution_time} seconds")
    print(f"\n------- Step {n_step}: formatting the srt file provided/generated into a simplified version --> COMPLETE ------\n")
    n_step+=1
    
    if not flag_podcast:
        ####### movie fragmentation into else fragments #########
        start_time = time.time()
        os.chdir(main_path)
        # cut the movie into fragments following the timemap provided in the reference srt file "srt_file"
        import Movie_cutter
        try:
            Movie_cutter.main(input_path, movie_name, "compr_subs.srt", True, flag_podcast) #Only else fragments are cut
        except Exception as e:
            print("An error occurred:", e)
            
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Movie_cutter execution time: {execution_time} seconds")
        print(f"\n------- Step {n_step}: cutting the movie into else mp4 fragments --> COMPLETE ------\n")
        n_step+=1
        
    os.chdir(main_path)
    start_time = time.time()
    import accelCalculator
    try:
        os.chdir(input_path)
        target_min_speed, target_max_speed = accelCalculator.main(input_path, "compr_subs.srt", srt_file, target_min_speed, 
                                                                  target_max_speed, reference, acc_voice_max, acc_voice_min, 
                                                                  acc_motion_min, acc_motion_max, min_acc_scene_duration, 
                                                                  min_video_duration, n_segs_threshold, flag_podcast)
    except Exception as e:
        print("An error occurred:", e)
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"accelCalculator execution time: {execution_time} seconds")
    print(f"\n------- Step {n_step}: determining accelerations of voice/else fragments --> COMPLETE ------\n")
    n_step+=1
    
    ####### movie fragmentation into voice/else fragments with acceleration #########
    start_time = time.time()
    os.chdir(main_path)
    # cut the movie into fragments following the timemap provided in the srt file "compr_subs.srt"
    import Movie_cutter
    try:
        Movie_cutter.main(input_path, movie_name, "compr_subs_acc.srt", False, flag_podcast)
    except Exception as e:
        print("An error occurred:", e)
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Movie_cutter execution time: {execution_time} seconds")
    print(f"\n------- Step {n_step}: cutting the movie into voice/else mp4 fragments --> COMPLETE ------\n")
    n_step+=1
    
    ######## selective acceleration of movie fragments #######
    start_time = time.time()
    os.chdir(main_path)
    # accelerate the movie fragments with different speeds (one for voice content, one for gaps between lines)
    import Selective_acceleration
    try:
        Selective_acceleration.main(main_path, input_path, "compr_subs_acc.srt")
    except Exception as e:
        print("An error occurred:", e)
        exit()
        
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Selective_acceleration execution time: {execution_time} seconds")
    print(f"\n------- Step {n_step}: selective acceleration of voice/else mp4 files --> COMPLETE ------\n")
    n_step+=1

    ####### movie maker #######
    start_time = time.time()
    os.chdir(main_path)
    # merge the {index}.mp4 fragments into one final movie
    import Movie_maker
    try:
        Movie_maker.main(input_path, "compr_subs_acc.srt")
    except Exception as e:
        print("An error occurred:", e)
    
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Movie_maker execution time: {execution_time} seconds")
    print(f"\n------- Step {n_step}: putting together the accelerated mp4 files to create the summarized movie --> COMPLETE ------\n")
    n_step+=1
    
    ########speedup the summarized movie to fit the desired length#######
    os.chdir(input_path)
    sp_movie = 'merged_video.mp4'
    old_duration = subprocess.run(
       ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
        sp_movie], capture_output=True, text=True)
    old_duration = float(old_duration.stdout.strip())
    old_h = int(old_duration / 3600)
    old_min = int((float(old_duration / 3600) - old_h) * 60)
    old_s = ((float(old_duration / 3600) - old_h) * 60 - old_min) * 60
    print(f"Current duration: {old_h} hours, {old_min} minutes and {old_s} seconds")
    speedup = input("If you are not pleased with the final length of the movie, insert here the desired duration in the following format: hh:mm:ss.ms (3 decimals for ms)\nOtherwise, press any key: ")
    new_duration =0
    if len(speedup) > 11:
        h = int(re.findall(r'(\d+\d+):', speedup)[0])
        mins = int(re.findall(r':(\d+\d+):', speedup)[0])
        s = float(re.findall(r':(\d+\d+.\d+\d+\d+)', speedup)[0])
        new_duration = round(h*60 + mins + s/60, 3)   #in minutes, required by the config file of the speedup.py program
        print("Desired duration [minutes]: ", new_duration)
        
        shutil.copyfile(os.path.join(input_path, sp_movie), os.path.join(main_path, sp_movie))
        os.chdir(main_path)
        new_content = f"PATH={os.path.join(main_path, sp_movie)}\nOPTION=length\nSPEED=1\nLENGTH={new_duration}\n"
        with open("configurationSpeed.txt", 'w') as file:
            file.write(new_content)
        
        import speedup
        speedup.main()

        try:
            if os.path.exists(os.path.join(main_path, 'finalRESULT.mkv')):
                os.rename('finalRESULT.mkv', f'compressedin_{new_duration}min.mp4')
                shutil.move(os.path.join(main_path, f'compressedin_{new_duration}min.mp4'), os.path.join(input_path, f'compressedin_{new_duration}min.mp4'))
        except FileNotFoundError as e:
            print(f"File not found: {e}")
        except Exception as e:
            print(f"Error reading file_ {e}")
            
        ####### generate new subtitles for the summarized version ######
        ####### Subtitle generation of adjusted to duration video, not working properly ######
        try:
            os.chdir(main_path)
            import accelerate_srt
            start_time = time.time()
            os.chdir(input_path)
            accelerate_srt.main(input_path, srt_file, "voice-else_subs.srt", "compr_subs_acc.srt", f'compressedin_{new_duration}min.srt', f'compressedin_{new_duration}min.mp4')
            end_time = time.time()
            execution_time = end_time - start_time
            print(f"accelerate_srt execution time: {execution_time} seconds")
            print(f"\n------- Step {n_step}: compressedin_{new_duration}min.srt acceleration completed --> COMPLETE ------\n")
            n_step+=0.1
            os.chdir(main_path)
        except Exception as e:
            print("An error occurred:", e)

        print(f"\n------- Step {n_step} - optional\nspeed-up the summarized movie to fit in a certain length --> COMPLETE ------\n")
        n_step = round(n_step+1)

    ####### generate new subtitles for the summarized version ######
    ####### Acceleration of srt file of merged_video #######
    os.chdir(main_path)
    import accelerate_srt
    
    try:
        start_time = time.time()
        os.chdir(input_path)
        accelerate_srt.main(input_path, srt_file, "voice-else_subs.srt", "compr_subs_acc.srt", "merged_video.srt", "merged_video.mp4")
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"\naccelerate_srt execution time: {execution_time} seconds")
        print(f"\n------- Step {n_step}: merged_video.srt acceleration completed --> COMPLETE ------\n")
        n_step+=1
        
        os.chdir(main_path)
    except Exception as e:
        print("An error occurred:", e)
        
    voice_else_option = input(
        "Do you want to do a voice else analysis to obtain male/female voice/else percentages with inaAnalysis? <yes> or any key: ")
    
    if voice_else_option == 'yes':
        ####### female/male screentime duration results########
        os.chdir(main_path)
        import VoiceElseDuration
        try:
            VoiceElseDuration.main(input_path, movie_name)
        except Exception as e:
            print("An error occurred:", e)
    
        print(f"\n------- Step {n_step} - female/male/else inaSpeechSegmenter analysis on both the original and summarized movie --> COMPLETE ------\n")
        n_step+=1

    ########organize used files in folders############
    os.chdir(input_path)
    folder_normal = "fragments_normalcut"
    if not os.path.exists(folder_normal):
        os.makedirs(folder_normal)
    folder_speed = "fragments_spedup"
    if not os.path.exists(folder_speed):
        os.makedirs(folder_speed)
    folder_output = "output_results"
    if not os.path.exists(folder_output):
        os.makedirs(folder_output)
    folder_bat = "batfiles"
    if not os.path.exists(folder_bat):
        os.makedirs(folder_bat)
    folder_dep = "dep_results"
    if not os.path.exists(folder_dep):
        os.makedirs(folder_dep)
    folder_normal_acc = "fragments_normalcut_acc"
    if not os.path.exists(folder_normal_acc):
        os.makedirs(folder_normal_acc)
    folder_ts = "fragments_ts"
    if not os.path.exists(folder_ts):
        os.makedirs(folder_ts)

    normal_path = os.path.join(input_path, folder_normal)
    speed_path = os.path.join(input_path, folder_speed)
    output_path = os.path.join(input_path, folder_output)
    bat_path = os.path.join(input_path, folder_bat)
    normal_acc_path = os.path.join(input_path, folder_normal_acc)
    dep_path = os.path.join(input_path, folder_dep)
    ts_path = os.path.join(input_path, folder_ts)

    index = determine_index("compr_subs_acc.srt")
    print("Number of fragments to be generated: ", index)

    try:
        for i in range(1, int(index) + 1):
            if os.path.exists(os.path.join(input_path, f'{i}else.mp4')):
                shutil.move(os.path.join(input_path, f'{i}else.mp4'), os.path.join(normal_path, f'{i}else.mp4'))
            elif os.path.exists(os.path.join(input_path, f'{i}voice.mp4')):
                shutil.move(os.path.join(input_path, f'{i}voice.mp4'), os.path.join(normal_path, f'{i}voice.mp4'))
    except FileNotFoundError as e:
        print(f"File not found: {e}")

    try:
        for i in range(1, int(index) + 1):
            if os.path.exists(os.path.join(input_path, f'{i}.mp4')):
                shutil.move(os.path.join(input_path, f'{i}.mp4'), os.path.join(speed_path, f'{i}.mp4'))
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        
    try:
        for i in range(1, int(index) + 1):
            if os.path.exists(os.path.join(input_path, f'{i}elseacc.mp4')):
                shutil.move(os.path.join(input_path, f'{i}elseacc.mp4'), os.path.join(normal_acc_path, f'{i}elseacc.mp4'))
            elif os.path.exists(os.path.join(input_path, f'{i}voiceacc.mp4')):
                shutil.move(os.path.join(input_path, f'{i}voiceacc.mp4'), os.path.join(normal_acc_path, f'{i}voiceacc.mp4'))
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        
    try:
        for file in os.listdir(input_path):
            if file.endswith('.dep'):  # Check if the file has a .dep extension
                input_file = os.path.join(input_path, file)
                folder_file = os.path.join(dep_path, file)
                if os.path.exists(input_file):  # Check if the source file exists
                    shutil.move(input_file, folder_file)
                else:
                    print(f"File not found: {folder_file}")
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    
    try:
        for file in os.listdir(input_path):
            if file.endswith('.ts'):  # Check if the file has a .dep extension
                input_file = os.path.join(input_path, file)
                folder_file = os.path.join(ts_path, file)
                if os.path.exists(input_file):  # Check if the source file exists
                    shutil.move(input_file, folder_file)
                else:
                    print(f"File not found: {folder_file}")
    except FileNotFoundError as e:
        print(f"File not found: {e}")    
    
    try:
        if os.path.exists(os.path.join(input_path, "merged_video.mp4")):
            shutil.move(os.path.join(input_path, "merged_video.mp4"), os.path.join(output_path, "summarized_video.mp4"))
        if os.path.exists(os.path.join(input_path, movie_name)):
            shutil.move(os.path.join(input_path, movie_name), os.path.join(output_path, movie_name))
        if os.path.exists(os.path.join(input_path, "inaSpeechSegmenter_voice_else_analysis")):
            try:
                shutil.move(os.path.join(input_path, "inaSpeechSegmenter_voice_else_analysis"), os.path.join(output_path, "inaSpeechSegmenter_voice_else_analysis"))
            except:
                print(f"{os.path.join(output_path, 'inaSpeechSegmenter_voice_else_analysis')} already exists")
        if os.path.exists(os.path.join(input_path, "merged_video.srt")):
            shutil.move(os.path.join(input_path, "merged_video.srt"), os.path.join(output_path, "summarized_video.srt"))
        if new_duration>0 and os.path.exists(os.path.join(input_path, f'compressedin_{new_duration}min.mp4')):
            shutil.move(os.path.join(input_path, f'compressedin_{new_duration}min.mp4'), os.path.join(output_path, f'compressedin_{new_duration}min.mp4'))
        if os.path.exists(os.path.join(input_path, f'compressedin_{new_duration}min.srt')):
            shutil.move(os.path.join(input_path, f'compressedin_{new_duration}min.srt'), os.path.join(output_path, f'compressedin_{new_duration}min.srt'))
            
            
        os.chdir(input_path)
        for filename in os.listdir():
            if filename.endswith(".bat"):
                shutil.move(os.path.join(input_path, filename), os.path.join(bat_path, filename))

        os.chdir(main_path)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    print(f"\n------- Step {n_step} - the generated files were organized in their corresponding folders --> COMPLETE ------\n")
    n_step+=1

    ###### create zip with all generated files #########
    os.chdir(main_path)
    import tozip
    try:
        tozip.main(input_path, original_title, reference, target_min_speed, target_max_speed)
    except Exception as e:
        print("An error occurred:", e)
        
    print(f"\n------- Step {n_step} - the input file was compressed in a zip file located in the root directory (containing both <input> and <program> --> COMPLETE ------\n")
    n_step+=1

    ######## delete all files included in the zip, but the original movie file ########
    os.chdir(main_path)
    restart_option = input(
        "Do you want to empty the input folder, except for the movie you provided as input? <yes> or any key: ")
    if restart_option == 'yes':
        import Restart
        try:
            Restart.main(input_path, movie_name)
        except Exception as e:
            print("An error occurred:", e)

        print(f"\n------- Step {n_step}* optional - the <input> folder is empty and ready for a new movie\nall the files generated and used for the previous movies can be found in their corresponding zip files\n--> COMPLETE ------")

    return 

if __name__ == "__main__":
    main()