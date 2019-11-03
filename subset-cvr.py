#!/usr/bin/python3

# sf-elections-rcv - software to display ranked choice voting results
#   for San Francisco elections

# subset-cvr.py - script to subset the cast vote record (CVR) files used
#   starting in 2019

# Copyright 2019 L. David Baron <dbaron@dbaron.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import zipfile
import tempfile
import shutil
import json
import struct

from optparse import OptionParser

op = OptionParser()
(options, args) = op.parse_args()

if len(args) != 2:
    op.error("expected two arguments but got {0}".format(len(args)))
cvrFilename = args[0]
outFilename = args[1]

zf = zipfile.ZipFile(cvrFilename, "r")

# Take the pieces of each component JSON file that we care about, and
# discard the rest.

contests = json.load(zf.open("ContestManifest.json"))
contests = {o["Id"]: { "name": o["Description"] } for o in contests["List"]}

ballot_types = json.load(zf.open("BallotTypeManifest.json"))
ballot_types = {o["Id"]: { "name": o["Description"] } for o in ballot_types["List"]}

candidates = json.load(zf.open("CandidateManifest.json"))
candidates = {o["Id"]: { "name": o["Description"],
                         "contest": o["ContestId"] } for o in candidates["List"]}

counting_groups = json.load(zf.open("CountingGroupManifest.json"))
counting_groups = {o["Id"]: { "name": o["Description"] } for o in counting_groups["List"]}

precincts = json.load(zf.open("PrecinctPortionManifest.json"))
precincts = {o["Id"]: { "name": o["Description"] } for o in precincts["List"]}

# It would probably be better to use a streaming JSON processor for this
# rather than loading the whole thing into memory.

# A few notes on the CVR format:
#  - "IsVote" seems to represent whether a rank is the top rank.  It can be ignored.
cvr = json.load(zf.open("CvrExport.json"))
ballots = []
for session in cvr["Sessions"]:
    # For each session, it looks like we could either use the
    # "Original"/"Modified" properties *or* the "IsCurrent" fields on
    # them to determine modifications.  I'll use "Modified" and ignore
    # "IsCurrent" since it seems like they're equivalent.
    entry = session["Modified"] if "Modified" in session else session["Original"]

    # Convert all the ID-like things to strings, for use as values,
    # because both JSON and JavaScript are bad at having integer-typed
    # keys (they tend to convert to strings), so make everything strings
    # so comparisons work well.
    #
    # (Leave only the rank as an integer.)
    counting_group = str(session["CountingGroupId"])
    ballot_type_id = str(entry["BallotTypeId"])
    precinct_id = str(entry["PrecinctPortionId"])
    if precinct_id == "0":
        print("WARNING: Changing precinct ID of 0 to 1.  (Hope this is a problem only in the test dataset.)")
        precinct_id = "1"
    for contest in entry["Contests"]:
        contest_id = str(contest["Id"])
        ranks = []
        for mark in contest["Marks"]:
            ranks += [{"candidate": str(mark["CandidateId"]), "rank": mark["Rank"]}]
        ballots += [ { "counting_group": counting_group,
                       "ballot_type": ballot_type_id,
                       "precinct": precinct_id,
                       "contest": contest_id,
                       "ranks": ranks } ]

zf.close()


json_data = {
              "contests": contests,
              "ballot_types": ballot_types,
              "candidates": candidates,
              "counting_groups": counting_groups,
              "precincts": precincts,
              "ballots": ballots,
            }

jsonIO = open(outFilename, "w")
# can add indent=True for testing
json.dump(json_data, jsonIO, sort_keys=True)
jsonIO.close()
jsonIO = None