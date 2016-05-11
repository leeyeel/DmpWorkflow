"""
Created on Mar 25, 2016

@author: zimmer
"""
import os
import sys
import copy
import os.path
import random
import shlex
import string
import subprocess as sub
import time
import re
import datetime
from StringIO import StringIO
from xml.dom import minidom as xdom

def getSixDigits(number,asPath=False):
    """ since we can have many many streams, break things up into chunks, 
        this should make sure that 'ls' is not too slow. """
    if not asPath: return str(number).zfill(6)
    else:
        if number<100:
            return str(number).zfill(2)
        else:
            my_path = []
            rest = copy.deepcopy(number)
            blocks = [100000,10000,1000,100]
            for b in blocks:
                value, rest = divmod(rest,b)
                #print b, value, rest
                if value:
                    padding = "".join(["x" for i in range(len(str(b))-1)])
                    my_path.append("%i%s"%(value,padding))
                    rest = rest
            my_path.append(str(rest).zfill(2))
            return "/".join([str(s) for s in my_path])

def query_yes_no(question):
    print question+" [yes/no]"
    ret = False
    yes = set(['yes','y', 'ye', ''])
    no = set(['no','n'])
    choice = raw_input().lower()
    if choice in yes: ret = True
    elif choice in no: ret = False
    else:
        sys.stdout.write("Please respond with 'yes' or 'no', aborting\n")
        ret = False
    return ret

def exceptionHandler(exception_type, exception, traceback):
    # All your trace are belong to us!
    # your format
    print "%s: %s" % (exception_type.__name__, exception)


def random_string_generator(size=16, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def makeSafeName(srcname):
    rep = {".": "d", "+": "p", "-": "n"}
    for key in rep:
        srcname = srcname.replace(key, rep[key])
    return srcname


def pwd():
    # Careful, won't work after a call to os.chdir...
    return os.environ['PWD']


def mkdir(Dir):
    if not os.path.exists(Dir):
        os.makedirs(Dir)
    return Dir


def rm(pwd):
    os.system("rm -rf %s" % pwd)


def mkscratch():
    if os.path.exists('/scratch/'):
        return mkdir('/scratch/%s/' % os.environ['USER'])
    elif os.path.exists('/tmp/'):
        return mkdir('/tmp/%s/' % os.environ['USER'])
    else:
        raise Exception('...')


def touch(path):
    with open(path, 'a'):
        os.utime(path, None)


def Ndigits(val, size=6):
    """ returns a N-digit integer with leading zeros """
    _sixDigit = "%i" % val
    return _sixDigit.zfill(size)


def safe_copy(infile, outfile, sleep=10, attempts=10, debug=False):
    if debug:
        print 'cp %s -> %s' % (infile, outfile)
    infile = infile.replace("@", "") if infile.startswith("@") else infile
    # Try not to step on any toes....
    sleep = parse_sleep(sleep)
    if infile.startswith("root:"):
        print 'file is on xrootd - switching to XRD library'
        cmnd = "xrdcp %s %s" % (infile, outfile)
    else:
        if "$" in infile: infile = os.path.expandvars(infile)
        if "$" in outfile: outfile = os.path.expandvars(outfile)
        cmnd = "cp %s %s" % (infile, outfile)
    i = 1
    while i < attempts:
        if (debug and i > 0):             
            print "Attempting to copy file..."
        status = sub.call(shlex.split(cmnd))
        if status == 0:
            return status
        else:
            print "%i - Copy failed; sleep %ss" % (i, sleep)
            time.sleep(sleep)
        i += 1
    raise IOError("Failed to copy file")


def parse_sleep(sleep):
    MINUTE = 60
    HOUR = 60 * MINUTE
    DAY = 24 * HOUR
    WEEK = 7 * DAY
    if isinstance(sleep, float) or isinstance(sleep, int):
        return sleep
    elif isinstance(sleep, str):
        try:
            return float(sleep)
        except ValueError:
            pass

        if sleep.endswith('s'):
            return float(sleep.strip('s'))
        elif sleep.endswith('m'):
            return float(sleep.strip('m')) * MINUTE
        elif sleep.endswith('h'):
            return float(sleep.strip('h')) * HOUR
        elif sleep.endswith('d'):
            return float(sleep.strip('d')) * DAY
        elif sleep.endswith('w'):
            return float(sleep.strip('w')) * WEEK
        else:
            raise ValueError
    else:
        raise ValueError


def sleep(sleep):
    return time.sleep(parse_sleep(sleep))


def get_resources():
    import resource
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return '''usertime=%s systime=%s mem=%s mb
           ''' % (usage[0], usage[1],
                  (usage[2] * resource.getpagesize()) / 1000000.0)


def camelize(myStr):
    d = "".join(x for x in str(myStr).title() if not x.isspace())
    return d


def random_with_N_digits(n):
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return random.randint(range_start, range_end)

def convertHHMMtoSec(hhmm):
    vals = re.split(":",hhmm)
    if len(vals) == 2:
        h, m = vals[0], vals[1]
        s = 0
    elif len(vals)==3:
        h, m, s = vals[0], vals[1], vals[2]
    else:
        raise Exception("not well formatted time string")
    return float(datetime.timedelta(hours=int(h),minutes=int(m),seconds=int(s)).total_seconds())

class JobXmlParser(object):
    def __init__(self,domInstance,parent="Job",setVars=True):
        self.setVars = setVars
        self.out = {}
        elems = xdom.parse(StringIO(domInstance)).getElementsByTagName(parent)
        if len(elems) > 1:
            print 'found multiple job instances in xml, will ignore everything but last.'
        if not len(elems):
            raise Exception('found no Job element in xml.')
        self.datt = dict(zip(elems[-1].attributes.keys(), [v.value for v in elems[-1].attributes.values()]))
        if setVars:
            for k, v in self.datt.iteritems():
                os.environ[k] = v
        self.nodes = [node for node in elems[-1].childNodes if isinstance(node, xdom.Element)]
    def __extractNodes__(self):
        """ private method, do not use """
        for node in self.nodes:
            name = str(node.localName)
            if name == "JobWrapper":
                self.out['executable'] = node.getAttribute("executable")
                self.out['script'] = node.firstChild.data
            else:
                if name in ["InputFiles", "OutputFiles"]:
                    my_key = "File"
                else:
                    my_key = "Var"
                section = []
                for elem in node.getElementsByTagName(my_key):
                    section.append(dict(zip(elem.attributes.keys(), [v.value for v in elem.attributes.values()])))
                self.out[str(name)] = section
                del section
        return self.out
    def __setVars__(self):
        """ private method, do not use """
        if self.setVars:
            for var in self.out['MetaData']:
                key = var['name']
                value = var['value']
                if "$" in value:
                    value = os.path.expandvars(value)
                os.environ[key] = value
                var['value'] = value
                # expand vars
        self.out['atts'] = self.datt
        if 'type' in self.datt:
            os.environ["DWF_TYPE"] = self.datt["type"]
        for var in self.out['InputFiles'] + self.out['OutputFiles']:
            if '$' in var['source']:
                var['source'] = os.path.expandvars(var['source'])
            if '$' in var['target']:
                var['target'] = os.path.expandvars(var['target'])
            # print var['source'],"->",var['target']
        return self.out
    def getResult(self):
        out = self.out
        out.update(self.__extractNodes__())
        out.update(self.__setVars__())
        return out

def parseJobXmlToDict(domInstance, parent="Job", setVars=True):
    xp = JobXmlParser(domInstance,parent=parent,setVars=setVars)
    out = xp.getResult()
    return out