"""
Zip creation of the files of the folder where the output is generated.
"""

import os
import shutil

##
# @brief  Main function.
# @param movie_path   The path where the files are stored.
# @param original_title   The name of the original file to name the zip file.
# @param method   The method used to accelerate the video {ina, srt}, to add to the name of the zip file.
# @param target_min_speed   The minimum target voice speed of the video to add to the name of the zip file.
# @param target_max_speed   The maximum target voice speed of the video to add to the name of the zip file..
##
def main(movie_path, original_title, method, target_min_speed, target_max_speed):

    os.chdir(movie_path)
    name = original_title
    root_dir = f'{movie_path}'[:-6] #length("input") == 6
    os.chdir(root_dir)
    shutil.make_archive(f'{name}_{method}_{target_min_speed}_{target_max_speed}', 'zip', 'input')

    if os.path.exists(os.path.join(root_dir, f'{name}_{method}_{target_min_speed}_{target_max_speed}.zip')):
        print("ZIP file successfully created")
    else:
        print("The ZIP file was not created")
