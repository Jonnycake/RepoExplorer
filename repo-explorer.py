#!/usr/bin/python3
import argparse
import pathlib
import time
import Analyzer

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
print("Creating the analyzer...")
analyzer = Analyzer.Analyzer(path=args.repo_path, enable_cache=args.enable_cache)

print("Loading configurations...")
analyzer.loadConfigs(args.ini_file)
if args.cache_file is not None:
    analyzer.cache_file = pathlib.Path(args.cache_file)

print("Collecting data...")
analyzer.collectData(args.load_cache)
print("\tData collection completed in %d seconds." % (time.time()-start_time))
print("Performing analysis...")
analyzer.doAnalysis()
print("Full process complete in %d seconds." % (time.time()-start_time))
analyzer.output(file=args.to_file, filename=args.output_file)

