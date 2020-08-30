This repo is for grabbing data from Robinhood (ask price, bid price, and market price, etc) from robinhood, which seemingly can only be accessed from a real-time call

EC2 setup: 
1) Install python3.8 by running the command: sudo amazon-linux-extras install python 3.8
2) Install pip by running the command: curl -O https://bootstrap.pypa.io/get-pip.py
3) Check pip version by running from python (instead of invoking pip directly...for some reason, the EC2 instances doesn't like this): python3.8 -m pip --version
4) using 'python3.8 -m pip instal ...', install the following packages: robin-stocks, numpy, pytz, dropbox


To run the code on personal macine: python dataCollector.py
on EC2: python3.8 dataCollector.py