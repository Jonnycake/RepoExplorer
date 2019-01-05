#!/usr/bin/python3
import argparse
import configparser
import difflib
import pathlib
import json
import sys
import os
import git
import pprint
import time

class Analyzer:
    # Can be customized via command line
    cache_file=None
    repo_dir = "."
    config = None
    data = {}
    differ = None
    stats = {}
    structure = {}
    cache_enabled = False

    def __init__(self, path=".", enable_cache=False):
        self.repo_dir = path
        self.differ = difflib.Differ()
        self.cache_enabled = enable_cache

    def loadConfigs(self, path):
        config = configparser.ConfigParser()
        config.read(path)
        self.config = config
        self.cache_file = pathlib.Path("%s/%s" % (self.repo_dir, self.config.get('Caching', 'cache_file')))

    def collectData(self, from_cache=False):
        """
            Collect list of commits and list of files
            For each commit - identify "author", "files changed", "date", and
              "impact" (based on changeset)
            For each file - identify file type and the current content
        """
        data = {}
        cache_path = self.cache_file
        if from_cache and cache_path.is_file():
            print("\tLoading from cache (%s)..." % (cache_path))
            try:
                with open(cache_path, "r") as f:
                    data = json.load(f)
            except:
                # @todo Do something with the error
                print(sys.exc_info()[0])
        else:
            print("\tLoading live data...")
            data = self.loadLiveData()

        self.data = data

        if self.cache_enabled:
            print("\tWriting cache file '%s'..." % (cache_path))
            with open(cache_path, "w") as f:
                f.write(json.dumps(self.data))

    def getDiffStats(self, commit, last_commit):
        files = {}
        commit_file_limit = int(self.config.get('Data Collection', 'commit_file_limit'))
        commit_diff = last_commit.diff(commit) if last_commit != git.NULL_TREE else commit.diff(last_commit)

        if commit_file_limit != -1 and len(commit_diff) > commit_file_limit:
            return None

        for change in commit_diff:
            #if change.b_path in self.data['files']:
            #    self.data['files'][change.b_path] += 1

            files[change.b_path] = {"add": None, "del": None, "type": "A", "diff": None}
            files[change.b_path]['type'] = change.change_type
            if self.config.getboolean('Data Collection', 'impact_stats'):
                try:
                    # Probably want to maintain previous path info too...
                    files[change.b_path]['add'] = 0
                    files[change.b_path]['del'] = 0

                    orig = change.a_blob.data_stream.read().decode('utf-8').splitlines(1)
                    new = change.b_blob.data_stream.read().decode('utf-8').splitlines(1)
                    diffed = list(self.differ.compare(orig, new))

                    for diff in diffed:
                        if diff.startswith('+'):
                            files[change.b_path]['add'] += 1
                        elif diff.startswith('-'):
                            files[change.b_path]['del'] += 1

                    if self.config.getboolean('Data Collection', 'full_diff'):
                        files[change.b_path]['diff'] = "\n".join(diffed)

                except:
                    # @todo Do something with the error
                    pass

        return files

    def loadLiveData(self):
        repo = git.Repo(self.repo_dir)

        data = {"authors": {}, "commits": {}, "files": {}}
        commits = {}
        last_commit = git.NULL_TREE
        total_commits = len(list(repo.iter_commits()))
        complete_update = int(total_commits / 10)
        commits_completed = 0
        a_time = time.time()
        for commit in list(repo.iter_commits())[::-1]:
            # @todo Why is this not working? o.O I double checked and this definitely should get 0...
            #         In fact....it says the 0/X message....
            if not commits_completed % complete_update:
                print("\t\tCommits Complete: %d / %d (~%d%%)" % (commits_completed, total_commits, (commits_completed/total_commits*100)))

            commits_completed += 1
            # Ignore merge commits (commits with > 1 parent)
            if len(commit.parents) > 1:
                continue

            tmp_commit_data = {
                "author": commit.author.name,
                "files": {},
                "date": "unknown"
            }
            tmp_commit_data['files'] = self.getDiffStats(commit, last_commit)
            commits[str(commit)] = tmp_commit_data
            last_commit = commit
            if time.time() - a_time > 60:
                print("\t\tMinutely Update: Commits Complete: %d / %d (~%d%%)" % (commits_completed, total_commits, (commits_completed/total_commits*100)))
                a_time = time.time()

        data['commits'] = commits

        return data

    def doAnalysis(self):
        self.stats['basic'] = self.aggregateBasicInfo()

        if self.config.getboolean('General', 'structure_location'):
            print("\tFinding structures...")
            self.stats['structures'] = self.findStructures()

        if self.config.getboolean('General', 'dependency_analysis'):
            print("\tInferring dependencies...")
            self.stats['dependencies'] = self.inferDependencies()

        if self.config.getboolean('General', 'most_changed'):
            print("\tFinding most changed file(s)...")
            self.stats['most_changed'] = self.findMostChanged()

        if self.config.getboolean('General', 'top_contributor'):
            print("\tFinding top contributor(s)...")
            self.stats['top_contributor'] = self.findTopContributor()

    def findMostChanged(self):
        pass

    def findTopContributor(self):
        pass

    def findStructures(self):
        # Load the structure location configs
        doc_dirs = self.config.get('Structure Location', 'doc_dirs').split(',')
        include_dirs = self.config.get('Structure Location', 'include_dirs').split(',')
        src_dirs = self.config.get('Structure Location', 'src_dirs').split(',')
        test_dirs = self.config.get('Structure Location', 'test_dirs').split(',')
        vendor_dirs = self.config.get('Structure Location', 'vendor_dirs').split(',')
        useful_files = self.config.get('Structure Location', 'useful_files').split(',')

        structures = {'docs': [], 'includes': [], 'sources': [], 'tests': [], 'vendor code': [], 'references': []}
        walked = []

        # We can probably find structures as we walk....
        for root, dirs, files in os.walk(self.repo_dir):
            dirs[:] = [d for d in dirs if d != '.git']
            walked.append((root, dirs, files))

        # First we must find and exclude vendor code (which may have it's own structures)
        for root, dirs, files in walked:
            vendor_code = list(set(vendor_dirs) & set(dirs))
            structures['vendor code'] += [os.path.join(root, dir) for dir in vendor_code]

        non_vendor_paths = []
        for root, dirs, files in walked:
            is_vendor = False

            for vendor_dir in structures['vendor code']:
                if not os.path.relpath(root, vendor_dir).startswith('..'):
                    is_vendor = True
                    break

            if not is_vendor:
                non_vendor_paths.append((root, dirs, files))

        # Then we can continue locating the relevant structures
        for root, dirs, files in non_vendor_paths:
            # doc, include, src, test & useful_files
            docs = list(set(doc_dirs) & set(dirs))
            structures['docs'] += [os.path.relpath(os.path.join(root, d), self.repo_dir) for d in docs]

            includes = list(set(include_dirs) & set(dirs))
            structures['includes'] += [os.path.relpath(os.path.join(root, d), self.repo_dir) for d in includes]

            sources = list(set(src_dirs) & set(dirs))
            structures['sources'] += [os.path.relpath(os.path.join(root, d), self.repo_dir) for d in sources]

            tests = list(set(test_dirs) & set(dirs))
            structures['tests'] += [os.path.relpath(os.path.join(root, d), self.repo_dir) for d in tests]

            references = list(set(useful_files) & set(files))
            structures['references'] += [os.path.relpath(os.path.join(root, d), self.repo_dir) for d in references]

        return structures

    def inferDependencies(self):
        # Get the threshold config value
        threshold = int(self.config.get('Dependency Analysis', 'threshold'))

        # Ignore the first commit
        commit_hashes = list(self.data['commits'].keys())
        if self.config.getboolean('Dependency Analysis', 'ignore_first_commit'):
            commit_hashes = commit_hashes[1:]

        # Ignore particular extensions
        ignored_extensions = self.config.get('Dependency Analysis', 'ignore_extensions').split(",")

        commits = self.data['commits']

        ignored_dirs = []
        ignored_files = []
        if 'structures' in self.stats:
            ignored_dirs = self.stats['structures']['docs'] \
                + self.stats['structures']['tests'] \
                + self.stats['structures']['references']
            ignored_files = self.stats['structures']['references']

        print("\t\t...maybe ignoring directories: %s" % (", ".join(ignored_dirs)))

        # Look at each commit one by one and record what files are together
        file_relations = {}
        for commit in commit_hashes:
            # Commit had too many files, not usable for dependency analysis
            if commits[commit]['files'] is None:
                continue

            # This looks ugly...we can probably simplify it
            for file in commits[commit]['files']:
                if file.endswith(tuple(ignored_extensions)):
                    continue

                if file.startswith(tuple(ignored_dirs)):
                    continue

                if file in ignored_files:
                    continue

                if not pathlib.Path(os.path.join(self.repo_dir, file)).exists():
                    continue

                if file not in file_relations:
                    file_relations[file] = {}

                for related_file in commits[commit]['files']:
                    if related_file.endswith(tuple(ignored_extensions)):
                        continue

                    if related_file.startswith(tuple(ignored_dirs)):
                        continue

                    if related_file in ignored_files:
                        continue

                    if not pathlib.Path(os.path.join(self.repo_dir, related_file)).exists():
                        continue

                    if related_file == file:
                        continue

                    file_relations[file][related_file] = 1 if related_file not in file_relations[file] else file_relations[file][related_file] + 1

                    if related_file not in file_relations:
                        file_relations[related_file] = {file: 1}
                    elif file not in file_relations[related_file]:
                        file_relations[related_file][file] = 1
                    else:
                        file_relations[related_file][file] += 1

        # Limit it to only files with relationships above the threshold
        for file in file_relations:
            file_relations[file] = {k:v for (k, v) in file_relations[file].items() if v > threshold}

        return file_relations

    def output(self, file=False, filename=""):
        if file and len(filename):
            with open(filename, "w") as f:
                f.write(json.dumps(self.stats))
        else:
            pp = pprint.PrettyPrinter(indent=4)
            pp.pprint(self.stats)

    def aggregateBasicInfo(self):
        """
            Total number of commits
            First commit date & Author
            Last commit date & Author
        """
        basic_stats = {"total": 0, "first":{}, "last": {}}
        commit_hashes = list(self.data['commits'].keys())
        basic_stats['total'] = len(commit_hashes)
        basic_stats['first'] = {commit_hashes[0]: self.data['commits'][commit_hashes[0]]}
        basic_stats['last'] = {commit_hashes[-1]: self.data['commits'][commit_hashes[-1]]}
        return basic_stats

