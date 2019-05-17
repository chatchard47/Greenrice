import os
import glob
import datetime
import time
import grovepi
import RPi.GPIO as GPIO
import subprocess
from influxdb import InfluxDBClient
import requests
import firebase
#from time import time
from grove_rgb_lcd import * # Connect Grove-LCD RGB Backlight to I2C port of Grove-Pi
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
 
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'
 
def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
 
def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f
temp_c=read_temp()
temp_humidity=4
#gas_sensor = 2
moisture_sensor=1
Vcc=16
relay_pump=23
#relay_led=24
grovepi.pinMode(temp_humidity,"INPUT")
#grovepi.pinMode(gas_sensor,"INPUT")
grovepi.pinMode(moisture_sensor,"INPUT")
grovepi.pinMode(Vcc,"OUTPUT")
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(relay_pump,GPIO.OUT)
#GPIO.setup(relay_led,GPIO.OUT)
# Generates the necessary payload to post
# temperature data into the InfluxDB
capture_interval = 25.0 # Every 25 seconds
#light_threshold=10;
client = InfluxDBClient('localhost','8086','root','root','testdb')
counter = 0
pump_last=0
pump=0
while True:
   try:
# setRGB(255,255,255) # white 
# strg = "Greenhouse Data" 
# print strg
# for i in range(0,16): 
#  setText(strg[:i]) 
#  time.sleep(.2) 
 time.sleep(1)   # Get temperature and humidity sensor value. First read might give previous residual value
 light_sensor_value = grovepi.analogRead(light_sensor)
 if light_sensor_value==0: 
  light_sensor_value=1 
 resistance = (float)(1023 - light_sensor_value) * 10 / light_sensor_value
 now=datetime.datetime.now()
        # Vcc Timing first 5 minutes of every hour
        if now.minute<15:# and now.minute<46:
            grovepi.digitalWrite(Vcc,1)
        else:
            grovepi.digitalWrite(Vcc,0)
        # Read sensor value from moisture sensor
 moisture = grovepi.analogRead(moisture_sensor)
 time.sleep(1)
 moisture = grovepi.analogRead(moisture_sensor)
 if moisture<100:
  moisture=0
 else:
  moisture=int(((1023-moisture)/10.23))
 time.sleep(1) #2 second delay for sensor stability. Total delay is capture_interval + 2
        [temp,humidity] = grovepi.dht(temp_humidity,1)
#        gas = grovepi.analogRead(gas_sensor)
        time.sleep(1)
 #second read done to get fresh value
 [temp,humidity] = grovepi.dht(temp_humidity,1)
#        gas = grovepi.analogRead(gas_sensor)
#  light_sensor_value = grovepi.analogRead(light_sensor)
#  resistance = (float)(1023 - sensor_value) * 10 / sensor_value
 time.sleep(1)
# print("Temp.: {0}".format(temp))
# print 'Temperature (Digital) = %.2f Deg C' % temp_c
#        print("Humidity: {0}".format(humidity))
#        print("Gas = %d" %gas)
#        print("Light sensor value = %d resistance =%.2f" %(light_sensor_value,  resistance))
#        print("Moisture: {0}".format(moisture))
now = datetime.datetime.now()
        if light_sensor_value<100 and now.hour>2 and now.hour<22:
                lights=1
                GPIO.output(relay_light,GPIO.LOW)
        else:
                GPIO.output(relay_light,GPIO.HIGH)
  lights=0
if (time.time()-fans_last)>30:
  if temp>32 or now.hour>23:
                        fans_last=time.time()
   fans=1
                        GPIO.output(relay_fans,GPIO.LOW)
                else:
                        GPIO.output(relay_fans,GPIO.HIGH)
   fans=0
if (time.time()-pump_last)>30:
                if moisture>0 and moisture<50:
                        pump_last=time.time()
   pump=1
                        GPIO.output(relay_pump,GPIO.LOW)
                else:
                        GPIO.output(relay_pump,GPIO.HIGH)
   pump=0
relay_status=""
 if lights==1:
  relay_status=relay_status+"L "
 if fans==1:
  relay_status=relay_status+"F "
 if pump==1:
  relay_status=relay_status+"P"
# print "Relay Status: ",relay_status
# print("-------------------")
 json_body = [
 {
 "measurement": "WeatherData",
 "tags": {
 "Project": "Green-house"
 },
 "fields": {
    "Temperature": temp,
    "Humidity": humidity,
    "Light": light_sensor_value,
    "Moisture": moisture,
    "Relay_Status": relay_status
         }
 }
 ]
try: #this should handle the case of writing -1 to influxdb
  client.write_points(json_body)
  try:
   currentTime = datetime.datetime.now()
   data = str(temp)+","+str(humidity)+","+str(moisture)+","+relay_status+","+str(currentTime)
   payLoad = {'deviceID':'{deviceid}', 'passwd':'{password}', 'data':data}
   r = requests.post("{server address}", data=payLoad)
   print r
  except:
   print "Data not put in server"
   pass
  try:
   URL = '{firebase-address}'
   payload = {"greenhouse":{"temperature":str(temp),"humidity":str(humidity),"moisture":str(moisture),"relay_status":relay_status,"currentTime":str(currentTime)}}
   firebase.put(URL, payload)
  except:
   print "Data not put into firebase"
   pass
 except:
  if counter == 10:
   subprocess.call(["avrdude", "-c", "gpio", "-p", "m328p"])#run avrdude
   counter  = 0
  else:
   counter = counter + 1
# if resistance>light_threshold:
#  GPIO.output(relay_led,GPIO.LOW)
# else:
#  GPIO.output(relay_led,GPIO.HIGH)
#  setRGB(255,127,0)
#      str = "Greenhouse Data Display"
#      for i in range(0,24):
#         setText(str[:i])
#         time.sleep(.1)
#      time.sleep(2)
#  setRGB(255,255,255)
#        setText("Temp:" + temp + " F      " + "Humidity :" + humidity + " %")
#  time.sleep(2)
#        setText("Moisture:" + moisture + "       " + "Gas :" + gas)
#  time.sleep(2)
except KeyboardInterrupt:
 GPIO.output(relay_fans,GPIO.HIGH)
 GPIO.output(relay_pump,GPIO.HIGH)
 GPIO.output(relay_light,GPIO.HIGH)
 grovepi.digitalWrite(Vcc,0)
# GPIO.output(relay_led,GPIO.HIGH)
        break
except: #this should handle the case of data error from sensors themselves
        if counter == 10:
  subprocess.call(["avrdude", "-c", "gpio", "-p", "m328p"])#run avrdude
  counter  = 0
 else:
  counter = counter + 1
time.sleep(capture_interval) #sleep is done irrespective of data get or not
