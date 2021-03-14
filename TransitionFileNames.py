import csv
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


# Access token to Evan's Dropbox
TOKEN = None
with open("dropboxToken.json", 'r') as infile:
    TOKEN = json.load(infile)
print(TOKEN)
TOKEN = TOKEN.get("token")
# Root path at which to save files. Keep the forward slash before destination filename
BACKUPPATH_ROOT = '/AWS_Server1'
DATA_DIRECTORY = 'Data'
# Set DEBUGGER to 1 to print debugging statements
DEBUGGER = 0

FILE_APPEND = datetime.datetime.now(timezone('EST')).strftime("%Y_%m_%d")


def setup():
    # Check for an access token
    if (len(TOKEN) == 0):
        sys.exit("ERROR: Looks like you didn't add your access token. Open up backup-and-restore-example.py in a text editor and paste in your token in line 14.")
     # Create an instance of a Dropbox class, which can make requests to the API.

    if(DEBUGGER == 1):
        print("inside setup")

    codes = None
    with open("coinCodes.json", 'r') as infile:
        codes = json.load(infile)
    codes = codes["codes"]

    return codes


def RenameFilesToNewFormat(dbx, uploadFilepath):
    listOfDropboxFiles = dbx.files_list_folder(
        uploadFilepath, recursive=False, include_deleted=False).entries

    listOfFilePaths = []
    for file in listOfDropboxFiles:
        listOfFilePaths.append(file.path_display)
    print(len(listOfFilePaths))

    for file in listOfDropboxFiles:
        print("\n##########")
        # We use WriteMode=overwrite to make sure that the settings in the file
        # are changed on upload
        if(DEBUGGER == 1):
            print("Editing Dropbox file: " + uploadFilepath + "...")

        try:
            print(file.path_display)
            splitFilename = file.name.split('_')
            print(splitFilename)

            if(splitFilename[1] != '2020' and splitFilename[1] != '2021'):
                print(splitFilename[3].split("."))
                # If there is anything but a .csv after the YEAR in the original filename, just delete the file. File is not needed or wanted.
                if(len(splitFilename[3].split(".")) == 2):
                    code = splitFilename[0]
                    year = splitFilename[3].split(".")[0]

                    month = splitFilename[2]
                    day = splitFilename[1]
                    newFilename = code + "_" + year + "_" + month + "_" + day + ".csv"
                    newFilepath = uploadFilepath + "/" + newFilename
                    print(newFilepath)
                    if not (newFilepath in listOfFilePaths):
                        dbx.files_move_v2(file.path_display, newFilepath)
                        print("Update Made!!!")
                else:
                    dbx.files_delete(file.path_display)
        except ApiError as err:
            # This checks for the specific error where a user doesn't have enough Dropbox space quota to upload this file
            if (err.error.is_path() and
                    err.error.get_path().error.is_insufficient_space()):
                print("ERROR: Cannot back up; insufficient space.")
            elif err.user_message_text:
                print(err.user_message_text)
            else:
                print(err)
        except dbx.files.RelocationError as err:
            print(err.user_message_text)


def FileManager(coinCodes):
    dbx = dropbox.Dropbox(TOKEN)
    # Check that the access token is valid
    try:
        dbx.users_get_current_account()
    except AuthError as err:
        sys.exit(
            "ERROR: Invalid access token; try re-generating an access token from the app console on the web.")
    for code in coinCodes:
        DropBoxFilepath = BACKUPPATH_ROOT + "/" + DATA_DIRECTORY + "/" + code
        RenameFilesToNewFormat(dbx, DropBoxFilepath)


def main():
    coinCodes = setup()

    FileManager(coinCodes)


if __name__ == "__main__":
    main()
