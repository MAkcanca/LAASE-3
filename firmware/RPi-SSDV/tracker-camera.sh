#!/bin/bash
cd /home/pi/sw/tracker;

# i=1
# while true; do
for ((i=0; ;i++)); do

  # if at least 200 MB free disk space
  # if (( $(df /dev/root | awk 'NR==2{print $4}') > 204800 )); then
  if [ `df | grep /dev/root | awk '{print $4}'` -gt 204800 ]; then

    # echo `date +%Y%m%d-%H%M%S`
    
    # gps_latitude = grep lat ./gps-data.txt | awk '{print $2}'
    # gps_longitude = `grep lon ./gps-data.txt | awk '{print $2}'`
    
    echo "taking picture #${i}"
    gps_altitude=`grep alt ./gps-data.txt | awk '{print $2}'`
    gps_exiftags=`grep exif ./gps-data.txt`
    filename=`date +%Y%m%d-%H%M%S`_${gps_altitude}_${i}
    
    /usr/bin/raspistill -n -w 2592 -h 1944 -t 1000 -e jpg -q 90 -ex auto -mm matrix -o ./pics/${filename}.jpg ${gps_exiftags:6:999}
    # /usr/bin/raspistill -n -w 128 -h 128 -t 1000 -e jpg -q 90 -ex auto -mm matrix -o ./pics/${filename}.jpg ${gps_exiftags:6:999}

    if ! ((i % 3)); then
      echo "taking SSDV picture #${i}"
      gps_altitude=`grep alt ./gps-data.txt | awk '{print $2}'`
      gps_exiftags=`grep exif ./gps-data.txt`
      filename=`date +%Y%m%d-%H%M%S`_${gps_altitude}_${i}
      # 400x256
      # 512x288
      # 272x208
      # 256x176
      /usr/bin/raspistill -n -w 272 -h 176 -t 1000 -e jpg -q 90 -ex auto -mm matrix -o ./ssdvpics/${filename}.jpg ${gps_exiftags:6:999}
      if [ $gps_altitude ]; then
        echo "annotating SSDV image"
        # backup
        cp ./ssdvpics/${filename}.jpg ./ssdvpics/${filename}.jpg.orig
        # echo "cp done"
        /usr/bin/convert ./ssdvpics/${filename}.jpg -fill white -undercolor '#00000040' -gravity SouthWest -annotate +0+0 " Altitude: ${gps_altitude}m " ./ssdvpics/${filename}.jpg
        # echo "convert done"
      fi
    fi
  
  
    if ! ((i % 10)); then
      echo "taking video #${i}"
      gps_altitude=`grep alt ./gps-data.txt | awk '{print $2}'`
      sleep 1
      # 640x360
      /usr/bin/raspivid -n -w 854 -h 480 -t 20000 -ex auto -mm matrix -fps 25 -b 2000000 -o ./video/`date +%Y%m%d-%H%M%S`_${gps_altitude}_${i}.h264
    fi

  fi
    
  sleep 15;
done
