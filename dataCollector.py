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

try:
    # Setup Robinhood account
    totp = pyotp.TOTP("3FYIQZB7NUF2SS6J").now()
    r.login("evan-west@hotmail.com", "Ambrosio%67", mfa_code=totp)
except ConnectionError as err:
    log("Connection Error while logging in")
    log(err)

# Set DEBUGGER to 1 to log debugging statements
DEBUGGER = 0

LOCAL_DATA_DIRECTORY = 'Data/'
LOGGING_DIRECTORY = LOCAL_DATA_DIRECTORY + "Logs/"
FILE_APPEND = datetime.datetime.now(timezone('EST')).strftime("%d_%m_%Y_%M")


def setup():
    if(DEBUGGER == 1):
        log("inside setup")

    all_currency_info = None
    try:
        # Retrieve all currency information from Robinhood
        all_currency_info = r.crypto.get_crypto_currency_pairs(info=None)
    except ConnectionError as err:
        log("Connection Error while retreiving currency information")
        log(err)

    # Build array of currency codes
    codes = []
    for data in all_currency_info:
        codes.append(data.get('asset_currency').get('code'))
    return codes


def save_data(coinCodes, allData, current_datetime):
    if(DEBUGGER == 1):
        log("Inside save_data")

    filenames = {}
    # Extract raw data from the dictionary
    for code in coinCodes:
        data = allData.get(code)
        raw_data = []
        for record in data:
            row = []
            for item in record:
                row.append(record.get(item))
            raw_data.append(row)
        numpy_data = np.array(raw_data)

        # Create directories, as needed
        directory = LOCAL_DATA_DIRECTORY + code
        if(not os.path.exists(directory)):
            os.makedirs(directory)

        filename = directory + '/' + code + '_' + FILE_APPEND + '.csv'
        filenames.update({code: filename})
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
                np.savetxt(fname=outfile, X=numpy_data,
                           delimiter=',', fmt='%s')


def process_func(code):
    if(DEBUGGER == 1):
        log("Starting process_func for code: " + str(code))

    try:
        # Get current quote from RobinHood
        local_dict = r.crypto.get_crypto_quote(code, info=None)
    except ConnectionError as err:
        log(
            "Connection Error while retrieving a quote for " + code)
        log(err)
    except Exception as err:
        log(
            "Exception while retrieving a quote for " + code)
        log(err)

    if(DEBUGGER == 1):
        log("data fetched from robinhood " + str(local_dict))

    # Append the datetime to the record
    est = timezone('EST')
    current_datetime = datetime.datetime.now(est)
    local_dict.update({'datetime': str(current_datetime)})

    return local_dict


def log(data):
    # Create logging directory, if it doesn't exist
    if(not os.path.exists(LOGGING_DIRECTORY)):
        os.makedirs(LOGGING_DIRECTORY)

    # Create filename form current date
    current_datetime = datetime.datetime.now(timezone('EST'))
    filepath = LOGGING_DIRECTORY + "logs_" + \
        current_datetime.strftime("%d_%m_%Y") + ".txt"

    # Log data
    with open(filepath, 'a') as f:
        f.write(str(current_datetime) + "\t" + data)
        f.write("\n-------------------------------------------------\n")


def logCleanup():
    log_files = [f for f in listdir(
        LOGGING_DIRECTORY) if isfile(join(LOGGING_DIRECTORY, f))]
    for log_file in log_files:
        f_split = log_file.replace('.', '_')
        f_split = f_split.split('_')
        # f_split = re.split('_|.', local_file)
        file_date_str = f_split[1] + "_" + f_split[2] + "_" + f_split[3]
        file_date = datetime.datetime.strptime(
            file_date_str, "%d_%m_%Y")

        current_date_str = datetime.datetime.now(
            timezone('EST')).strftime("%d_%m_%Y")
        current_date = datetime.datetime.strptime(
            current_date_str, "%d_%m_%Y")

        # If the file was created more than X days ago, delete it locally
        if((current_date - file_date).days > 14):
            filepath = LOGGING_DIRECTORY + log_file
            os.remove(filepath)


def readStatus():
    filename = LOCAL_DATA_DIRECTORY + "runData.json"
    # If the file does not exist, return nothing
    if(not os.path.exists(filename)):
        return None
    # If the file exists, update data
    else:
        # Append data to the file
        with open(filename, 'r') as infile:
            return json.load(infile)


def saveStatus(run_counter):
    statusDict = {
        "run_counter": run_counter
    }
    status = json.dumps(statusDict, indent=4, sort_keys=True, default=str)

    filename = LOCAL_DATA_DIRECTORY + "runData.json"

    # Append data to the file
    with open(filename, 'w') as outfile:
        return json.dump(status, outfile)


def main():
    # Setup connection to
    coinCodes = setup()

    # # Threshold for triggering file write. The value here is the number of loops between file writes (i.e. 36 = 3 minutes when duration is set to 5 seconds)
    # write_threshold = 20

    # loop_counter = 0  # Will trigger a while write when loop_counter == write_threshold

    status = readStatus()

    # This if statement should only occur on the first run
    if(status is None):
        statusDict = {
            "run_counter": 0,
        }
        status = json.dumps(
            statusDict, indent=4, sort_keys=True, default=str)
    status = json.loads(status)

    run_counter = status["run_counter"]

    # data - For each coin, save all data
    # previous_filename - For each coin, track when filename changes. This is needed so that if the filename changes between upload intervals, the final version of the previous file can be uploaded
    allData = {}
    for code in coinCodes:
        allData.update({code: []})

    if(DEBUGGER == 1):
        log("coinCodes: " + str(coinCodes))
        log("allData: " + str(allData))

    current_datetime = datetime.datetime.now(timezone('EST'))

    # log each 5 loops
    if(run_counter % 5 == 0):
        log("total_loop_counter: " + str(run_counter) +
            ", datetime: " + str(current_datetime))
    run_counter += 1

    # For each coin, get its current market data
    for code in coinCodes:
        coindata = allData.get(code)
        coindata.append(process_func(code))
        allData.update({code: coindata})
        if(DEBUGGER == 1):
            log("#################################################")
            log("Inside coinCodes loop1")
            log("Code: " + str(code))
            log("allData: " + str(allData))
            log("#################################################")

    if(DEBUGGER == 1):
        log("#################################################")
        log("Post coinCodes loop1")
        log("allData: " + str(allData))
        log("#################################################")

    # Save the accumulated data
    save_data(coinCodes, allData, current_datetime)

    saveStatus(run_counter)
    logCleanup()


if __name__ == "__main__":
    main()
