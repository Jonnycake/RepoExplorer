# Basic Description

This is a python script to automate getting familiar with a git repo.  It works
under the presumption that VCS best practices are followed (commit early,
commit often) and, for dependency evaluation, that related files are modified
in the same commits.

# Features
## Statistics
### Basic Statistics

Simple Commit Statistics:

* Total Commits
* First Commit
* Last Commit

### Most Changed Files

Impact vs Commit Based

* Impact based - Net amount of changed lines
* Commit based - Total number of commits affecting the file

### Top Contributors

Impact vs Commit Based

* Impact based - Net amount of changed lines
* Commit based- Total number of commits by each contributor

## Structure Identification

Identifies common, useful structures such as:

* Documentation directories
* Source/include directories
* Test directories
* Vendor directories
* Reference files (READMEs, install/upgrade instructions, copyright info)

## Dependency Inference

Based on the presumption that related files are likely to be modified in the
same commits due to the fact that a change in one may prompt a change to the
other.  While useful for a new developer to get a heads up on what may need
to be double checked after making a change, it is also useful from a design
perspective as files with a large number of dependencies can indicate poor
encapsulation.

# Future Goals
## Static Code Analysis
### Break Checks

We can check if a change breaks the public interface of classes/functions,
thereby reducing the chance that any change will unwittingly break the system.

### Enhanced Dependency Analysis

We can use static code analysis to identify dependencies that weren't commited
at the same time, but were used by a changeset.  We may also be able to reduce
false-positives in a similar fashion.

## Statistics
### Intelligent Fragility Rating

We may be able to infer the fragility of a piece of code by seeing how often
it is changed and in response to what.

### Intelligent Impact Assessments

We may be able to weigh the impact based on, not only, number of lines changed,
but also how many downstream dependents that piece of code has.  With static
code analysis that may be able to be fine tuned all the way down to a line-by-
line level.

### Language Listing

Just a simple list of what programming languages were used in the project.

## Misc
### Commit Message Analysis

Commit messages may help give some context into what the change was in response
to - was it a bugfix, enhancement, or a brand new feature?
