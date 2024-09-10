"""

Speech acceleration

In this file, the subtitle file is converted into a dataframe with multiple columns to get statistics and search values.
"""

import pandas as pd
import subprocess
import re
import string
import pysubs2
import langdetect

##
# @brief This function first creates a table with columns for each subtitle such as start and end times, graphemes and phonemes, speed and speed-1s.
# There are also cells with the mean, maximum and minimum of the speed-1s column.
# The next step is to load the subtitle file and create a text file with the graphemes of each subtitle, separated by three line breaks by the next block, and write it also in the df.
# The following modifications have to be made to the original graphemes: remove any html markings such as ''<>'' or ''{}'', replace line breaks with spaces, ensure that the first 
# character is a letter and delete any symbols that may appear, as well as escape characters.
# @param srt_name   The name of the subtitle file.
# @param n_decimals   The number of decimal places to format so it fits better in a csv cell.
# @param output_path   The path where the files are stored.
# @return  The dataframe with the subtitles.
##
def process_srt_graphemes_df(srt_name, n_decimals, output_path):
    columns = pd.Series(['index','start-time', 'end-time', 'subtitles-graphemes', 'subtitles-phonemes', 'speed','mean-speed', 'speed-1s', 'mean-speed-1s', 'max-speed', 'min-speed', 'start-time-s', 'end-time-s'])
    df = pd.DataFrame(columns=columns)
    df.set_index('index', inplace = True)
    index = 0

    pattern_html1 = re.compile('<[^<]+?>')
    pattern_html2 = re.compile('{[^{]+?}')
    pattern_first_notsymbol = re.compile('^\W+')
    
    index = 0
    
    subs = pysubs2.load(path = srt_name + '.srt', encoding = 'UTF-8', format = 'srt')
    
    translator = str.maketrans("", "", string.punctuation+"!\"#$%&'()*+,-./:;<=>?@[\]^__`{|}~¿¡♪[\n][\t]}")
    
    for sub in subs:
        
        index = index + 1

        df.loc[index, 'start-time'] = pysubs2.time.ms_to_str(sub.start, fractions = True)
        df.loc[index, 'start-time-s'] = round(sub.start/1000, n_decimals)
                                            
        df.loc[index, 'end-time'] = pysubs2.time.ms_to_str(sub.end, fractions = True)
        df.loc[index, 'end-time-s'] = round(sub.end/1000, n_decimals)
        
        df.loc[index, 'time-diff'] = round(df.loc[index, 'end-time-s'] - df.loc[index, 'start-time-s'], n_decimals)
                    
        # Elimination of html tags ({} and <>)
        line_html1 = re.sub(pattern_html1, ' ', sub.text)
        line_html2 = re.sub(pattern_html2, ' ', line_html1)
        
        # Lines were joined by \n
        lines_split = line_html2.split('\n')
        
        lines_join = ' '.join(line.strip() for line in lines_split)
        line_initial = re.sub(pattern_first_notsymbol, '', lines_join).replace(r'\N', ' ').translate(translator) # \N in some cases
        
        df.loc[index, 'subtitles-graphemes'] = line_initial


    # Delete subtitle lines (grapheme) which are empty (speed impossible to calculate)
    df_empty = df['subtitles-graphemes'].map(lambda x: x if x.strip() else '\t')
    df.drop(df[df_empty == '\t'].index, inplace=True)
    df.reset_index(drop=True,inplace=True)

    # Create a custom index starting from 1
    index_arranged = pd.Index(range(1, len(df)+1))
    df.index = index_arranged
        
    input_file_path = output_path + "/graphemes_" + srt_name + ".txt"
    
    with open(input_file_path, 'w', encoding = 'UTF-8') as file:
        # Iterate over each line in the file
        for i in df.index:
            file.write((df.loc[i, 'subtitles-graphemes'].strip()).translate(translator))
            # Write three empty lines, to read each line separately in the espeak program
            file.write("\n" * 3)
    
    return df

