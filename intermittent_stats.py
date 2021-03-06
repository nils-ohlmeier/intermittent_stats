#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import urllib2, json, re, argparse, datetime, urllib, gzip, os
from StringIO import StringIO
from collections import Counter

BUGZILLA_URL = "https://bugzilla.mozilla.org/rest.cgi/bug/"
BUGZILLA_COMMENTS = "/comment"
EMAIL_TBPL = "tbplbot@gmail.com"
MAX_SLAVES = 10

def printPrettyCounter(counter, name, maxval=None):
  total = sum(counter.values()) + 0.0
  print "%s:" % (name)
  for c in counter.most_common(maxval):
    percent = c[1] / total * 100
    print "  %d (%.1f%s):  %s" % (c[1], percent, '%', c[0])
  if maxval and len(counter.most_common()) > maxval:
    print "  + %d more" % (total - maxval)

parser = argparse.ArgumentParser(description="Collect TBPL build statistics from a Bugzilla ticket")
parser.add_argument('bznumber', type=int,
help='the bugzilla ticket number to pull from')
parser.add_argument('-v', '--verbose', action="count", default=0,
help="increase output verbosity")
parser.add_argument('-d', '--days', action='store', type=int, default=0,
help='how many days of history from today backwards are collected')
parser.add_argument('-s', '--slaves', action='store', type=int,
default=MAX_SLAVES, help="maximum number of slave entries to print")
parser.add_argument('-o' '--download', action='store_true',
help='download the still available build logs', dest='download')
args = parser.parse_args()

bugID = args.bznumber
datefrom = None
if (args.days > 0):
  datefrom = datetime.datetime.today() - datetime.timedelta(days=args.days)
verbose = args.verbose
download = args.download

osc = Counter()
branch = Counter()
btype = Counter()
testgrp = Counter()
date = time = []
slaves = Counter()
#                         OS   branch        btype         testgrp            date      time
re_build = re.compile(r'^(.*) ([a-z0-9-_]+) ([a-z]+) test ([A-Za-z0-9-]+) on ([0-9-]+) ([0-9:]+)$')
re_slave = re.compile(r'slave: (.*)')
re_log = re.compile(r'^(https://tbpl.mozilla.org/php/getParsedLog.php.*)')

def parseOldTbplMessage(lines):
  if download:
    logline = lines[1]
    match = re_log.match(logline)
    if match:
      log_url = match.group(1)
      if (verbose > 1):
        print "Found link to log: %s" % (log_url)
      log_resp = urllib2.urlopen(log_url)
      data = ""
      if log_resp.info().get('Content-Encoding') == 'gzip':
        buf = StringIO(log_resp.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
      else:
        data = log_resp.read()
      if data != "Unknown run ID.":
        re_full = re.compile(r'.*(http://ftp.mozilla.org[A-Za-z0-9/.\-_@]+).*')
        match = re_full.findall(data)
        if len(match) == 1:
          url = match[0]
          filename = str(bugID) + "-" + str(commentnum) + ".gz"
          print "Downloading full log (%s): %s" % (filename, url)
          (filename, headers) = urllib.urlretrieve(url, filename)
          if headers.get('Content-Encoding') != 'x-gzip':
            os.remove(filename)
  buildline = lines[2]
  match = re_build.match(buildline)
  if match:
    osc[match.group(1)] += 1
    branch[match.group(2)] += 1
    btype[match.group(3)] += 1
    testgrp[match.group(4)] += 1
    # collect them, but not agregated yet
    date.append(match.group(5))
    time.append(match.group(6))
  else:
    print "Failed to find/parse build line in here: %s" % (lines)
  slave_line = lines[4]
  match = re_slave.match(slave_line)
  if not match:
    slave_line = lines[3]
    match = re_slave.match(slave_line)
  if match:
    slaves[match.group(1)] += 1
  else:
    print "Failed to find/parse slave line in here: %s" % (lines)

def handleLogLine(value):
  print "Implement log handler"

def handleRepLine(value):
  branch[value] += 1

def handleStartTime(value):
  print "Implement start time handler"

def handleWho(value):
  print "Implement who handler"

def handleMachineLine(value):
  slaves[value] += 1

re_buildname = re.compile(r'^(.*) ([a-z0-9-_]+) ([a-z]+) test ([A-Za-z0-9-]+)$')
def handleBuildLine(value):
  match = re_buildname.match(value)
  if match:
    osc[match.group(1)] += 1
    branch[match.group(2)] += 1
    btype[match.group(3)] += 1
    testgrp[match.group(4)] += 1

def handleRevision(value):
  print "Implement revision handler"

TreeherderNames = {
  'log': handleLogLine,
  'repository': handleRepLine,
  'start_time': handleStartTime,
  'who': handleWho,
  'machine': handleMachineLine,
  'buildname': handleBuildLine,
  'revision': handleRevision
}

def parseNewTreeherderMessage(lines):
  print "Parser for Treeherder needs to be implemented"
  for line in lines:
    if len(line) == 0:
      break
    name_value = line.split(':')
    name = name_value[0]
    value = name_value[1]
    if name in TreeherderNames.keys():
      TreeherderNames[name](value.strip())

connection = urllib2.urlopen(BUGZILLA_URL + str(bugID) + BUGZILLA_COMMENTS)
jsonDict = json.loads(connection.read())

comments = jsonDict['bugs'][str(bugID)]['comments']
commentnum = 0
for c in comments:
  commentnum += 1
  if c['author'] == EMAIL_TBPL :
    creation = datetime.datetime.strptime(c['creation_time'], "%Y-%m-%dT%H:%M:%SZ")
    if datefrom and (creation < datefrom):
      if (verbose > 0):
        print "Ignoring entry from %s" % (creation)
      continue
    #cid = c['id']
    lines = re.split("\r?\n", c['text'])
    if (verbose > 2):
      print lines
    parseNewTreeherderMessage(lines)
    #parseOldTbplMessage(lines)


printPrettyCounter(osc, "OS's")
printPrettyCounter(branch, "Branches")
printPrettyCounter(btype, "Build-Type")
printPrettyCounter(testgrp, "Test Group")
printPrettyCounter(slaves, "Slaves", args.slaves)
