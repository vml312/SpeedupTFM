"""
Deleting the processing product folder (OPTIONAL)

You are asked by keyboard if you want to delete this folder, if you enter ''yes'' this function is called.

In order not to cause problems for future film processing, this folder is deleted, because the compressed folder has also been generated and stored.

@author: V
"""

import os
import shutil

##
# @brief  Deletes the processing product folder.
# @param input_path   The path where the files are stored.
# @param movie_name   The name of the movie.
##
def main(input_path, movie_name):
    os.chdir(input_path)
    for filename in os.listdir(input_path):
        if filename != movie_name:
            file_path = os.path.join(input_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'{e}: Failed to delete')
