from os import*
import subprocess
from random import*
from math import*
from signal import*

from kb import*

path="/home/victor/Music/music/"
playTool="sox"
listDirTool="find"
listFileTool="find"
infoTool="mid3v2"
fmtName="notext_tal"
supportedTypes=[".mp3"]

bShuffle=True
bRepeat=True

queueSize=30

try:
    from settings import*
    print("loaded \"settings.py\".")
except:
    print("no \"settings.py\" file loaded.")


# Apply settings
if playTool=="vlc":
    playCmd="vlc --qt-start-minimized --play-and-exit {}"
elif playTool=="sox":
    playCmd="play {}"
else:
    print("Unsupported playing tool.")
    print("Supported: vlc, sox.")
    exit(1)

if listDirTool=="find":
    listDirCmd="find {} -maxdepth 1 -mindepth 1 -type d"
else:
    print("Unsupported directory listing tool.")
    print("Supported: find.")
    exit(1)

if listFileTool=="find":
    listFileCmd="find {} -maxdepth 1 -mindepth 1 -type f"
else:
    print("Unsupported file listing tool.")
    print("Supported: find.")
    exit(1)

if infoTool=="none":
    infoCmd=None
elif infoTool=="mid3v2":
    infoCmd="mid3v2 -l {}"
else:
    print("Unsupported metadata listing tool")
    print("Supported: none, mid3v2.")
    exit(1)

if fmtName=="text":
    songFmtT="\"{T}\""
    songFmtTA="\"{T}\" by {A}"
    songFmtTAL="\"{T}\" by {A} on {L}"
    songFmtTL="\"{T}\" on {L}"
elif fmtName=="notext_tal":
    songFmtT="\"{T}\""
    songFmtTA="\"{T}\" - {A}"
    songFmtTAL="\"{T}\" - {A} ({L})"
    songFmtTL="\"{T}\" ({L})"
elif fmtName=="notext_atl":
    songFmtT="\"{T}\""
    songFmtTA="{A}: \"{T}\""
    songFmtTAL="{A}: \"{T}\" ({L})"
    songFmtTL="\"{T}\" ({L})"
else:
    print("Unsupported format name")
    print("Supported: text, notext_atl, notext_tal.")
    exit(1)

def scoreFunc(size):
    return round(sqrt(size))


