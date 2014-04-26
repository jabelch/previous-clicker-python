import serial
import msvcrt
import sys
import os
import time
import calendar
#import datetime

class Clicker(object):
    def __init__(self, com, baud, file):
        self.myClickerMac = "57EB94"
        self.masterMode = True
        self.channel = "f41."
        self.filename = file
        self.question = 0
        self.macanswers = {}
        self.allmacs = {}
        self.com = com
        self.baud = baud
        self.ser = serial.Serial(com)
        self.ser.baudrate = baud
        self.curmac = ""   #leave this blank so our loop can catch it in testing (no master)
        self.carrierMode = False
        self.carrierTimeout = 300
        print self.ser
        
        print "Attempting to load MAC addresses from file"
        print calendar.timegm(time.gmtime())
        self.load()
        self.main()

    def load(self):
        if os.path.exists(self.filename):
            data = None
            with open(self.filename, "rb") as f:
                data = f.readlines()
            for line in data:
                mac = line.rstrip()
                # self.allmacs[mac] = '0'
                self.loadBytes(mac)
        print "Loaded " + str(len(self.allmacs)) + " MAC addresses from file"

    def validateMac(self, mac):
        if not len(mac) == 6:
            return False
        else:
            return True

    def save(self):
        with open(self.filename, "wb") as f:
            for mac in self.allmacs.keys():
                if self.validateMac(mac) == True:
                    f.write(mac + "\n")
                #else:
                #    print mac + ": " + str(len(mac))
        print "Saved " + str(len(self.allmacs)) + " MAC addresses to file"
        #print self.allmacs
        
    def loadBytes(self, macstr):
        mac = int(macstr, 16)
        macbytes = []
        a = (mac & 0xff0000) >> 16
        b = (mac & 0x00ff00) >> 8
        c = (mac & 0x0000ff)
        macbytes.append(a)
        macbytes.append(b)
        macbytes.append(c)

        if len(macbytes) == 3:
            #Ignore Answer here, save value as byte representation of MAC
            self.allmacs[macstr] = "".join(chr(i) for i in macbytes)
        else:
            pass

    def massSend(self, answer=None):
        if answer:
            self.write("c" + str(answer))

        for key, value in self.allmacs.iteritems():
            strline = "k" + value + "."
            self.write(strline)
            self.write(self.channel)
            self.write("s")
            
            done = False
            buffer = ""
            while not done:
                buffer = buffer + self.ser.read(self.ser.inWaiting())
                if 'z' in buffer:
                    done = True
        print "Mass Send Done"

    def setMyClicker(self, inputstring):
        input = inputstring.split(" ")
        mac = input[1]
        self.myClickerMac = mac
        print "\nSet master listen MAC to: " + self.myClickerMac

    def nextQuestion(self):
        self.question += 1

    def main(self):

        done = False

        global last_received
        buffer = ''
        inputstr = ''
        #Main loop handles both serial input and output
        #It first checks the serial port for any input, adding
        #it to the buffer until it recieves a newline character.
        #Control then goes to a non-blocking section to accept
        #user input. When character 13 is recieved (ENTER) it sends
        #the contents of inputstr to the serial device.
        #(ESC) quits the program completely.
        while not done:
            try:
                
                #Handle serial input
                buffer = buffer + self.ser.read(self.ser.inWaiting())
                if '\n' in buffer:
                    lines = buffer.split('\n') # Guaranteed to have at least 2 entries

                    try:
                        if "<p>" in buffer and "</p>" in buffer:
                            #print "FOUND <P></p>" + str(len(buffer))
                            #curmac = ""
                            for packet in lines[:-1]:
                                p = packet.split(",")
                                mac = (p[0].rstrip()).replace("<p>", "").replace(" ", "")
                                ans = (p[1].rstrip()).replace("</p>", "")
                                
                                if self.validateMac(mac) == True:       #Validate the mac is the proper length so we don't work on bad data
                                    if not self.myClickerMac == mac:    #If the recorded mac isn't the master mac, load it in our list
                                        self.loadBytes(mac)
                                    if self.myClickerMac == mac and self.masterMode:    #If we're in master mode this is master: save or mass send
                                        #print self.curmac + " CURRENT MAC"
                                        #print mac + " serial MAC"
                                        if True:#if self.curmac != mac:     #comment this out when running for real
                                            if ans == '?':      #save
                                                self.save()
                                            elif ans == '0':
                                                self.write('j')
                                                print "Entering Constant Carrier Mode"

                                                self.carrierMode = True
                                                startTime = calendar.timegm(time.gmtime())
                                                curTime = startTime

                                                while self.carrierMode and (curTime - startTime) < self.carrierTimeout:
                                                    curTime = calendar.timegm(time.gmtime())
                                                    print curTime - startTime
                                                    time.sleep(5)

                                                self.carrierMode = False
                                                self.write("c1s")
                                                mac = ""
                                                ans = ""
                                                buffer = lines[-1]
                                                break

                                            else:               #mass send answer
                                                self.massSend(answer=ans)
                                    self.curmac = mac
                        # else:
                        print buffer

                        last_received = lines[-2]
                        #If the Arduino sends lots of empty lines, you'll lose the
                        #last filled line, so you could make the above statement conditional
                        #like so: if lines[-2]: last_received = lines[-2]
                        buffer = lines[-1]
                    except:
                        print "Bad parse:"
                        print mac
                        buffer = ""
                        self.curmac = ""
                        
                #Handle serial writes
                #Check input 

                if msvcrt.kbhit():
                    c = msvcrt.getch()
                    #print ord(c)
                    if ord(c) == 43:    # plus '+'
                        self.save()
                    elif ord(c) == 27:  #Escape
                        if inputstr:
                            inputstr = ''
                        else:
                            #Exit loop completely
                            done = True
                            self.save()
                    elif ord(c) == 13:  #Enter
                        if 'y' in inputstr:
                            self.setMyClicker(inputstr)
                            inputstr = ''
                            continue
                        elif 'q' in inputstr:
                            self.masterMode = True if not self.masterMode else False
                            print "\nMaster listen mode is " + ("ON and listening for MAC Address " + str(self.myClickerMac) if self.masterMode else "OFF")
                            inputstr = c
                            sys.stdout.write("%s" % (c))
                            sys.stdout.flush()
                            #continue
                        elif 'f' in inputstr:
                            self.channel = inputstr
                        elif 'n' in inputstr:
                            self.nextQuestion()
                        elif 'm' in inputstr:
                            self.massSend()
                            inputstr = ''
                            continue
                        #Send our input to the serial port
                        print("\n")
                        self.write(inputstr)
                        inputstr = ''
                    elif ord(c) == 8:   #Backspace
                        inputstr = inputstr[0:-1]
                        sys.stdout.write("\n%s" % (inputstr))
                        sys.stdout.flush()
                    else:
                        #Add character to the input string
                        inputstr = inputstr + c
                        sys.stdout.write("%s" % (c))
                        sys.stdout.flush()
            except:
                self.save()

    def write(self, data):
        self.ser.write(data)

if __name__=="__main__":
    clicker = Clicker('COM3', 115200, "macset.txt")
    
    # data = raw_input("Enter Something Here")
    # clicker.ser.write(data)
