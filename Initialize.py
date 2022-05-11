import os, time
from sys import argv

## Need to find and pass in arguments to the Main.py for dev testing 
if len(argv) > 1:
    args = argv[1:]
    arguments = " ".join(argv[1:])
else:
    arguments = ""

while 1:
    os.system("python Main.py " + arguments)
    print("Restarting...")
    time.sleep(1.5)