##
# @brief The next step is to convert the graphemes into phonemes using the ''speak'' program, a dialogue synthesiser, and write the result to a text file. The reason for using 3 line breaks 
# in the input grapheme text file is because this translation program translates every 2 line breaks. As in the previous operation, the content is copied into the data table. 
# The phonemes of each subtitle need to be obtained to get the actual speech rate, which truly reflects this rate, if this were done with graphemes it would not be accurate. 
# The output of this program is phonemes separated by underscores or spaces, but it has been necessary to separate diphthongs and triphthongs so that they do not count as one phoneme.
# @param file_name   The name of the subtitle file.
# @param df   The dataframe with the subtitles and other parameters.
# @param language_prefix   The language of the subtitles.
# @param output_path   The path where the files are stored.
# @return  The dataframe with the subtitles.
##
def espeak_phonemes_df(file_name, df, language_prefix, output_path):
    
    output_file_path = output_path + "/phonemes_" + file_name + ".txt"
    result_file_path = output_path + "/error_espeak" + file_name + ".txt"
    input_file_path = output_path + "/graphemes_" + file_name + ".txt"
    
    command = ['espeak','-q','-v', language_prefix,'--ipa=3', "-f", input_file_path , '--phonout=' + output_file_path]
    
    result=subprocess.run(command, capture_output=True, text=True)
    
    if result.stdout.strip():
        with open(result_file_path, 'w', encoding = 'UTF-8') as file:
            file.write(result.stdout)
            print(result.stdout)
    
    #\u0250-\u02AF: IPA characters
    #\u0061-\u007A: alphanumeric

    pattern_diptongo = r"([\u0250-\u02AF\u0061-\u007A])([\u0250-\u02AF\u0061-\u007A])"
    pattern_triptongo = r"([\u0250-\u02AF\u0061-\u007A])([\u0250-\u02AF\u0061-\u007A])([\u0250-\u02AF\u0061-\u007A])"

    with open(output_file_path,'r', encoding = 'utf-8') as file:
        for i, line in enumerate(file):
            line = line.strip()
            triptongo_clean = re.sub(pattern_triptongo, r'\1_\2_\3', line)
            diptongo_clean = re.sub(pattern_diptongo, r'\1_\2', triptongo_clean)
            df.loc[i+1, 'subtitles-phonemes'] = str(diptongo_clean)
            
    return df

##
# @brief To obtain the speed-1s (grouping the subtitles) if they are separated by less than one second), the duration is calculated as the difference between the end of the 
# last grouped subtitle and the beginning of the first one, while the number of phonemes is the sum of all the grouped ones. The speed is similarly found by dividing phonemes by duration.
# @param df   The dataframe with the subtitles and other parameters.
# @param n_segs_umbral   The minimum number of seconds to group the subtitles, it is defined in the configuration file.
# @param n_decimals   The number of decimal places to format so it fits better in a csv cell.
##
def calculate_speed_1s(df, n_segs_umbral, n_decimals):
    i = 1
    while i <= len(df):
        group_start = i
        group_end = i
        total_phonemes = df.loc[i, 'phonemes-number']

        while group_end + 1 < len(df) and df.loc[group_end + 1, 'start-time-s'] - df.loc[group_end, 'end-time-s'] <= n_segs_umbral:
            group_end += 1
            total_phonemes += df.loc[group_end, 'phonemes-number']

        total_time = df.loc[group_end, 'end-time-s'] - df.loc[group_start, 'start-time-s']

        speed_1s = round(total_phonemes / total_time, n_decimals)
        df.loc[group_start:group_end, 'speed-1s'] = speed_1s
        i = group_end + 1

##
# @brief After having the number of phonemes per subtitle and their duration, the speed of each is calculated by dividing phonemes by duration. 
# @param df   The dataframe with the subtitles and other parameters.
# @param n_decimals   The number of decimal places to format so it fits better in a csv cell.
##
def calculate_speed(df, n_decimals):
    df['phonemes-number'] = df['subtitles-phonemes'].apply(lambda x: x.count('_') + x.count(' '))
    df['speed'] = round(df['phonemes-number'] / df['time-diff'], n_decimals)

