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
import json
import pyotp
from os.path import isfile, join
from os import listdir
import re

try:
    # Setup Robinhood account
    totp = pyotp.TOTP("3FYIQZB7NUF2SS6J").now()
    r.login("evan-west@hotmail.com", "Ambrosio%67", mfa_code=totp)
except ConnectionError as err:
    logging.error("Connection Error while logging in")
    logging.error(err)
# Access token to Evan's Dropbox
# TOKEN = 'sl.AgvJduh0Hme3yN02cpSv7Omx-upyHV8Uwvq_7OM5mVHr_qYH-mpw_IABmFkuZwCtTQQEFCS7XpXulA6Y9fZIYQFz-wA11kj_fgrnPHCsIlXXSfWhe9QyLf-DIgdybMEnyDHUUUE'
TOKEN = 'CuaXlDyGECgAAAAAAAAAAZYAeOmfjT2c2UcrE7CcWNLU2dz5hRbLaNQGrxx2GK4H'
# Root path at which to save files. Keep the forward slash before destination filename
BACKUPPATH_ROOT = '/local'

# Set DEBUGGER to 1 to print debugging statements
DEBUGGER = 1

LOCAL_DATA_DIRECTORY = 'Data/'


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

# Uploads all files that are not currently on Dropbox


def UploadFilesToDropboxIfTheyDoNotExist(dbx, code, local_files, directory):
    dropbox_backuppath = BACKUPPATH_ROOT + "/" + LOCAL_DATA_DIRECTORY + code
    drobbox_files = {
        f.name for f in dbx.files_list_folder(dropbox_backuppath).entries}

    file_to_upload = []
    for file in local_files:
        if not (file in drobbox_files):
            file_to_upload.append(file)

    for upload_file in file_to_upload:
        with open(directory + "/" + upload_file, 'rb') as f:
            # We use WriteMode=overwrite to make sure that the settings in the file
            # are changed on upload
            upload_filepath = dropbox_backuppath + "/" + upload_file
            if(DEBUGGER == 1):
                print("Uploading " + upload_file +
                      " to Dropbox as " + upload_filepath + "...")

            try:
                dbx.files_upload(f.read(), upload_filepath,
                                 mode=WriteMode('add'))
            except ApiError as err:
                # This checks for the specific error where a user doesn't have enough Dropbox space quota to upload this file
                if (err.error.is_path() and
                        err.error.get_path().error.is_insufficient_space()):
                    print("ERROR: Cannot back up; insufficient space.")
                elif err.user_message_text:
                    print(err.user_message_text)
                else:
                    print(err)


def DeleteLocalFilesOlderThan1Month(code, local_files, directory):
    for local_file in local_files:
        f_split = local_file.replace('.', '_')
        f_split = f_split.split('_')
        # f_split = re.split('_|.', local_file)
        file_date_str = f_split[1] + "_" + f_split[2] + "_" + f_split[3]
        file_date = datetime.datetime.strptime(
            file_date_str, "%d_%m_%Y")

        est = timezone('EST')
        current_date_str = datetime.datetime.now(est).strftime("%d_%m_%Y")
        current_date = datetime.datetime.strptime(
            current_date_str, "%d_%m_%Y")

        temp = current_date - file_date
        print(temp)

        # If the file was created more than 31 days ago, delete it locally
        if((current_date - file_date).days > 31):
            filepath = directory + "/" + local_file
            os.remove(filepath)


def FileManager(coinCodes):
    dbx = dropbox.Dropbox(TOKEN)

    # Check that the access token is valid
    try:
        dbx.users_get_current_account()
    except AuthError as err:
        sys.exit(
            "ERROR: Invalid access token; try re-generating an access token from the app console on the web.")

    for code in coinCodes:
        directory = LOCAL_DATA_DIRECTORY + code

        local_files = [f for f in listdir(
            directory) if isfile(join(directory, f))]

        UploadFilesToDropboxIfTheyDoNotExist(dbx, code, local_files, directory)
        DeleteLocalFilesOlderThan1Month(code, local_files, directory)


def main():
    coinCodes = setup()
    FileManager(coinCodes)


if __name__ == "__main__":
    main()
