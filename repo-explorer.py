#!/usr/bin/python3
# RepoExplorer: A utility to quickly familiarize oneself with a code repo.
# Copyright (C) 2019  Jon Stockton <jonstockton1416@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import argparse
import pathlib
import time
import Explorer

# @todo Make argument groups...
argparser = argparse.ArgumentParser(description="Analyze a git repo for useful information.")
argparser.add_argument("repo_path", help="Repo location", type=str)
argparser.add_argument("-i", "--ini_file", help="Config file location.", type=str, required=True)
argparser.add_argument("-o", "--output_file", help="Output file location.", type=str, default="repo-explorer.out")
argparser.add_argument("-c", "--cache_file", help="Cache file location.", type=str, default=None)
argparser.add_argument("-C", "--enable_cache", help="Enable caching.", action="store_true")
argparser.add_argument("-L", "--load_cache", help="Load from cache.", action="store_true")
argparser.add_argument("-F", "--to_file", help="Write output to file.", action="store_true")
argparser.add_argument("-T", "--tops", help="Enable top contributor and most changed file.", action="store_true")
argparser.add_argument("-D", "--dependency_inference", help="Enable dependency inference.", action="store_true")
argparser.add_argument("-S", "--structure_id", help="Enable structure identification.", action="store_true")
argparser.add_argument("-dt", "--dependency_threshold", help="Set dependency threshold.", type=int)
argparser.add_argument("-e", "--ignore_extensions", help="Add ignored file extensions.", type=str)
argparser.add_argument("--full_diff", help="Enable full diff storage.", action="store_true")
argparser.add_argument("-l", "--commit_limit", help="Commit file limmit.", type=int)
argparser.add_argument("-s", "--structures", help="Structure additions.", type=str)

# @todo More config overrides...

args = argparser.parse_args()

start_time = time.time()
print("Creating the explorer...")
explorer = Explorer.Explorer(path=args.repo_path)

print("Loading configurations...")
explorer.loadConfigs(args.ini_file)

# Override configs
print("Performing command line overrides...")
if args.enable_cache:
    print("\tEnabling cache...")
    explorer.setConfig('General', 'enable_cache', 'true')

if args.cache_file is not None:
    print("\tSetting Caching.cache_file to: %s..." % (args.cache_file))
    explorer.setConfig('Caching', 'cache_file', args.cache_file)

if args.tops:
    print("\tEnabling top contributor and most changed file stats...")
    explorer.setConfig('General', 'top_contributor', 'true')
    explorer.setConfig('General', 'most_changed', 'true')

if args.dependency_inference:
    print("\tEnabling dependency inference...")
    explorer.setConfig('General', 'dependency_inference', 'true')

if args.structure_id:
    print("\tEnabling structure identifiction...")
    explorer.setConfig('General', 'structure_location', 'true')

if args.structures:
    print("\tAdding a list to structures...")
    structures = args.structures.split(";")
    for structure in structures:
        structure_type, value = structure.split(":")
        orig_value = explorer.getConfig('Structure Location', structure_type)
        if orig_value is not False:
            explorer.setConfig('Structure Location', structure_type, "%s,%s" % (orig_value, value))
        else:
            print("\t\tWarning: Unknown structure type: %s" % (structure_type))

if args.dependency_threshold is not None:
    print("\tSetting dependency threshold to: %d..." % (args.dependency_threshold))
    explorer.setConfig('Dependency Inference', 'threshold', str(args.dependency_threshold))

if args.ignore_extensions is not None:
    print("\tAdding '%s' to the ignored extensions list..." % (args.ignore_extensions))
    ignored_extensions = explorer.getConfig('Dependency Inference', 'ignore_extensions')
    ignored_extensions += ",%s" % (args.ignore_extensions)
    print("\t\tThe final list is as follows:")
    for extension in ignored_extensions.split(","):
        print("\t\t * %s" % (extension))

if args.full_diff:
    print("\tEnabling full diff storage...")
    explorer.setConfig('Data Collection', 'full_diff', 'true')

if args.commit_limit is not None:
    print("\tSetting the commit file limit...")
    explorer.setConfig('Data Collection', 'commit_file_limit', str(args.commit_limit))

print("Collecting data...")
explorer.collectData(args.load_cache)
print("\tData collection completed in %d seconds." % (time.time()-start_time))
print("Exploring...")
explorer.explore()
print("Full process complete in %d seconds." % (time.time()-start_time))
explorer.output(file=args.to_file, filename=args.output_file)

