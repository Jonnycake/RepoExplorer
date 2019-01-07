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
import configparser
import difflib
import pathlib
import json
import sys
import os
import git
import pprint
import time

class Explorer:
    repo_dir = "."
    config = None
    data = {}
    differ = None
    stats = {}
    structure = {}

    def __init__(self, path="."):
        self.repo_dir = path
        self.differ = difflib.Differ()

    def setConfig(self, config_group, config, value):
        self.config.set(config_group, config, value)

    def getConfig(self, config_group, config):
        if self.config.has_option(config_group, config):
            return self.config.get(config_group, config)
        else:
            return False

    def loadConfigs(self, path):
        config = configparser.ConfigParser()
        config.read(path)
        self.config = config

        # We want to store the cache file in the relevant repo unless directed otherwise
        self.config.set('Caching', 'cache_file', ("%s/%s" % (self.repo_dir, self.config.get('Caching', 'cache_file'))))

    def keepFileStats(self, change, change_info):
        if "files" not in self.data:
            self.data['files'] = {}

        if change.change_type == "A" \
          or (change.b_path not in self.data['files'] \
          and change.a_path not in self.data['files']):
            self.data['files'][change.b_path] = {}
            self.data['files'][change.b_path]['commits'] = 1
        elif change.change_type == "M":
            self.data['files'][change.b_path]['commits'] += 1
        elif change.change_type == "R":
            # There's a chance that a_path doesn't exist in our data yet....
            # @todo Figure out how/why that happens...
            """
                yii ....
                Commits Complete: 5264 / 6581 (~79%)
                KeyError: 'framework/vendors/markdown/License.md' """

            if change.a_path in self.data['files']:
                self.data['files'][change.b_path] = {}
                self.data['files'][change.b_path]['commits'] = self.data['files'][change.a_path]['commits'] + 1
                if "impact" in self.data['files'][change.a_path]:
                    self.data['files'][change.b_path]['impact'] = self.data['files'][change.a_path]['impact']
                del self.data['files'][change.a_path]
            elif change.b_path in self.data['files']:
                self.data['files'][change.b_path]['commits'] += 1
            else:
                self.data['files'][change.b_path]['commits'] = 1

        # Delete should be separate...in case it's a delete and it got set anyways
        if change.change_type == "D":
            del self.data['files'][change.b_path]
        elif change_info['del'] is not None and change_info['add'] is not None:
            if "impact" not in self.data['files'][change.b_path]:
                self.data['files'][change.b_path]['impact'] = 0
            self.data['files'][change.b_path]['impact'] += change_info['add'] + change_info['del']

    def collectData(self, from_cache=False):
        """
            Collect list of commits and list of files
            For each commit - identify "author", "files changed", "date", and
              "impact" (based on changeset)
            For each file - identify file type and the current content
        """
        data = {}
        cache_path = pathlib.Path(self.config.get('Caching', 'cache_file'))
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

        # @todo Make this not needed....
        data['files'] = self.data['files']
        self.data = data

        if self.config.getboolean('General', 'enable_cache'):
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
            files[change.b_path] = {"add": None, "del": None, "type": "A", "diff": None}
            files[change.b_path]['type'] = change.change_type

            if self.config.getboolean('Data Collection', 'impact_stats'):
                try:
                    # Probably want to maintain previous path info too...
                    files[change.b_path]['add'] = 0
                    files[change.b_path]['del'] = 0
                    files[change.b_path]['a_path'] = change.a_path

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

            self.keepFileStats(change, files[change.b_path])

        return files

    def loadLiveData(self):
        repo = git.Repo(self.repo_dir)

        data = {"authors": {}, "commits": {}, "files": {}}
        commits = {}
        last_commit = git.NULL_TREE
        total_commits = len(list(repo.iter_commits()))
        complete_update = int(total_commits / 10) or 1
        commits_completed = 0
        a_time = time.time()

        for commit in list(repo.iter_commits())[::-1]:
            # Progress updates every ~10%
            if not commits_completed % complete_update:
                print("\t\tCommits Complete: %d / %d (~%d%%)" % (commits_completed, total_commits, (commits_completed/total_commits*100)))
            commits_completed += 1

            # Ignore merge commits (commits with > 1 parent)
            if len(commit.parents) > 1:
                continue

            # Basic information
            tmp_commit_data = {
                "author": commit.author.name,
                "files": {},
                "date": "unknown"
            }
            tmp_commit_data['files'] = self.getDiffStats(commit, last_commit)
            commits[str(commit)] = tmp_commit_data
            last_commit = commit
            if commit.author.name not in data['authors']:
                data['authors'][commit.author.name] = {"commits": 0}
            data['authors'][commit.author.name]['commits'] += 1
            if self.config.getboolean('Data Collection', 'impact_stats'):
                if "impact" not in data['authors'][commit.author.name]:
                    data['authors'][commit.author.name]['impact'] = 0

                if tmp_commit_data['files'] is not None:
                    for file in tmp_commit_data['files']:
                        data['authors'][commit.author.name]['impact'] += tmp_commit_data['files'][file]['add'] + tmp_commit_data['files'][file]['del']


            if time.time() - a_time > 60:
                print("\t\tMinutely Update: Commits Complete: %d / %d (~%d%%)" % (commits_completed, total_commits, (commits_completed/total_commits*100)))
                a_time = time.time()

        data['commits'] = commits

        return data

    def explore(self):
        self.stats['basic'] = self.aggregateBasicInfo()

        if self.config.getboolean('General', 'structure_location'):
            print("\tFinding structures...")
            self.stats['structures'] = self.findStructures()

        if self.config.getboolean('General', 'most_changed'):
            print("\tFinding most changed file(s)...")
            self.stats['most_changed'] = self.findMostChanged()

        if self.config.getboolean('General', 'top_contributor'):
            print("\tFinding top contributor(s)...")
            self.stats['top_contributor'] = self.findTopContributor()

        if self.config.getboolean('General', 'dependency_inference'):
            print("\tInferring dependencies...")
            self.stats['dependencies'] = self.inferDependencies()

    def findMostChanged(self):
        key = "impact" if self.config.get('Most Changed', 'type') == "impact" and self.config.getboolean('Data Collection', 'impact_stats') else "commits"
        sorted_files = sorted(self.data['files'].keys(), key=lambda k: self.data['files'][k][key], reverse=True)
        most_changed = []

        for file in sorted_files:
            most_changed.append((file, self.data['files'][file]))

        return most_changed[:int(self.config.get('Most Changed', 'limit'))]

    def findTopContributor(self):
        key = "impact" if self.config.get('Top Contributor', 'type') == "impact" and self.config.getboolean('Data Collection', 'impact_stats') else "commits"
        sorted_authors = sorted(self.data['authors'].keys(), key=lambda k: self.data['authors'][k][key], reverse=True)
        top_contributors = []

        for author in sorted_authors:
            top_contributors.append((author, self.data['authors'][author]))

        return top_contributors[:int(self.config.get('Top Contributor', 'limit'))]

    def findStructures(self):
        # Load the structure location configs
        config_paths = self.config.get('Structure Location', 'configs').split(',')
        doc_dirs = self.config.get('Structure Location', 'doc_dirs').split(',')
        include_dirs = self.config.get('Structure Location', 'include_dirs').split(',')
        src_dirs = self.config.get('Structure Location', 'src_dirs').split(',')
        test_dirs = self.config.get('Structure Location', 'test_dirs').split(',')
        vendor_dirs = self.config.get('Structure Location', 'vendor_dirs').split(',')
        useful_files = self.config.get('Structure Location', 'useful_files').split(',')

        structures = {'configs': [], 'docs': [], 'includes': [], 'sources': [], 'tests': [], 'vendor code': [], 'references': []}
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
            # configs, doc, include, src, test & useful_files
            configs = list((set(config_paths) & set(dirs)) | (set(config_paths) & set(files)))
            structures['configs'] += [os.path.relpath(os.path.join(root, d), self.repo_dir) for d in configs]

            docs = list(set(doc_dirs) & set(dirs))
            structures['docs'] += [os.path.relpath(os.path.join(root, d), self.repo_dir) for d in docs]

            includes = list(set(include_dirs) & set(dirs))
            structures['includes'] += [os.path.relpath(os.path.join(root, d), self.repo_dir) for d in includes]

            sources = list(set(src_dirs) & set(dirs))
            structures['sources'] += [os.path.relpath(os.path.join(root, d), self.repo_dir) for d in sources]

            tests = list(set(test_dirs) & set(dirs))
            structures['tests'] += [os.path.relpath(os.path.join(root, d), self.repo_dir) for d in tests]

            references = list((set(useful_files) & set(files)) | (set(useful_files) & set(dirs)))
            structures['references'] += [os.path.relpath(os.path.join(root, d), self.repo_dir) for d in references]

        return structures

    def inferDependencies(self):
        # Get the threshold config value
        threshold = int(self.config.get('Dependency Inference', 'threshold'))

        # Ignore the first commit
        commit_hashes = list(self.data['commits'].keys())
        if self.config.getboolean('Dependency Inference', 'ignore_first_commit'):
            commit_hashes = commit_hashes[1:]

        # Ignore particular extensions
        ignored_extensions = self.config.get('Dependency Inference', 'ignore_extensions').split(",")

        commits = self.data['commits']
        top_only = False
        tops = []

        if self.config.get('Dependency Inference', 'analysis_breadth') == "top"\
          and "most_changed" in self.stats:
            top_only = True
            tops = [file_stat[0] for file_stat in self.stats['most_changed']]

        ignored_dirs = []
        ignored_files = []
        if 'structures' in self.stats:
            ignored_dirs = self.stats['structures']['docs'] \
                + self.stats['structures']['tests'] \
                + self.stats['structures']['references'] \
                + self.stats['structures']['configs']

        print("\t\t...ignoring directories/files: %s" % (", ".join(ignored_dirs)))

        # Look at each commit one by one and record what files are together
        file_relations = {}
        for commit in commit_hashes:
            # Commit had too many files, not usable for dependency inference
            if commits[commit]['files'] is None:
                continue

            # This looks ugly...we can probably simplify it
            for file in commits[commit]['files']:
                if top_only and file not in tops:
                    continue

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

