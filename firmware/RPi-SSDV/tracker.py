# x-f, 2013
# space.people.lv
# Raspberry Pi SSDV payload
# ----------------------------------------------------------------------------

import serial
import os
import time
from time import gmtime, strftime
import subprocess
import glob
import demjson as json
import crcmod


RADIO_CALLSIGN = "RASA"
RADIO_BAUDRATE = 1200

DS18B20_SENSOR_ID = "28-000003bb2414"

gps_time_set = False

# ----------------------------------------------------------------------------

def mylog(string):
  print "[" + strftime("%Y-%m-%d %H:%M:%S", gmtime()) + "] " + str(string)

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
        if year == 2014:
          gps_data["date"] = tmp_date
    
    return gps_data
    
  else:
    mylog("GPS: no line")
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
    "external_temp": 0,
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
    
    result["external_temp"] = ds18b20_read_temp()
  except:
    print "fail"
  
  return result


# http://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing/
def ds18b20_read_temp_raw():
  device_file = '/sys/bus/w1/devices/' + DS18B20_SENSOR_ID + '/w1_slave'
  catdata = subprocess.Popen(['cat',device_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  out,err = catdata.communicate()
  out_decode = out.decode('utf-8')
  lines = out_decode.split('\n')
  return lines

def ds18b20_read_temp():
  lines = ds18b20_read_temp_raw()
  ts = time.time()
  while lines[0].strip()[-3:] != 'YES':
    if time.time() - ts > 1:
      return 0
    time.sleep(0.2)
    lines = ds18b20_read_temp_raw()
  equals_pos = lines[1].find('t=')
  if equals_pos != -1:
    temp_string = lines[1][equals_pos+2:]
    temp_c = float(temp_string) / 1000.0
    return temp_c


# --------------------------------
# Exif for images
import math
import fractions

# http://stackoverflow.com/questions/10799366/geotagging-jpegs-with-pyexiv2
class Fraction(fractions.Fraction):
    """Only create Fractions from floats.

    >>> Fraction(0.3)
    Fraction(3, 10)
    >>> Fraction(1.1)
    Fraction(11, 10)
    """

    def __new__(cls, value, ignore=None):
        """Should be compatible with Python 2.6, though untested."""
        return fractions.Fraction.from_float(value).limit_denominator(99999)


def decimal_to_dms(decimal):
    """Convert decimal degrees into degrees, minutes, seconds.

    >>> decimal_to_dms(50.445891)
    [Fraction(50, 1), Fraction(26, 1), Fraction(113019, 2500)]
    >>> decimal_to_dms(-125.976893)
    [Fraction(125, 1), Fraction(58, 1), Fraction(92037, 2500)]
    """
    remainder, degrees = math.modf(abs(decimal))
    remainder, minutes = math.modf(remainder * 60)
    return [Fraction(n) for n in (degrees, minutes, remainder * 60)]

# --------------------------------

def dump_current_position(gps_data):
  current_position = ""
  if gps_data["fixq"] > 2:
    current_position += "alt: " + str(gps_data["altitude"]) + "\n"
    current_position += "exif: "
    current_position += " -x GPS.GPSLatitude=" + str(decimal_to_dms(gps_data["latitude"])[0]) + "/1," + str(decimal_to_dms(gps_data["latitude"])[1]) + "/1," + str(decimal_to_dms(gps_data["latitude"])[2]) + "/1"
    current_position += " -x GPS.GPSLatitudeRef=" + ("N" if gps_data["latitude"] < 0 else "N")
    current_position += " -x GPS.GPSLongitude=" + str(decimal_to_dms(gps_data["longitude"])[0]) + "/1," + str(decimal_to_dms(gps_data["longitude"])[1]) + "/1," + str(decimal_to_dms(gps_data["longitude"])[2]) + "/1"
    current_position += " -x GPS.GPSLongitudeRef=" + ("W" if gps_data["longitude"] < 0 else "E")
    current_position += " -x GPS.GPSAltitude=" + str(abs(gps_data["altitude"])) + "/1"
    current_position += " -x GPS.GPSAltitudeRef=" + ("1" if gps_data["altitude"] < 0 else "0") + "\n"
    
  open("./gps-data.txt", 'w').write(current_position)


# ----------------------------------------------------------------------------

# counters = {}
# counters["sentence_id"] = 0
# counters["ssdv-image"] = 0
# counters["ssdv-lastTXtime"] = 0
# open("./counters.json", 'w').write(json.encode(counters))


radio_send("\n\n--= space.people.lv =--\n\n")

mylog("reading counters")

tmp = open("./counters.json", 'r').read()
counters = json.decode(tmp)
sentence_id = counters["sentence_id"]
ssdv_image_seq = counters["ssdv-image"]
ssdv_lastTXtime = counters["ssdv-lastTXtime"]

# mylog("setting up GPS..")
# gps_setup()
# mylog("  ..done")

# DS18B20 sensor
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')


while True:
# if True:
  try:

    gps_setup()
    gps_data = gps_poll()
    
    # for images
    dump_current_position(gps_data)    

    if gps_time_set == False:
      mylog("system time not set")
      data = gps_poll("04*37")
      if data["date"] != "0000-00-00" and data["time"] != "00:00:00":
        mylog("setting time: " + data["date"] + " " + data["time"])
        os.system("sudo date +%Y-%m-%d -s " + data["date"] + " > /dev/null")
        os.system("sudo date +%T -s " + data["time"] + " > /dev/null")
        gps_time_set = True


    # find biggest image since the transmission of the previous one
    # encode and start transmitting
    
    files = glob.glob("./ssdvpics/2014*.jpg")
    files = sorted(files, key=os.path.getmtime)

    bigfile_filename = ""
    bigfile_filesize = 0
    for item in files:
      filemtime = os.stat(item)[8]

      if filemtime > ssdv_lastTXtime:
        if os.stat(item)[6] > bigfile_filesize:
          bigfile_filesize = os.stat(item)[6]
          bigfile_filename = item

    mylog("next SSDV pic: " + bigfile_filename)

    if bigfile_filename:
      image_filename = os.path.basename(bigfile_filename)
    
      cmd = "/home/pi/sw/ssdv/ssdv -e -c " + RADIO_CALLSIGN + " -i " + str(ssdv_image_seq) + " ./ssdvpics/" + image_filename + " ./current.ssdv > /dev/null 2>&1"
      os.system(cmd)
      mylog(cmd)
      mylog("encoded SSDV picture")
    
      ssdv_lastTXtime = time.time()
  

    f = open("./current.ssdv", "rb"); 
    packet = f.read(256); 
    i = 0
    while packet != "":

      # mylog("polling GPS..")
      gps_data = gps_poll()
      # mylog("  ..done")
      # mylog(gps_data)
      
      # for images
      dump_current_position(gps_data)    

      
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
      datastring += str(temps["gpu_temp"]) + ","
      datastring += str(temps["external_temp"])
      
      datastring += "*" + str(hex(crc16f(datastring))).upper()[2:].zfill(4)
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
  
  
    ssdv_image_seq += 1
    counters["sentence_id"] = sentence_id
    counters["ssdv-image"] = ssdv_image_seq
    counters["ssdv-lastTXtime"] = ssdv_lastTXtime
    open("./counters.json", 'w').write(json.encode(counters))
  
    mylog("next cycle")
  

  except KeyboardInterrupt:
    quit()
