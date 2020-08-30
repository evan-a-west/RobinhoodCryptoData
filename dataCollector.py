import robin_stocks as r
import multiprocessing as mp
import threading as thr
import csv
import numpy as np
import time
import os
import datetime
from pytz import timezone
import sys
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
import logging
from requests.exceptions import ConnectionError

try:
    # Setup Robinhood account
    r.login("evan-west@hotmail.com", "Ambrosio%67")
except ConnectionError as err:
    logging.error("Connection Error while logging in")
    logging.error(err)
# Access token to Evan's Dropbox
# TOKEN = 'sl.AgvJduh0Hme3yN02cpSv7Omx-upyHV8Uwvq_7OM5mVHr_qYH-mpw_IABmFkuZwCtTQQEFCS7XpXulA6Y9fZIYQFz-wA11kj_fgrnPHCsIlXXSfWhe9QyLf-DIgdybMEnyDHUUUE'
TOKEN = 'CuaXlDyGECgAAAAAAAAAAZYAeOmfjT2c2UcrE7CcWNLU2dz5hRbLaNQGrxx2GK4H'
# Root path at which to save files. Keep the forward slash before destination filename
BACKUPPATH_ROOT = '/Server1'
# Set DEBUGGER to 1 to print debugging statements
DEBUGGER = 0


def setup():
    # Check for an access token
    if (len(TOKEN) == 0):
        sys.exit("ERROR: Looks like you didn't add your access token. Open up backup-and-restore-example.py in a text editor and paste in your token in line 14.")
     # Create an instance of a Dropbox class, which can make requests to the API.

    if(DEBUGGER == 1):
        print("inside setup")

    all_currency_info = None
    try:
        # Retrieve all currency information from Robinhood
        all_currency_info = r.crypto.get_crypto_currency_pairs(info=None)
    except ConnectionError as err:
        logging.error("Connection Error while retreiving currency information")
        logging.error(err)

    # Build array of currency codes
    codes = []
    for data in all_currency_info:
        codes.append(data.get('asset_currency').get('code'))
    return codes


def save_data(code, data, current_datetime, file_upload_time, previous_filename, backup_thread):
    if(not (backup_thread is None)):
        if(DEBUGGER == 1):
            print(
                "\n\n###########################################################################")
            print("backup_thread: " + str(backup_thread))
            print("backup_thread is None: " + str(backup_thread is None) +
                  ", Note - expecting FALSE here")
            print("Waiting for previous backup process to complete")
        backup_thread.join()
        if(DEBUGGER == 1):
            print("Previous backup process is complete")

    if(DEBUGGER == 1):
        print("Inside save_data")

    # Extract raw data form the dictionary
    raw_data = []
    for record in data:
        row = []
        for item in record:
            row.append(record.get(item))
        raw_data.append(row)
    numpy_data = np.array(raw_data)

    # Create directories, as needed
    directory = 'Data/' + code
    if(not os.path.exists(directory)):
        os.makedirs(directory)

    file_append = current_datetime.strftime("%d_%m_%Y")

    filename = directory + '/' + code + '_' + file_append + '.csv'

    # If the file does not exist, create it and output the headers
    if(not os.path.exists(filename)):
        # Generate headers
        headers = ''
        for i in data[0].keys():
            headers += i + ','
        # Create the new file and save data with headers
        with open(filename, 'a') as outfile:
            np.savetxt(fname=outfile, X=numpy_data,
                       delimiter=',', fmt='%s', header=str(headers))

    # If the file exists, save data without headers
    else:
        # Append data to the file
        with open(filename, 'a') as outfile:
            np.savetxt(fname=outfile, X=numpy_data, delimiter=',', fmt='%s')

    # Upload the file to dropbox if the file_upload_time has been reached or if the filename changed.
    # If the filename changed, then the final version of the previous file can be uploaded
    # Note: This will overwrite any existing file on Dropbox
    if(DEBUGGER == 1):
        print("(current_datetime - file_upload_time).total_seconds() : " +
              str((current_datetime - file_upload_time).total_seconds()))
        print("(current_datetime - file_upload_time).total_seconds() >= 0 : " +
              str((current_datetime - file_upload_time).total_seconds() >= 0))
        print("previous_filename : " + previous_filename)
        print("filename : " + filename)
        print("previous_filename != filename : " +
              str(previous_filename != filename))
    backup_thread = None
    if((current_datetime - file_upload_time).total_seconds() >= 0 or (previous_filename != filename)):
        # On the first iteration of the program, the previous_filename will be null, and we want to update it to the new filname
        if(previous_filename == code + '_firstupload.csv'):
            previous_filename = filename
        filepath = previous_filename
        backuppath = BACKUPPATH_ROOT + "/" + filepath

        backup_thread = thr.Thread(target=backup, args=(backuppath, filepath,))
        backup_thread.start()
    return {'filename': filename, 'backup_thread': backup_thread}