##
# @brief This process calls calculate_speed and calculate_speed_1s
# @param df   The dataframe with the subtitles and other parameters.
# @param n_segs_umbral   The minimum number of seconds to group the subtitles, it is defined in the configuration file.
# @param n_decimals   The number of decimal places to format so it fits better in a csv cell.
# @return  The dataframe with the subtitles.
##
def speed_calculation(df, n_segs_umbral, n_decimals):
    calculate_speed(df, n_decimals)
    calculate_speed_1s(df, n_segs_umbral, n_decimals)
    return df

##
# @brief Calculation of parameters such as the average speed, the maximum and minimum speed, the score of the file and whether it has errors so they are calculated in this process.
# This score represents the quality of the subtitle file, which is calculated by subtracting errors such as bad formatting.
# @param df   The dataframe with the subtitles and other parameters.
# @param min_speed   The minimum speed.
# @param max_speed   The maximum speed.
# @param n_decimals   The number of decimal places.
# @return  The dataframe with the subtitles.
##
def global_parameters(df, min_speed, max_speed, n_decimals):
    index_min_speed = 0
    index_max_speed = 0

    df.loc[df['speed-1s'] < min_speed, 'index-min-speed-count'] = 1

    df.loc[df['speed-1s'] > max_speed, 'index-max-speed-count'] = 1

    index_min_speed = df['index-min-speed-count'].count()
    index_max_speed = df['index-max-speed-count'].count()
    
    if index_max_speed > 0:
        print(f"Subtitles whose speed is faster than 20 phonemes/second: {index_max_speed}")
    if index_min_speed > 0:
        print(f"Subtitles whose speed is slower than 4 phonemes/second: {index_min_speed}")

    df.loc[1, 'index-min-speed'] = index_min_speed
    df.loc[1, 'index-max-speed'] = index_max_speed

    subtitle_score = round(1 - (index_min_speed/len(df) + index_max_speed/len(df)), n_decimals)

    print(f"subtitle_score (/1): {subtitle_score}")

    df.loc[1, 'subtitle-score'] = subtitle_score - df.loc[1, 'n_errors']

    df.loc[1, 'mean-speed'] = round(df['speed'].mean(), n_decimals)
    df.loc[1, 'max-speed'] = df['speed'].max()
    df.loc[1, 'min-speed'] = df['speed'].min()
    df.loc[1, 'mean-speed-1s'] = round(df['speed-1s'].mean(), n_decimals)
    df.loc[1, 'max-speed-1s'] = df['speed-1s'].max()
    df.loc[1, 'min-speed-1s'] = df['speed-1s'].min()
    
    return df

##
# @brief Once the maximum and minimum target speeds have been confirmed, the target speeds for each subheading are calculated, so that the acceleration of each subheading can be calculated by 
# by dividing the target speed by the speed-1s. This acceleration is then limited if it is not within the range of accelerations entered in the configuration file 
# (acc_voice_min, acc_voice_max) or if these parameters are not numbers, they are changed to 1 if it is the minimum or 1.8 if it is the maximum that is wrong.
# @param file_name   The name of the subtitle file.
# @param df   The dataframe with the subtitles and other parameters.
# @param target_speed_min   The minimum speed.
# @param target_speed_max   The maximum speed.
# @param n_decimals   The number of decimal places.
# @param output_path   The path where the files are stored.
# @return  The dataframe modified.
##
def acc_calculate_csv_format(file_name, df, target_speed_min, target_speed_max, n_decimals, output_path):
    if len((df['speed-1s'] - df['min-speed-1s']).unique()) > 1:  #len(df)==1
        for i in df.index:
            df.loc[i, 'target-speed-1s'] = round((target_speed_max - target_speed_min)/(df.loc[1,'max-speed-1s'] - df.loc[1,'min-speed-1s'])*(df.loc[i,'speed-1s'] - df.loc[1,'min-speed-1s']) + target_speed_min, n_decimals)
            df.loc[i, 'acceleration-factor-1s'] = round(df.loc[i, 'target-speed-1s']/df.loc[i, 'speed-1s'], n_decimals)
            
    df_copy = df.copy()
        
    for (columnName, columnData) in df.items():
        df[columnName]=df[columnName].map(lambda x: '' if pd.isna(x) else x) #NaN
        df[columnName]=df[columnName].map(lambda x: str(x).replace('.',',') if isinstance(x, float) else x) #decimal con coma
            
    output_csv = output_path + "/" + file_name + '.csv'
    
    df.to_csv(output_csv, encoding = 'UTF-8', sep = ';', decimal = ',') 
    return df_copy