### System funcs
def runAlone(fmt, arg):
    return subprocess.Popen([arg if i=="{}" else i for i in fmt.split()], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def runGetOutput(fmt, arg):
    p=subprocess.Popen([arg if i=="{}" else i for i in fmt.split()], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return iter(p.stdout.readline, b'')

### Playing vars & funcs
playerProcess=subprocess.Popen("true")
playQueue=[]

def isSong(filename):
    for ext in supportedTypes:
        if filename[-len(ext):]==ext:
            return True
    return False

### Classes

class PlayQueue:
    def __init__(self):
        self.content=[]
        self.cur=None
        self.bPaused=False

    def append(self, x):
        self.content.append(x)

    def tick(self):
        if not self.bPaused and playerProcess.poll() is not None:
            self.play()
            outputManager.lastCmd=""
            outputManager.display()

    def togglePause(self):
        if self.bPaused:
            if self.cur is None:
                self.play()
            else:
                self.resume()
        else:
            self.pause()

    def play(self):
        self.bPaused=False
        self.cur=None
        self.fill()
        if len(self.content):
            self.cur=self.content[0].desc()
            self.content[0].play()
            self.content.pop(0)

    def stop(self):
        self.bPaused=True
        self.cur=None
        self.fill()
        playerProcess.terminate()

    def resume(self):
        self.bPaused=False
        playerProcess.send_signal(SIGCONT)

    def pause(self):
        self.bPaused=True
        playerProcess.send_signal(SIGSTOP)
        #self.stop()

    def display(self):
        system('cls' if os.name == 'nt' else 'clear')
        if self.cur is not None:
            print("> ", self.cur, sep="")
        for i in self.content:
            print("  ", i.desc(), sep="")

    def getSize(self):
        return len(self.content)+int(self.cur is not None)

    def fill(self):
        while self.getSize()<queueSize:
            if not rootDir.addToQueue():
                break

class Song:
    def __init__(self, fn=None):
        self.filename=fn
        self.title=None
        self.artist=None
        self.album=None

        self.size=1
        self.gotInfo=False
        self.getInfo()

    def getInfo(self):
        if self.gotInfo:
            return
        else:
            self.gotInfo=True
        if self.filename is not None:
            # get file info
            if infoTool=="mid3v2":
                for line in runGetOutput(infoCmd, self.filename):
                    line=line.decode('utf-8').strip()
                    if line[0:4]=="TIT2":
                        self.title=line[5:]
                    elif line[0:4]=="TPE1":
                        self.artist=line[5:]
                    elif line[0:4]=="TALB":
                        self.album=line[5:]

    def desc(self):
        self.getInfo()
        if self.filename is None:
            return "Error - no filename"
        elif self.title is None:
            return self.filename
        else:
            # build using best format
            if self.artist is None and self.album is None:
                fmt=songFmtT
            elif self.album is None:
                fmt=songFmtTA
            elif self.artist is None:
                fmt=songFmtTL
            else:
                fmt=songFmtTAL
            return fmt.replace("{T}", str(self.title)).replace("{A}", str(self.artist)).replace("{L}", str(self.album))

    def play(self):
        if self.filename is None:
            print("Error - no filename")
            playQueue.stop()
            exit(2)
        global playerProcess
        if playerProcess.poll() is None:
            playerProcess.terminate()
        playerProcess=runAlone(playCmd, self.filename)

    def addToQueue(self):
        playQueue.append(self)
        if not bRepeat:
            self.size=0
        return True


class Directory:
    def __init__(self, p=None):
        self.path=p
        self.content=[]
        if p is not None:
            for line in runGetOutput(listDirCmd, self.path):
                line=line.decode('utf-8').strip()
                self.content.append(Directory(line))
                if self.content[-1].size==0:
                    self.content.pop()
            for line in runGetOutput(listFileCmd, self.path):
                line=line.decode('utf-8').strip()
                if isSong(line):
                    self.content.append(Song(line))
        self.update()

    def append(self, x):
        self.content.append(x)
        if self.content[-1].size==0:
            self.content.pop()
        self.update()

    def update(self):
        self.size=self.calcSize()
        self.shuffler=list(range(0,len(self.content)))
        if bShuffle:
            shuffle(self.shuffler)

    def calcSize(self):
        return sum([i.size for i in self.content])

    def addToQueue(self): # adds a child song to queue
        if len(self.content):
            maxi=(len(self.content))//2
            tmp=[]
            for i in self.shuffler[:maxi+1]:
                for j in range(scoreFunc(self.content[i].size)):
                    tmp.append(i)
            i=choice(tmp)
            self.shuffler.append(self.shuffler.pop(self.shuffler.index(i)))
            result=self.content[i].addToQueue()
            if not bRepeat:
                if self.content[i].size==0:
                    self.content.pop(i)
                self.update()
            return result
        return False

class OutputManager:
    def __init__(self):
        self.lastCmd=""
        self.mode="playlist"

    def display(self):
        if self.mode=="playlist":
            playQueue.display()
            print(self.lastCmd)
        elif self.mode!="manual":
            print("Unknow output mode!")
            playQueue.stop()
            exit(2)

### UI funcs

kb=KBHit()


rootDir=Directory()
#rootDir.append(Directory("/home/victor/Music/music/SomeRock/Lions in the street/"))
#rootDir.append(Directory("/home/victor/Music/music/SomeRock/Weezer/"))
rootDir.append(Directory(path+"SomeRock/"))

playQueue=PlayQueue()
outputManager=OutputManager()


while True:
    if kb.kbhit():
        c = kb.getch()
        if c=='h':
            print('''\
Help:
- Help    - Display this help page
- <Space> - Play/Pause (Pause=Stop when not available)
- Next    - Skip to next song
- Quit    - Stop and quit SMP
- Stop    - Stop the music''')

        if c==' ':
            playQueue.togglePause()
            outputManager.lastCmd="Play/Pause"
            outputManager.display()
        if c=='n':
            playQueue.play()
            outputManager.lastCmd="Next"
            outputManager.display()
        if c=='q':
            playQueue.stop()
            print("Quit")
            break
        if c=='s':
            playQueue.stop()
            outputManager.lastCmd="Stop"
            outputManager.display()
    playQueue.tick()