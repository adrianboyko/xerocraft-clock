import network
from sys import stdout
from time import sleep
from machine import Pin, PWM, ADC
from math import cos, radians, floor
from ntptime import settime
from utime import localtime
from credentials import ssid, pw

def connect_to_network(station: network.WLAN, ssid: str, pw: str):

    print("Deactivating...")
    station.active(False)
    print("Activating...")
    station.active(True)
    
    if not station.isconnected():
        print("Connecting to network...", end='')
        station.connect(ssid, pw)
        tries = 0
        while not station.isconnected():
            print(".", end='')
            tries += 1
            sleep(.2)

    print('\nNetwork Config:', station.ifconfig())

def load_bit_registers(x, symbol):
    digits  = [
        # x,a,b,c,d,e,f,g
        [ x,1,1,1,1,1,1,0 ], # 0
        [ x,0,1,1,0,0,0,0 ], # 1
        [ x,1,1,0,1,1,0,1 ], # 2
        [ x,1,1,1,1,0,0,1 ], # 3
        [ x,0,1,1,0,0,1,1 ], # 4
        [ x,1,0,1,1,0,1,1 ], # 5
        [ x,1,0,1,1,1,1,1 ], # 6
        [ x,1,1,1,0,0,0,0 ], # 7
        [ x,1,1,1,1,1,1,1 ], # 8
        [ x,1,1,1,1,0,1,1 ], # 9
    ]
    if symbol is None:
        bits = [x,0,0,0,0,0,0,0]
    elif isinstance(symbol, list):
        assert len(symbol) == 8, "Must provide list of eight 0/1 values"
        bits = symbol
    else:
        bits = digits[symbol]
    for bit in reversed(bits):
        ser.value(bit)
        srck.on()
        srck.off()

def load_digits(hr1, hr2, min1, min2):
    assert hr1 in [0, 1], "hr1 is {}!".format(hr1)
    digits = [(hr1, hr2), (1, min1), (1, min2)]
    #digits.reverse()
    for digit in digits:
        load_bit_registers(*digit)
    rck.on()
    rck.off()
    
def set_appropriate_duty(dim, amps):

    num_reads = 100
    sum = 0
    for n in range(num_reads):
        sum += amps.read()
    avg = sum / num_reads
    print("Avg analog reading: {}".format(avg)) 

    if avg < 15:
        duty = 1  # Max brightness (I'm avoiding 0)
    else:
        # This formula was determined by connecting clock to a variable voltage supply.
        # At each different Vin, the current measured by the clock was noted and the
        # duty cycle was set so that clock displayed a specific brightness as determined
        # by a "light meter" app on a smart-phone. A mathematical model was chosen and
        # Mathematica was used to determine the specific model parameters given the
        # experimental data.
        duty = floor(1023.0 - 1.0 / ((avg - 10.1991) / 15284.0))

    # Clamp, just to be safe:
    duty = max(1, duty)
    duty = min(1022, duty)
    
    print("Duty set to: {}".format(duty)) 
    dim.duty(duty)

# This code assumes a TPIC6B595 Shift Register
ser  = Pin(12, Pin.OUT, value=0)  # SERIN is pin  3 on shift register
srck = Pin(14, Pin.OUT, value=0)  # SRCK  is pin 13 on shift register
rck  = Pin(16, Pin.OUT, value=0)  # RCK   is pin 12 on shift register
up   = Pin(4,  Pin.IN)
down = Pin(5,  Pin.IN)
amps = ADC(0)

# "dim" drives NOT G (pin 9) on shift register. 
# Because we're driving a NOT pin, 0 is HIGH duty and 1023 is LOW duty.
# Frequency is 1-1000 (Hz)
# Duty cycle is 0-1023
dim = PWM(Pin(13))
dim.freq(500)

load_digits(1,8,8,8)
set_appropriate_duty(dim, amps)
station = network.WLAN(network.STA_IF)
connect_to_network(station, ssid, pw)

disp_mins = None
while True:
        
    try:    
        settime()
        print("settime success")
    except Exception as e:
        print("settime failure: "+str(e))
        
    (_, _, _, hour, minutes, seconds, _, _) = localtime()

    if disp_mins != minutes:
        disp_mins = minutes
        
        # Adjust hour to AZ time in 12 hour format.
        az_hour = hour - 7  # No DST in AZ
        if az_hour > 12:
           az_hour -= 12
        if az_hour < 1:
           az_hour += 12

        hr_str = "{:02d}".format(az_hour)
        min_str = "{:02d}".format(minutes)
        hr1 = int(hr_str[0])
        hr2 = int(hr_str[1])
        min1 = int(min_str[0]) 
        min2 = int(min_str[1])
        
        load_digits(hr1, hr2, min1, min2)      

    sleep(60-seconds)