def process_func(code, stop_threads):
    if(DEBUGGER == 1):
        print("Starting process_func for process: " + str(mp.current_process()))
    data = []
    duration = 5.0  # Duration of sleep in seconds

    # Threshold for triggering file write. The value here is the number of loops between file writes (i.e. 36 = 3 minutes when duration is set to 5 seconds)
    write_threshold = 36

    loop_counter = 0  # Will trigger a while write when loop_counter == write_threshold
    file_upload_time = 0  # For tracking the previous file upload
    time_between_uploads = 3  # Hours between uploads to Dropbox
    # For tracking when filename changes. This is needed so that if the filename changes between upload intervals, the final version of the previous file can be uploaded
    previous_filename = code + '_firstupload.csv'
    backup_thread = None  # Allows the backup process generated in save_data to run in parrellel. Most of the time, the process will finish backing up to DropBox before the next call to save_data, but this is needed to handle the situations where the backup has not completed yet

    if(DEBUGGER == 1):
        print("stop_threads : " + str(stop_threads()) +
              ", Note: expecting FALSE until user input")
        print("not stop_threads : " + str(not stop_threads()) +
              ", Note: expecting TRUE until user input")

    while (not stop_threads()):  # Loop INFINITELY until user says to stop
        if(DEBUGGER == 1):
            print("Inside process_func while loop with loop_counter = " +
                  str(loop_counter))

        try:
            # Get current quote from RobinHood
            local_dict = r.crypto.get_crypto_quote(code, info=None)
        except ConnectionError as err:
            logging.error(
                "Connection Error while retrieving a quote for " + code)
            logging.error(err)

        # Append the datetime to the record
        est = timezone('EST')
        current_datetime = datetime.datetime.now(est)
        local_dict.update({'datetime': str(current_datetime)})

        # Update the fileupload time, if an upload occurred in the previous loop
        if(file_upload_time == 0):
            delta = datetime.timedelta(hours=time_between_uploads)
            # delta = datetime.timedelta(seconds=time_between_uploads)
            file_upload_time = current_datetime + delta
        # Save the newest record
        data.append(local_dict)

        # Wait
        time.sleep(duration)

        # Save the data to a file based on the write_threshold
        if(loop_counter >= write_threshold):

            # Save the accumulated data
            info_from_save_data = save_data(
                code, data, current_datetime, file_upload_time, previous_filename, backup_thread)
            previous_filename = info_from_save_data.get("filename")
            backup_thread = info_from_save_data.get("backup_thread")
            # counters and data
            loop_counter = 0
            data = []

        loop_counter += 1


# Uploads contents of LOCALFILE to Dropbox
def backup(backuppath, filepath):
    if(DEBUGGER == 1):
        print('backuppath: ' + backuppath)
        print('filepath: ' + filepath)
        print("Creating a Dropbox object...")

    dbx = dropbox.Dropbox(TOKEN)

    # Check that the access token is valid
    try:
        dbx.users_get_current_account()
    except AuthError as err:
        sys.exit(
            "ERROR: Invalid access token; try re-generating an access token from the app console on the web.")

    with open(filepath, 'rb') as f:
        # We use WriteMode=overwrite to make sure that the settings in the file
        # are changed on upload
        if(DEBUGGER == 1):
            print("Uploading " + filepath +
                  " to Dropbox as " + backuppath + "...")

        try:
            dbx.files_upload(f.read(), backuppath,
                             mode=WriteMode('overwrite'))
        except ApiError as err:
            # This checks for the specific error where a user doesn't have enough Dropbox space quota to upload this file
            if (err.error.is_path() and
                    err.error.get_path().error.is_insufficient_space()):
                sys.exit("ERROR: Cannot back up; insufficient space.")
            elif err.user_message_text:
                print(err.user_message_text)
                sys.exit()
            else:
                print(err)
                sys.exit()


# # Adding few functions to check file details
# def checkFileDetails():
#     print("Checking file details")

#     for entry in dbx.files_list_folder('').entries:
#         print("File list is : ")
#         print(entry.name)

def main():
    # Setup connection to
    process_names = setup()

    if(DEBUGGER == 1):
        print(process_names)
    # procs = []
    threads = []

    # process_names = ['ETC']
    stop_threads = False
    for name in process_names:
        # proc = mp.Process(target=process_func, args=(name,))
        # procs.append(proc)
        # proc.start()
        thread = thr.Thread(target=process_func,
                            args=(name, lambda: stop_threads))
        threads.append(thread)
        thread.start()

    while not stop_threads:
        userInput = input("input 'exit' to stop : ")
        if(userInput == "exit"):
            stop_threads = True

    # for proc in procs:
    #     proc.join()
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
