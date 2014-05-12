#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import urllib2, json, re, sys
from collections import Counter

BUGZILLA_URL = "https://bugzilla.mozilla.org/rest.cgi/bug/"
BUGZILLA_COMMENTS = "/comment"
EMAIL_TBPL = "tbplbot@gmail.com"

def printPrettyCounter(counter, name):
  total = sum(counter.values()) + 0.0
  print "%s:" % (name)
  for c in counter.most_common():
    percent = c[1] / total * 100
    print "  %d (%.1f%s):  %s" % (c[1], percent, '%', c[0])

if len(sys.argv) < 2:
  sys.exit('Usage: %s bugzilla-number' % sys.argv[0])

bugID = None
try:
  bugID = int(sys.argv[1])
except ValueError:
  sys.exit('Usage: %s bugzilla-number' % sys.argv[0]);

os = Counter()
branch = Counter()
build = Counter()
testgrp = Counter()
date = time = []
reobj = re.compile(r'^(.*) ([a-z0-9-_]+) ([a-z]+) test ([A-Za-z0-9-]+) on ([0-9-]+) ([0-9:]+)$')

connection = urllib2.urlopen(BUGZILLA_URL + str(bugID) + BUGZILLA_COMMENTS)
jsonDict = json.loads(connection.read())

comments = jsonDict['bugs'][str(bugID)]['comments']
for c in comments:
  if c['author'] == EMAIL_TBPL :
    # TODO: read the line with the machine name as well?!
    line = re.split("\r?\n", c['text'])[2]
    match = reobj.match(line)
    if match:
      os[match.group(1)] += 1
      branch[match.group(2)] += 1
      build[match.group(3)] += 1
      testgrp[match.group(4)] += 1
      # collect them, but not agregated yet
      date.append(match.group(5))
      time.append(match.group(6))
    else:
      print "NO MATCH: " + line

printPrettyCounter(os, "OS's")
printPrettyCounter(branch, "Branches")
printPrettyCounter(build, "Build")
printPrettyCounter(testgrp, "Test Group")
