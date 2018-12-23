#!/usr/bin/python3
import argparse
import configparser
import difflib
import pathlib
import json
import sys
import git

class Analyzer:
    repo_dir = "."
    config = None
    data = {}
    differ = None
    stats = {}
    def __init__(self, path="."):
        self.repo_dir = path
        self.differ = difflib.Differ()

    def loadConfigs(self, path):
        config = configparser.ConfigParser()
        config.read(path)
        self.config = config

    def collectData(self, from_cache=False):
        """
            Collect list of commits and list of files
            For each commit - identify "author", "files changed", "date", and
              "impact" (based on changeset)
            For each file - identify file type and the current content
        """
        data = {}
        cache_path = pathlib.Path("%s/%s" % (self.repo_dir, self.config.get('Caching', 'cache_file')))
        if from_cache and cache_path.is_file():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
            except:
                # @todo Do something with the error
                print(sys.exc_info()[0])
        else:
            data = self.loadLiveData()

        self.data = data

    def getDiffStats(self, commit, last_commit):
        files = {}
        commit_diff = last_commit.diff(commit) if last_commit != git.NULL_TREE else commit.diff(last_commit)
        for change in commit_diff:
            files[change.b_path] = {"add": 0, "del": 0, "type": "A"}
            files[change.b_path]['type'] = change.change_type
            try:
                orig = change.a_blob.data_stream.read().decode('utf-8').splitlines(1)
                new = change.b_blob.data_stream.read().decode('utf-8').splitlines(1)
                for diff in list(self.differ.compare(orig, new)):
                    if diff.startswith('+'):
                        files[change.b_path]['add'] += 1
                    elif diff.startswith('-'):
                        files[change.b_path]['del'] += 1
            except:
                # @todo Do something with the error
                pass
        return files

    def loadLiveData(self):
        repo = git.Repo(self.repo_dir)

        data = {"authors": {}, "commits": {}, "files": {}}
        commits = {}
        last_commit = git.NULL_TREE
        for commit in list(repo.iter_commits())[::-1]:
            tmp_commit_data = {
                "author": commit.author.name,
                "files": {},
                "date": "unknown"
            }
            tmp_commit_data['files'] = self.getDiffStats(commit, last_commit)
            commits[str(commit)] = tmp_commit_data
            last_commit = commit

        data['commits'] = commits
        with open("repo-explorer.cache", "w") as f:
            f.write(json.dumps(data))

        return data

    def doAnalysis(self):
        self.stats['basic'] = self.aggregateBasicInfo()

        if self.config.getboolean('General', 'dependency_analysis'):
            self.stats['dependencies'] = self.inferDependencies()

    def inferDependencies(self):
        threshold = int(self.config.get('Dependency Analysis', 'threshold'))

        commit_hashes = list(self.data['commits'].keys())
        if self.config.getboolean('Dependency Analysis', 'ignore_first_commit'):
                commit_hashes = commit_hashes[1:]
        commits = self.data['commits']

        file_relations = {}
        for commit in commit_hashes:
            for file in commits[commit]['files']:
                if file not in file_relations:
                    file_relations[file] = {}

                for related_file in commits[commit]['files']:
                    if related_file != file:
                        file_relations[file][related_file] = 1 if related_file not in file_relations[file] else file_relations[file][related_file] + 1
                        if related_file not in file_relations:
                            file_relations[related_file] = {file: 1}
                        elif file not in file_relations[related_file]:
                                file_relations[related_file][file] = 1
                        else:
                            file_relations[related_file][file] += 1

        print("Last commit: %s" % (commit))

    def output(self):
        pass

    def aggregateBasicInfo(self):
        """
            Total number of commits
            First commit date & Author
            Last commit date & Author
        """
        basic_stats = {"total": 0, "first":{}, "last": {}}
        basic_stats['total'] = len(self.data['commits'].keys())

        return basic_stats

analyzer = Analyzer("/Users/jonst/Desktop/projects/SimpleSite/")
print("Loading configurations...")
analyzer.loadConfigs("conf/repo-explorer.ini")
print("Collecting data...")
analyzer.collectData()
print("Performing analysis...")
analyzer.doAnalysis()