##
# @brief Order of start and end times, umber of subtitles with negative time and minimum of subtitles with text are checked, time overlaps and ensure its Spanish language.
# @param df   The dataframe with the subtitles and other parameters.
# @param n_subtitles_min   The minimum number of subtitles not empty.
# @param file_name   The name of the subtitle file.
# @param output_path   The path where the files are stored.
# @param language_prefix   The language of the subtitles.
##
def srt_errors(df, n_subtitles_min, file_name, output_path, language_prefix):
    n_errors = 0    
    df_sorted = df.copy()
    
    error_file = output_path + "/error.txt"
    
    df_sorted.sort_values(by='start-time-s', ascending=True, inplace = True) #df.compare(df2)
    if not df.equals(df_sorted):
        print(f"Error in {file_name}.srt, not sorted by start time")
        with open(error_file, "a") as file: file.write(f"Error in {file_name}.srt, not sorted by start time\n")
        n_errors += 1
    
    df_sorted = df.copy()
    df_sorted.sort_values(by='end-time-s', ascending=True, inplace = True) #df.compare(df2)
    if not df.equals(df_sorted):
        print(f"Error in {file_name}.srt, not sorted by end time")
        with open(error_file, "a") as file: file.write(f"Error in {file_name}.srt, not sorted by end time\n")
        n_errors += 1
    
    if (df['time-diff'] <= 0).any():
        print(f"Error in {file_name}.srt, subtitle with negative time")
        with open(error_file, "a") as file: file.write(f"Error in {file_name}.srt, subtitle with negative time\n")
        n_errors += 1
    
    if len(df) < n_subtitles_min:
        print(f"Error in {file_name}.srt, there isn't a minimum number of non-empty subtitles, the minimum is {n_subtitles_min}")
        with open(error_file, "a") as file: file.write(f"Error in {file_name}.srt, there isn't a minimum number of non-empty subtitles, the minimum is {n_subtitles_min}\n")
        n_errors += 1
        
    for i in df.index[:-1]:
        if (df.loc[i+1, 'start-time-s'] - df.loc[i, 'end-time-s'])<0:
            print(f"Error in {file_name}.srt, there is an overlap in subtitle {i}")
            with open(error_file, "a") as file: file.write(f"Error in {file_name}.srt, there is an overlap in subtitle {i}\n")
            n_errors += 1
        
    if len(df) > 1:
        text = open(output_path + "/graphemes_" + file_name + ".txt", 'r', encoding= 'UTF-8').read()
        if langdetect.detect(text) != language_prefix:
            results = langdetect.detect_langs(text)
            print(f"Error in {file_name}.srt, it's not in '{language_prefix}'. Results are {results}")
            with open(error_file, "a") as file: file.write(f"Error in {file_name}.srt, it's not in '{language_prefix}'. Results are {results}\n")
            n_errors += 1
        
    df.loc[1, 'n_errors'] = n_errors

    return 1
    
##
# @brief  Main function.
# @param file_name   The name of the subtitle file.
# @param language_prefix   The language of the subtitles.
# @param n_decimals   The number of decimal places.
# @param n_segs_umbral   The minimum number of seconds to group the subtitles.
# @param min_speed   The minimum speed.
# @param max_speed   The maximum speed.
# @param n_subtitles_min   The minimum number of subtitles.
# @param output_path   The path where the files are stored.
##
def main(file_name, language_prefix, n_decimals, n_segs_umbral, min_speed, max_speed, n_subtitles_min, output_path):
    df = process_srt_graphemes_df(file_name, n_decimals, output_path)
    df = espeak_phonemes_df(file_name, df, language_prefix, output_path)
    df = speed_calculation(df, n_segs_umbral, n_decimals)
    srt_errors(df, n_subtitles_min, file_name, output_path, language_prefix)
    df = global_parameters(df, min_speed, max_speed, n_decimals)
    return df