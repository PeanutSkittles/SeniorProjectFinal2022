# -*- coding: utf-8 -*-
"""
Created on Sat May 21 12:48:29 2022

@author: Mike
"""

import sys                      # Import sys module
from time import sleep          # Import sleep from time
from time import time
import Adafruit_GPIO.SPI as SPI # Import Adafruit GPIO_SPI Module
import Adafruit_MCP3008         # Import Adafruit_MCP3008
import threading

init_time = time()

adc_resolution = (2**10)-1

SPI_TYPE = 'SW'     #Software 'Serial Peripheral Interface'
# Software SPI Configuration
CLK     = 26    # Set the Serial Clock pin
MISO    = 20    # Set the Master Input/Slave Output pin
MOSI    = 19    # Set the Master Output/Slave Input pin
CS      = 13    # Set the Slave Select

delay = 0.001       #delay in seconds
running = True

# Instantiate the mcp class from Adafruit_MCP3008 module and set it to 'mcp'. 
mcp = Adafruit_MCP3008.MCP3008(clk = CLK, cs = CS, miso = MISO, mosi = MOSI)

#Pin 7 = volt meter
volt_pin = 7
#Pin 6 = secondary current sensor
secondary_current_pin = 6
#Pin 5 = primary current sensor 1
primary_current_pin_1 = 5
#Pin 4 = primary current sensor 2
primary_current_pin_2 = 4

MAX_SECONDARY_CURRENT = 17.5
MAX_PRIMARY_CURRENT = 1.458

#Parameters for the ACS712 30A current sensor
v_ref = 3.3
sens_30 = 0.066
offset_30 = 0.025

#Parameters for the ACS712 5A current sensor
v_ref = 3.3
sens_5 = 0.185
offset_5_1 = 0
offset_5_2 = 0

#Parameters for the voltage sensor
magic_number = 41.87
volt_sens = 0.00489
volt_offset = 0

samples = 10

#global variables

average_voltage = 0
average_secondary_current = 0
average_primary_current_1 = 0
average_primary_current_2 = 0
power_level = 0

###############################################################################################
#Getting IP + sending data to website
import socket
import requests

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
ip_target = str(s.getsockname()[0])
port = "490"
s.close()
def send_data_to_web():
    while(True):
        global power_level
        sleep(1)
        requests.get(f'http://{ip_target}:{port}/power/{round(abs(power_level),3)}')
        
background_web = threading.Thread(target=send_data_to_web)
#background_web.daemon = True
background_web.start()

###############################################################################################
#E-ink display
import lib.epd2in9_V2 as epd2in9_V2
from PIL import Image,ImageDraw,ImageFont


epd = epd2in9_V2.EPD()
epd.init()
#epd.Clear(0xFF)

font18 = ImageFont.truetype('lib/Font.ttc', 18) #setting the font
    
test_image = Image.new('1', (epd.height, epd.width), 255)
test_draw = ImageDraw.Draw(test_image)
epd.display_Base(epd.getbuffer(test_image))

def display_eink():
    try:
        global running
        while (running):
            test_draw.rectangle((5, 5, 296, 128), fill = 255)
            test_draw.text((10, 5), 'Secondary Voltage: ' + str(round(average_voltage,3)), font = font18, fill = 0)
            test_draw.text((10, 25), 'Secondary Current: ' + str(round(average_secondary_current, 3)), font = font18, fill = 0)
            test_draw.text((10, 45), 'Watts: ' + str(round(abs(power_level), 3)), font = font18, fill = 0)
            test_draw.text((120, 45), 'Current ratio: ' + str(round(abs((average_primary_current_1+0.0000001)/(average_primary_current_2+0.0000001)), 3)), font = font18, fill = 0)
            test_draw.text((10, 65), 'Primary Current 1: ' + str(round(average_primary_current_1,3)), font = font18, fill = 0)
            test_draw.text((10, 85), 'Primary Current 2: ' + str(round(average_primary_current_2,3)), font = font18, fill = 0)
            test_draw.text((10, 105), 'IP: ' + ip_target+' : '+port, font = font18, fill = 0)
            newimage = test_image.crop([10, 10, 120, 50])
            test_image.paste(newimage, (10,10))  
            epd.display_Partial(epd.getbuffer(test_image))
    except KeyboardInterrupt:    
        epd2in9_V2.epdconfig.module_exit()
        exit()
        
background_display = threading.Thread(target=display_eink)
#background_rv.daemon = True
background_display.start()

###############################################################################################
#Getting sensor data
import math

def read_average_data(type_data, num_samples, adc_pin, sens, offset, delay_amount, RMS):
    try:
        average_max = 0
        for x in range(num_samples):
            average_max += get_max_value(type_data, num_samples, adc_pin, sens, offset, delay_amount)
        
        average_max = average_max / num_samples

    except KeyboardInterrupt:
        print("exit")
        
    return (average_max/RMS)

def get_max_value(type_data, num_samples, adc_pin, sens, offset, delay_amount):
    try:
        max_value = -999
        data = -999
        for x in range(num_samples):
            digital_read = mcp.read_adc(adc_pin)
            calc = (digital_read*v_ref)/(adc_resolution)
            
            if type_data == "VOLT":
                data = calc*(5-offset)
                sleep(delay_amount)
            if type_data == "ACS712":
                data = (calc-(v_ref/2))/sens + offset
                sleep(delay_amount)
                
            if data > max_value:
                max_value = data
        
    except KeyboardInterrupt:
        print("exit")
        
    return max_value

###############################################################################################
#Relay data
import RPi.GPIO as GPIO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
trip_percentage = 0.5

RELAY_PIN = 16
GPIO.setup(RELAY_PIN, GPIO.OUT)

def relay_demo():
    while True:
        GPIO.output(RELAY_PIN,GPIO.LOW)
        sleep(2)
        GPIO.output(RELAY_PIN,GPIO.HIGH)
        sleep(2)
    
def relay_main():
    while True:
        current_ratio = 1 - abs((average_primary_current_1+0.0000001)/(average_primary_current_2+0.0000001))
        #print(current_ratio)
        if current_ratio >= trip_percentage and (average_primary_current_1 > 1 or average_primary_current_2 > 1) :
            sleep(0.25)
            current_ratio = 1 - abs((average_primary_current_1+0.0000001)/(average_primary_current_2+0.0000001))
            if current_ratio >= trip_percentage and (average_primary_current_1 > 1 or average_primary_current_2 > 1):
                 GPIO.output(RELAY_PIN,GPIO.LOW)
            else:
                GPIO.output(RELAY_PIN,GPIO.HIGH)
        else:
            GPIO.output(RELAY_PIN,GPIO.HIGH)

background_relay = threading.Thread(target=relay_main)
#background_rv.daemon = True
background_relay.start()
###############################################################################################
##Main thread
try:
    print(f'elapsed: {round(time() - init_time,5)} seconds')
    while True:
        average_voltage = read_average_data("VOLT", samples, volt_pin, volt_sens, volt_offset, delay, 1)
        average_secondary_current = read_average_data("ACS712", samples, secondary_current_pin, sens_30, offset_30, delay, math.sqrt(2))
        average_primary_current_1 = read_average_data("ACS712", samples, primary_current_pin_1, sens_5, offset_5_1, delay, 1/2*math.sqrt(2))
        average_primary_current_2 = read_average_data("ACS712", samples, primary_current_pin_2, sens_5, offset_5_2, delay, 1/2*math.sqrt(2))
        power_level = average_voltage * average_secondary_current
except KeyboardInterrupt:
    GPIO.cleanup()
