#!/bin/bash
cd /home/pi/sw/tracker;

cnt_ssdv=0
cnt_video=0

for ((i=0; ;i++)); do

  # if at least 200 MB free disk space
  # if (( $(df /dev/root | awk 'NR==2{print $4}') > 204800 )); then
  if [ `df | grep /dev/root | awk '{print $4}'` -gt 204800 ]; then
    
    echo "taking picture #${i}"
    gps_altitude=`grep alt ./gps-data.txt | awk '{print $2}'`
    gps_exiftags=`grep exif ./gps-data.txt`
    filename=`date +%Y%m%d-%H%M%S`_${gps_altitude}_${i}
    
    # /usr/bin/raspistill -n -w 2592 -h 1944 -t 1000 -e jpg -q 90 -ex auto -mm matrix -o ./pics/${filename}.jpg ${gps_exiftags:6:999}
    /usr/bin/raspistill -n -w 128 -h 128 -t 1000 -e jpg -q 90 -ex auto -mm matrix -o ./pics/${filename}.jpg ${gps_exiftags:6:999}

    if ! ((i % 3)); then
      echo "taking SSDV picture #${cnt_ssdv}"
      sleep 1
      gps_altitude=`grep alt ./gps-data.txt | awk '{print $2}'`
      gps_exiftags=`grep exif ./gps-data.txt`
      filename=`date +%Y%m%d-%H%M%S`_${gps_altitude}_${cnt_ssdv}
      
      # 400x256
      # 512x288
      # 272x208
      # 256x176
      /usr/bin/raspistill -n -w 272 -h 176 -t 1000 -e jpg -q 90 -ex auto -mm matrix -o ./ssdvpics/${filename}.jpg ${gps_exiftags:6:999}
      if [ $gps_altitude ]; then
        echo "annotating SSDV image: ${gps_altitude}m"
        # backup
        cp ./ssdvpics/${filename}.jpg ./ssdvpics/${filename}.jpg.orig
        /usr/bin/convert ./ssdvpics/${filename}.jpg -fill white -undercolor '#00000040' -gravity SouthWest -annotate +0+0 " Altitude: ${gps_altitude}m " ./ssdvpics/${filename}.jpg
      fi
      cnt_ssdv=$((cnt_ssdv+1))
    fi
  
    if ! ((i % 10)); then
      echo "taking video #${cnt_video}"
      sleep 1
      gps_altitude=`grep alt ./gps-data.txt | awk '{print $2}'`
      filename=`date +%Y%m%d-%H%M%S`_${gps_altitude}_${cnt_ssdv}
      # 640x360
      /usr/bin/raspivid -n -w 854 -h 480 -t 20000 -ex auto -mm matrix -fps 25 -b 2000000 -o ./video/${filename}.h264
      cnt_video=$((cnt_video+1))
    fi

  fi
    
  sleep 15
done
