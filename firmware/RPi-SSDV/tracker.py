# x-f, 2013
# space.people.lv
# Raspberry Pi SSDV payload
# ----------------------------------------------------------------------------

import serial
import os
import time
from time import gmtime, strftime
import subprocess
import demjson as json
import crcmod

gps_time_set = False

RADIO_CALLSIGN = "RASA"
RADIO_BAUDRATE = 300

# ----------------------------------------------------------------------------

# lcnt = 0
def mylog(string):
  # global lcnt
  # print str(lcnt) + ": " + str(string)
  print "[" + strftime("%Y-%m-%d %H:%M:%S", gmtime()) + "] " + str(string)
  # lcnt += 1

mylog("starting")

# function for crc16CCITT0xFFFF
crc16f = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000) 

def radio_send(data):
  global RADIO_BAUDRATE
  
  NTX2 = serial.Serial('/dev/ttyAMA0', RADIO_BAUDRATE, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_TWO) 
  NTX2.write(data)
  # mylog(data)
  time.sleep(0.2)
  NTX2.flush()
  time.sleep(0.2)
  NTX2.close()


def gps_setup():
  mylog("Setting up GPS..")
  
  # GPS = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
  # GPS.flush()
  # time.sleep(0.2)
  
  setNMEAoff = bytearray.fromhex("B5 62 06 00 14 00 01 00 00 00 D0 08 00 00 80 25 00 00 07 00 01 00 00 00 00 00 A0 A9")
  gps_sendUBX(setNMEAoff, len(setNMEAoff))
  # GPS.flush()
  # time.sleep(0.2)
  
  setNavmode = bytearray.fromhex("B5 62 06 24 24 00 FF FF 06 03 00 00 00 00 10 27 00 00 05 00 FA 00 FA 00 64 00 2C 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 16 DC")
  gps_sendUBX(setNavmode, len(setNavmode))
  # GPS.flush()
  # time.sleep(0.2)
  
  # GPS.flush()
  
  # iztiira visu, kas iekraajies
  GPS = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
  n = GPS.inWaiting()
  if n:
    GPS.read(n)
  GPS.close()
  
  mylog("GPS setup done")


def gps_poll(sentence_type="00*33"):
  gps_data = {
    "time": "00:00:00",
    "date": "0000-00-00",
    "latitude": 0,
    "longitude": 0,
    "altitude": 0,
    "speed": 0,
    "fixq": 0,
    "satellites": 0,
    "vspeed": 0,
  }
  
  GPS = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
  time.sleep(0.2)
  GPS.flush()
  time.sleep(0.2)
  
  GPS.write("$PUBX," + sentence_type + "\r\n")
  time.sleep(0.2)
  GPS.flush()
  time.sleep(0.2)
  GPS.close()
    
  GPS = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
  GPS.flush()
  time.sleep(0.2)
  
  line = GPS.readline().strip()
  if line:
    # mylog(line)
    # do something and return the parsed data
    # return line
    
    if line != "" and line.startswith("$PUBX"): # while we don't have a sentence
      line = line.split(",") # split sentence into individual fields
      
      # $PUBX,04,152045.00,301213,141645.00,1773,141645.00,-151518,-3226.618,21*00
      # $PUBX,00,152047.00,5708.89443,N,02450.21266,E,75.687,G3,27,30,3.420,17.85,0.130,,2.07,3.22,2.68,5,0,0*61
      
      if line[1] == "00" or line[1] == "04":        
        tmp_time = line[2]
        tmp_time = float(tmp_time)
        string = "%06i" % tmp_time
        hours = string[0:2]
        minutes = string[2:4]
        seconds = string[4:6]
        tmp_time = hours + ':' + minutes + ':' + seconds # the final time string in form 'hh:mm:ss'
        gps_data["time"] = tmp_time
      
      if line[1] == "00":
        lat = gps_DegreeConvert(line[3])
        if line[4] == "S": lat *= -1
        gps_data["latitude"] = round(lat, 5)
        lon = gps_DegreeConvert(line[5])
        if line[6] == "W": lon *= -1
        gps_data["longitude"] = round(lon, 5)
        gps_data["altitude"] = int(round(float(line[7])))
        fixq = line[8]
        if fixq == "NF": fixq = 1
        if fixq == "G2": fixq = 2
        if fixq == "G3": fixq = 3
        gps_data["fixq"] = fixq
        gps_data["speed"] = int(round(float(line[11])))
        gps_data["vspeed"] = round(float(line[13]), 1) * -1 # UKHAS style
        if gps_data["vspeed"] > -0.01 and gps_data["vspeed"] < 0.01: 
          gps_data["vspeed"] = 0
        gps_data["satellites"] = int(line[18])
        
      if line[1] == "04":
        tmp_date = line[3]
        tmp_date = int(tmp_date)
        string = "%06i" % tmp_date
        day = string[0:2]
        month = string[2:4]
        year = 2000 + int(string[4:6])
        tmp_date = str(year) + '-' + month + '-' + day
        if year == 2013 or year == 2014:
          gps_data["date"] = tmp_date
    
    return gps_data
    
  else:
    mylog("no line")
    # no values
    return gps_data


# http://us.cactii.net/~bb/gps.py
def gps_DegreeConvert(degrees):
  deg_min, dmin = degrees.split('.')
  degrees = int(deg_min[:-2])
  minutes = float('%s.%s' % (deg_min[-2:], dmin))
  decimal = degrees + (minutes/60)
  return decimal


