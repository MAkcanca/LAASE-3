#!/bin/bash
cd /home/pi/sw/tracker;

./tracker-camera.sh & 

while true; do
  /usr/bin/python ./tracker.py & >> ./log.txt;
  sleep 1;
done
