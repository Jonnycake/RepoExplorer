#!/usr/bin/python3
import argparse
import configparser
import pathlib
import json
import sys
import git

class Analyzer:
    repo_dir = "."
    config = None
    data = {}
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
                print(sys.exc_info()[0])
        else:
            data = self.loadLiveData()

        self.data = data

    def loadLiveData(self):
        pass

    def doAnalysis(self):
        pass

    def output(self):
        pass

    def aggregateBasicInfo(self):
        """
            Total number of commits
            First commit date & Author
            Last commit date & Author
        """
        pass

analyzer = Analyzer()
analyzer.loadConfigs("conf/repo-explorer.ini")
analyzer.collectData(from_cache=True)
analyzer.doAnalysis()
