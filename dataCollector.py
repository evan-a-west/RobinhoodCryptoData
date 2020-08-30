import robin_stocks as r
import multiprocessing as mp
import csv
import numpy as np
import time
import os
import datetime
from pytz import timezone
r.login("evan-west@hotmail.com", "Ambrosio%67")

DEBUGGER = 1


def setup():
    if(DEBUGGER == 1):
        print("inside setup")

    all_currency_info = r.crypto.get_crypto_currency_pairs(info=None)
    codes = []
    for data in all_currency_info:
        codes.append(data.get('asset_currency').get('code'))
    return codes


def save_data(code, data, current_datetime, file_upload_time):
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

    file_append = current_datetime.strftime("%d_%m_%Y_Hour%H")

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

    # Upload the file to dropbox every three hours
    # ...Need logic here


def process_func(code):
    if(DEBUGGER == 1):
        print("Starting process_func for process: " + str(mp.current_process()))
    data = []
    duration = 5.0  # Duration of sleep in seconds

    # Threshold for triggering file write. The value here is the number of loops between file writes (i.e. 36 = 3 minutes when duration is set to 5 seconds)
    write_threshold = 36

    loop_counter = 0  # Will trigger a while write when loop_counter == write_threshold
    file_upload_time = 0  # For tracking the previous file upload
    time_between_uploads = 3  # Hours between uploads to Dropbox

    while (1+1 == 2):  # Loop INFINITELY
        if(DEBUGGER == 1):
            print("Inside process_func while loop with loop_counter = " +
                  str(loop_counter))

        # Get current quote from RobinHood
        local_dict = r.crypto.get_crypto_quote(code, info=None)

        # Append the datetime to the record
        est = timezone('EST')
        current_datetime = datetime.datetime.now(est)
        local_dict.update({'datetime': str(current_datetime)})

        # Update the fileupload time, if an upload occurred in the previous loop
        if(file_upload_time == 0):
            file_upload_time = datetime.timedelta(hours=time_between_uploads)

        # Save the newest record
        data.append(local_dict)

        # Wait
        time.sleep(duration)

        # Save the data to a file based on the write_threshold
        if(loop_counter >= write_threshold):

            # Save the accumulated data
            save_data(code, data, current_datetime, file_upload_time)

            # counters and data
            loop_counter = 0
            data = []

        loop_counter += 1


def main():
    process_names = setup()

    if(DEBUGGER == 1):
        print(process_names)
    procs = []

    for name in process_names:
        proc = mp.Process(target=process_func, args=(name,))
        procs.append(proc)
        proc.start()

    for proc in procs:
        proc.join()


if __name__ == "__main__":
    main()
