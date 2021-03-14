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
BACKUPPATH_ROOT = '/AWS_Server1'

# Set DEBUGGER to 1 to print debugging statements
DEBUGGER = 0

LOCAL_DATA_DIRECTORY = 'Data/'
FILE_APPEND = datetime.datetime.now(timezone('EST')).strftime("%d_%m_%Y")


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


def UploadPreviousFilenameToDropbox(dbx, uploadFilepath, localFilepath):
    with open(localFilepath, 'rb') as f:
        # We use WriteMode=overwrite to make sure that the settings in the file
        # are changed on upload
        if(DEBUGGER == 1):
            print("Uploading " + localFilepath +
                  " to Dropbox as " + uploadFilepath + "...")

        try:
            dbx.files_upload(f.read(), uploadFilepath,
                             mode=WriteMode('overwrite'))
        except ApiError as err:
            # This checks for the specific error where a user doesn't have enough Dropbox space quota to upload this file
            if (err.error.is_path() and
                    err.error.get_path().error.is_insufficient_space()):
                print("ERROR: Cannot back up; insufficient space.")
            elif err.user_message_text:
                print(err.user_message_text)
            else:
                print(err)


def FileManager(coinCodes, previous_filenames):
    dbx = dropbox.Dropbox(TOKEN)
    # Check that the access token is valid
    try:
        dbx.users_get_current_account()
    except AuthError as err:
        sys.exit(
            "ERROR: Invalid access token; try re-generating an access token from the app console on the web.")
    filenames = {}
    for code in coinCodes:
        filename = code + '_' + FILE_APPEND + '.csv'
        filenames.update({code: filename})
        # On the first iteration of the program, the previous_filename will be null, and we want to update it to the new filname
        # Also, occasionally, the preivious_filenames dictionary will be empty (i.e. {}). IN this case, recover by setting previous filename to current filename
        previous_filename = None
        if(previous_filenames is None or not previous_filenames):
            previous_filename = filename
        # Otherwise, stick with the previous filename
        else:
            previous_filename = previous_filenames.get(code)

        localFilePath = LOCAL_DATA_DIRECTORY + code + "/" + previous_filename
        uploadFilepath = BACKUPPATH_ROOT + "/" + localFilePath
        UploadPreviousFilenameToDropbox(dbx, uploadFilepath, localFilePath)

    # Save the new filename
    saveStatus(filenames)


def readStatus():
    filename = LOCAL_DATA_DIRECTORY + "uploadData.json"
    # If the file does not exist, return nothing
    if(not os.path.exists(filename)):
        return None
    # If the file exists, update data
    else:
        # Append data to the file
        with open(filename, 'r') as infile:
            return json.load(infile)


def saveStatus(newFilename):
    statusDict = {
        "previous_filenames": newFilename
    }
    status = json.dumps(statusDict, indent=4, sort_keys=True, default=str)

    filename = LOCAL_DATA_DIRECTORY + "uploadData.json"

    # Append data to the file
    with open(filename, 'w') as outfile:
        return json.dump(status, outfile)


def main():
    coinCodes = setup()

    status = readStatus()
    # This if statement should only occur on the first run
    if(status is None):
        statusDict = {
            "previous_filenames": None
        }
        status = json.dumps(
            statusDict, indent=4, sort_keys=True, default=str)
    status = json.loads(status)

    previous_filenames = status["previous_filenames"]

    FileManager(coinCodes, previous_filenames)


if __name__ == "__main__":
    main()
