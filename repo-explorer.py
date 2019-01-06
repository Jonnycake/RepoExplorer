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

# @todo Use these arguments
argparser.add_argument("-e", "--ignore_extensions", help="Add ignored file extensions.", type=str)
argparser.add_argument("-D", "--dependency_analysis", help="Enable dependency analysis.", action="store_true")
argparser.add_argument("-dt", "--dependency_threshold", help="Set dependency threshold.", type=int)
argparser.add_argument("-I", "--structure_id", help="Enable structure identification.", action="store_true")
argparser.add_argument("-T", "--tops", help="Enable top contributor and most changed file.", action="store_true")

args = argparser.parse_args()

start_time = time.time()
print("Creating the explorer...")
explorer = Explorer.Explorer(path=args.repo_path, enable_cache=args.enable_cache)

print("Loading configurations...")
explorer.loadConfigs(args.ini_file)
if args.cache_file is not None:
    explorer.cache_file = pathlib.Path(args.cache_file)

print("Collecting data...")
explorer.collectData(args.load_cache)
print("\tData collection completed in %d seconds." % (time.time()-start_time))
print("Exploring...")
explorer.explore()
print("Full process complete in %d seconds." % (time.time()-start_time))
explorer.output(file=args.to_file, filename=args.output_file)