argparser = argparse.ArgumentParser(description="Analyze a git repo for useful information.")
argparser.add_argument("repo_path", help="Repo location", type=str)
argparser.add_argument("-i", "--ini_file", help="Config file location.", type=str, required=True)
argparser.add_argument("-o", "--output_file", help="Output file location.", type=str, default="repo-explorer.out")
argparser.add_argument("-c", "--cache_file", help="Cache file location.", type=str, default=None)
argparser.add_argument("-C", "--enable_cache", help="Enable caching.", action="store_true")
argparser.add_argument("-L", "--load_cache", help="Load from cache.", action="store_true")
argparser.add_argument("-e", "--ignore_extensions", help="Add ignored file extensions.", type=str)
argparser.add_argument("-F", "--to_file", help="Write output to file.", action="store_true")
args = argparser.parse_args()

print("Creating the analyzer...")
analyzer = Analyzer(path=args.repo_path, enable_cache=args.enable_cache)

print("Loading configurations...")
analyzer.loadConfigs(args.ini_file)
if args.cache_file is not None:
    analyzer.cache_file = pathlib.Path(args.cache_file)

print("Collecting data...")
analyzer.collectData(args.load_cache)

print("Performing analysis...")
analyzer.doAnalysis()

analyzer.output(file=args.to_file, filename=args.output_file)