# function to send commands to the GPS 
def gps_sendUBX(MSG, length):
  GPS = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
  GPS.flush()
  time.sleep(0.2)
  
  # mylog("Sending UBX Command: ")
  ubxcmds = ""
  for i in range(0, length):
    GPS.write(chr(MSG[i])) #write each byte of ubx cmd to serial port
    ubxcmds = ubxcmds + str(MSG[i]) + " " # build up sent message debug output string
  GPS.write("\r\n") #send newline to ublox
  # mylog(ubxcmds) #print debug message
  # mylog("UBX Command Sent...")
  
  GPS.flush()
  time.sleep(0.2)
  GPS.close()


def get_temperatures():
  result = {
    "cpu_temp": 0,
    "gpu_temp": 0,
  }
  
  try:
    p = subprocess.Popen('cat /sys/class/thermal/thermal_zone0/temp', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
      cpu_temp = round(float(float(line)/10 % float(line)/100), 1)
      result["cpu_temp"] = cpu_temp
    retval = p.wait()
    
    p = subprocess.Popen('/opt/vc/bin/vcgencmd measure_temp', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
      tmp = line.split("=")
      tmp = tmp[1].split("'")
      gpu_temp = float(tmp[0])
      result["gpu_temp"] = gpu_temp
    retval = p.wait()
  except:
    print "fail"
  
  return result


# ----------------------------------------------------------------------------

# counters = {}
# counters["sentence_id"] = 0
# counters["image"] = 0
# counters["image-ssdv"] = 0
# open("./counters.json", 'w').write(json.encode(counters))


radio_send("\n\n--= space.people.lv =--\n\n")

mylog("reading counters")

tmp = open("./counters.json", 'r').read()
counters = json.decode(tmp)
# print counters
sentence_id = counters["sentence_id"]
image_seq = counters["image"]
image_ssdv_seq = counters["image-ssdv"]

# mylog("setting up GPS..")
# gps_setup()
# mylog("  ..done")


while True:
# if True:
  try:

    gps_setup()
    gps_data = gps_poll()

    if gps_time_set == False:
      mylog("system time not set")
      data = gps_poll("04*37")
      if data["date"] != "0000-00-00" and data["time"] != "00:00:00":
        mylog("setting time: " + data["date"] + " " + data["time"])
        os.system("sudo date +%Y-%m-%d -s " + data["date"] + " > /dev/null")
        os.system("sudo date +%T -s " + data["time"] + " > /dev/null")
        gps_time_set = True


    image_filename = strftime("%Y%m%d-%H%M%S", gmtime()) + "_" + str(image_ssdv_seq)

    mylog("taking SSDV picture #" + str(image_ssdv_seq) + "..")
    # 400x256
    # 512x288
    # 272x208
    # 256x176
    os.system("/usr/bin/raspistill -n -w 272 -h 176 -t 1000 -e jpg -q 90 -ex auto -mm matrix -o ./ssdvpics/" + image_filename + ".jpg")
    mylog("  ..done")
    
    if gps_data["fixq"] == 3 and gps_data["altitude"] > 0:
      mylog("annotating")
      cmd = "/usr/bin/convert ./ssdvpics/" + image_filename + ".jpg"
      cmd += " -fill white -undercolor '#00000040' -gravity SouthWest"
      cmd += " -annotate +0+0 ' Altitude: " + str(gps_data['altitude']) + "m '"
      # cmd += " -font Tahoma -pointsize 6 -density 50"
      cmd += " ./ssdvpics/" + image_filename + "-osd.jpg"
      os.system(cmd)
      image_filename += "-osd"
    
    os.system("/home/pi/sw/ssdv/ssdv -e -c " + RADIO_CALLSIGN + " -i " + str(image_ssdv_seq) + " ./ssdvpics/" + image_filename + ".jpg ./current.ssdv > /dev/null 2>&1")
    mylog("encoded SSDV picture")
  

    f = open("./current.ssdv", "rb"); 
    packet = f.read(256); 
    i = 0
    while packet != "":

      mylog("polling GPS..")
      gps_data = gps_poll()
      mylog("  ..done")
      # mylog(gps_data)

      if i % 5 == 0:
        mylog("taking picture #" + str(image_seq) + "..")
        # os.system("/usr/bin/raspistill -n -w 2592 -h 1944 -t 1000 -e jpg -q 90 -ex auto -mm matrix -o ./pics/" + strftime("%Y%m%d-%H%M%S", gmtime()) + "_" + str(image_seq) + ".jpg &")
        mylog("  ..done")
        image_seq += 1
      
      # telemetrija
      datastring = RADIO_CALLSIGN + ","
      datastring += str(sentence_id) + ","
      datastring += str(gps_data["time"]) + ","
      datastring += str(gps_data["latitude"]) + ","
      datastring += str(gps_data["longitude"]) + ","
      datastring += str(gps_data["altitude"]) + ","
      datastring += str(gps_data["speed"]) + ","
      datastring += str(gps_data["vspeed"]) + ","
      datastring += str(gps_data["satellites"]) + ","
      
      temps =  get_temperatures()
      datastring += str(temps["cpu_temp"]) + ","
      datastring += str(temps["gpu_temp"])
      
      datastring += "*" + str(hex(crc16f(datastring))).upper()[2:]
      datastring = "$$" + datastring
      mylog(datastring)
      telemetry = bytearray.fromhex("00 00 00") + "\n\n$" + datastring + "\n\n"

      radio_send(telemetry + packet)
      # radio_send(telemetry)

      sentence_id += 1
      
      # ssdv pakete
      packet = f.read(256);
      
      i += 1
    f.close() 
  
    mylog("all packets sent")
  
  
    image_ssdv_seq += 1
    counters["sentence_id"] = sentence_id
    counters["image-ssdv"] = image_ssdv_seq
    counters["image"] = image_seq
  
    open("./counters.json", 'w').write(json.encode(counters))
  
    mylog("next cycle")
  

  except KeyboardInterrupt:
    quit()
