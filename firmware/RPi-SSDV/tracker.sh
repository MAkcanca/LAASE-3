#!/bin/bash
cd /home/pi/sw/tracker;
while true; do
  /usr/bin/python ./tracker.py &>> /home/pi/sw/tracker/log.txt;
  sleep 1;
done
