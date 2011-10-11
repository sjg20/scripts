#!/usr/bin/python

# Patch creatiion and submission script
# Clean up patches ready for upstream by removing Chrome OS-specific things,
# running through checkpatch.pl and git-am.

'''
Removes code review lines from patches:
    BUG=, TEST=, Change-Id:, Review URL:
    Reviewed-on:, Reviewed-by:, Tested-by

Creates a cover letter from text found in the patches:

Cover-letter:
Subject of cover letter email
text line 1
text line 2
...
END

Subject is [<prefix> PATCH v<version>]

which is set by tag lines:
Series-prefix: RFC
Series-version: 3

Patch can be sent to people mentioned in the commits:

Series-to: u-boot
Series-cc: Simon Schwarz <simonschwarzcor@googlemail.com>
Series-cc: Detlev Zundel <dzu@denx.de>
Series-changes: 2
- Changed macros so that all code is compiled even if DEBUG is disabled
      (blank line)

(for u-boot it looks up ~/.config/clean-patch for lines like:
u-boot: "U-Boot Mailing List" <u-boot@lists.denx.de>
)

You can also create notes in each commit which appear after the cover letter

Series-notes:
Here are some notes
...
END

'''

from optparse import OptionParser
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


re_prog = re.compile('^BUG=|^TEST=|^Change-Id:|^Review URL:'
    '|Reviewed-on:|Reviewed-by:')
#|Tested-by:

# Lines which are allowed after a TEST= line
re_allowed_after_test = re.compile('^Signed-off-by:')

# The start of the cover letter
re_cover = re.compile('^Cover-letter:')

# Patch series
re_series = re.compile('^Series-(\w*): *(.*)')

# Tag that we want to collect and keep
re_tag = re.compile('^(Tested-by|Acked-by|Signed-off-by): (.*)')

# Copyright
re_copyright = re.compile('\+ \* Copyright \(c\) 2011, Google Inc. '
    'All rights reserved.')

re_commit = re.compile('commit (.*)')

re_space_before_tab = re.compile('^[+].* \t')

valid_series = ['to', 'cc', 'version', 'changes', 'prefix', 'notes'];


class Color(object):
  """Conditionally wraps text in ANSI color escape sequences."""
  BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
  BOLD = -1
  COLOR_START = '\033[1;%dm'
  BOLD_START = '\033[1m'
  RESET = '\033[0m'

  def __init__(self, enabled=True):
    """Create a new Color object, optionally disabling color output.

    Args:
      enabled: True if color output should be enabled. If False then this
        class will not add color codes at all.
    """
    self._enabled = enabled

  def Start(self, color):
    """Returns a start color code.

    Args:
      color: Color to use, .e.g BLACK, RED, etc.

    Returns:
      If color is enabled, returns an ANSI sequence to start the given color,
      otherwise returns empty string
    """
    if self._enabled:
      return self.COLOR_START % (color + 30)
    return ''

  def Stop(self):
    """Retruns a stop color code.

    Returns:
      If color is enabled, returns an ANSI color reset sequence, otherwise
      returns empty string
    """
    if self._enabled:
      return self.RESET
    return ''

  def Color(self, color, text):
    """Returns text with conditionally added color escape sequences.

    Keyword arguments:
      color: Text color -- one of the color constants defined in this class.
      text: The text to color.

    Returns:
      If self._enabled is False, returns the original text. If it's True,
      returns text with color escape sequences based on the value of color.
    """
    if not self._enabled:
      return text
    if color == self.BOLD:
      start = self.BOLD_START
    else:
      start = self.COLOR_START % (color + 30)
    return start + text + self.RESET


class Command(object):
  """Shell command ease-ups for Python."""

  def RunPipe(self, pipeline, infile=None, outfile=None,
              capture=False, oneline=False, hide_stderr=False):
    """
    Perform a command pipeline, with optional input/output filenames.

    hide_stderr     Don't allow output of stderr (default False)
    """

    last_pipe = None
    while pipeline:
      cmd = pipeline.pop(0)
      kwargs = {}
      if last_pipe is not None:
        kwargs['stdin'] = last_pipe.stdout
      elif infile:
        kwargs['stdin'] = open(infile, 'rb')
      if pipeline or capture:
        kwargs['stdout'] = subprocess.PIPE
      elif outfile:
        kwargs['stdout'] = open(outfile, 'wb')
      if hide_stderr:
        kwargs['stderr'] = open('/dev/null', 'wb')

      last_pipe = subprocess.Popen(cmd, **kwargs)

    if capture:
      ret = last_pipe.communicate()[0]
      if not ret:
        return None
      elif oneline:
        return ret.rstrip('\r\n')
      else:
        return ret
    else:
      return os.waitpid(last_pipe.pid, 0)[1] == 0

  def Output(self, *cmd):
    return self.RunPipe([cmd], capture=True)

  def OutputOneLine(self, *cmd):
    return self.RunPipe([cmd], capture=True, oneline=True)

  def Run(self, *cmd, **kwargs):
    return self.RunPipe([cmd], **kwargs)


def MakeChangeLog(changes):
    final = []
    need_blank = False
    for change in sorted(changes):
        out = []
        if need_blank:
            out.append('')
        out.append('Changes in v%d:' % change)
        for item in changes[change]:
            if item not in out:
                out.append(item)
        need_blank = True
        final += out
    if changes:
        final.append('')
    return final

# States we can be in
STATE_MSG_HEADER = 0        # Still in the message header
STATE_PATCH_HEADER = 1      # In patch header
STATE_DIFFS = 2             # In the diff part (past --- line)

class PatchStream:
    def __init__(self, series={}, is_log=False, name=None):
        self.skip_blank = False          # True to skip a single blank line
        self.found_test = False          # Found a TEST= line
        self.lines_after_test = 0        # MNumber of lines found after TEST=
        self.warn = []                   # List of warnings we have collected
        self.linenum = 1                 # Output line number we are up to
        self.in_section = None           # Name of start...END section we are in
        self.cover = None                # The cover letter contents
        self.notes = []                  # Series notes
        self.section = []                # The current section...END section
        self.series = series             # Info about the patch series
        self.is_log = is_log             # True if indent like git log
        self.in_change = 0               # Non-zero if we are in a change list
        self.changes = {}                # List of changelogs
        self.blank_count = 0             # Number of blank lines stored up
        self.name = name                 # Name of patch being processed
        self.state = STATE_MSG_HEADER    # What state are we in?
        self.tags = []                   # Tags collected, like Tested-by...
        self.signoff = None              # Contents of signoff line

        # Set up 'cc' which must a list
        if not self.series.get('cc'):
            self.series['cc'] = []

    def AddToSeries(self, line, name, value):
        if name in self.series:
            values = value.split(',')
            values = [str.strip() for str in values]
            if type(self.series[name]) != type([]):
                raise ValueError("In %s: line '%s': Cannot add another value "
                        "'%s' to series '%s'" %
                            (self.name, line, values, self.series[name]))
            self.series[name] += values
        elif name in valid_series:
            self.series[name] = value
            if name == 'notes':
                self.in_section = name
                self.skip_blank = False
        else:
            raise ValueError("In %s: line '%s': Unknown 'Series-%s': valid "
                        "options are %s" % (self.name, line, name,
                            ', '.join(valid_series)))

    def ProcessLine(self, line):
        """Process a single line of a patch file or commit log

        Args:
            line: text line to process

        Returns:
            list of output lines, or [] if nothing should be output"""
        out = []
        line = line.rstrip('\n')
        if self.is_log:
            if line[:4] == '    ':
                line = line[4:]
        series_match = re_series.match(line)
        commit_match = re_commit.match(line) if self.is_log else None
        tag_match = re_tag.match(line) if self.state == STATE_PATCH_HEADER else None
        is_blank = not line.strip()
        if is_blank and self.state == STATE_MSG_HEADER:
            self.state = STATE_PATCH_HEADER

        if re_prog.match(line):
            self.skip_blank = True
            if line.startswith('TEST='):
                self.found_test = True
        elif self.skip_blank and is_blank:
            self.skip_blank = False
        elif re_cover.match(line):
            self.in_section = 'cover'
            self.skip_blank = False
        elif self.in_section:
            if line == 'END':
                if self.in_section == 'cover':
                    self.cover = self.section
                elif self.in_section == 'notes':
                    self.notes += self.section
                else:
                    self.warn.append("Unknown section '%s'" % self.in_section)
                self.in_section = None
                self.skip_blank = True
                self.section = []
            else:
                self.section.append(line)
        elif self.in_change:
            if is_blank:
                # Blank line ends this change list
                self.in_change = 0
            else:
                self.changes[self.in_change].append(line)
            self.skip_blank = False
        elif re_copyright.match(line):
            out = ['+ * Copyright (c) 2011 The Chromium OS Authors.']
            self.warn.append("Changed copyright from '%s'" % line)
            self.skip_blank = False
        elif series_match:
            name = series_match.group(1)
            value = series_match.group(2)
            if name == 'changes':
                # value is the version number: e.g. 1, or 2
                value = int(value)
                if not self.changes.get(value):
                    self.changes[value] = []
                self.in_change = int(value)
            else:
                self.AddToSeries(line, name, value)
                self.skip_blank = True
        elif commit_match:
            self.name = commit_match.group(1)[:7]
        elif tag_match:
            if tag_match.group(1) == 'Signed-off-by':
                if self.signoff:
                    self.warn.append('Patch has more than one Signed-off-by '
                            'tag')
                else:
                    self.signoff = line
            else:
                self.tags.append(line)
        else:
            pos = 1
            # TODO: Would be nicer to report source filename and line
            for ch in line:
                if ord(ch) > 0x80:
                    self.warn.append('Line %d/%d has funny ascii character' %
                        (self.linenum, pos))
                pos += 1

            m = re_space_before_tab.match(line)
            if m:
                self.warn.append('Line %d/%d has space before tab' %
                    (self.linenum, m.start()))

            out = [line]
            self.linenum += 1
            self.skip_blank = False
            if self.state == STATE_DIFFS:
                pass
            elif line == '---':
                self.state = STATE_DIFFS

                # Output the tags (signeoff first), then change list
                out = []
                if self.signoff:
                    out += [self.signoff]
                out += sorted(self.tags) + [line] + MakeChangeLog(self.changes)
            elif self.found_test:
                if not re_allowed_after_test.match(line):
                    self.lines_after_test += 1
        #print line, out
        return out

    def Finalize(self):
        if self.lines_after_test:
            self.warn.append('Found %d lines after TEST=' %
                    self.lines_after_test)
        if self.cover:
            self.series['cover'] = self.cover
        if self.notes:
            self.series['notes'] = self.notes

    def ProcessStream(self, infd, outfd, name=None):
        """Copy a stream from infd to outfd, filtering out unwanting things.

        Args:
            infd: Input stream
            outfd: Output stream"""

        # Extract the filename from each diff, for nice warnings
        fname = None
        last_fname = None
        re_fname = re.compile('diff --git a/(.*) b/.*')
        while True:
            line = infd.readline()
            if not line:
                break
            out = self.ProcessLine(line)
            for line in out:
                # Swallow blank lines at end of file;
                # git format-patch 1.7.3.1 creates these for unknown reasons.
                match = re_fname.match(line)
                if match:
                    last_fname = fname
                    fname = match.group(1)
                if line == '+':
                    self.blank_count += 1
                else:
                    if self.blank_count and (line == '-- ' or match):
                        self.warn.append("Found possible blank lines at "
                                "end of file '%s'" % last_fname)
                    outfd.write('+\n' * self.blank_count)
                    outfd.write(line + '\n')
                    self.blank_count = 0
        self.Finalize()


def GetMetaData(count):
    """Reads out patch series metadata from the commits"""
    cmd = Command()
    pipe = [['git', 'log', '-n%d' % count]]
    stdout = cmd.RunPipe(pipe, capture=True)
    ps = PatchStream(is_log=True)
    for line in stdout.splitlines():
        ps.ProcessLine(line)
    ps.Finalize()
    return ps.series, ps.changes

def FixPatch(backup_dir, fname, series, name):
    """Fix up a patch file, putting a backup in back_dir (if not None).

    Returns a list of errors, or [] if all ok."""
    handle, tmpname = tempfile.mkstemp()
    outfd = os.fdopen(handle, 'w')
    infd = open(fname, 'r')
    ps = PatchStream(series, name)
    ps.ProcessStream(infd, outfd, fname)
    infd.close()
    outfd.close()

    # Create a backup file if required
    if backup_dir:
        shutil.copy(fname, os.path.join(backup_dir, os.path.basename(fname)))
    shutil.move(tmpname, fname)
    return ps.warn

def FixPatches(fnames):
    """Fix up a list of patches identified by filename
    TODO: Tidy this up by integrating properly with checkpatch
    """
    backup_dir = tempfile.mkdtemp('clean-patch')
    count = 0
    series = {}
    for fname in fnames:
        result = FixPatch(backup_dir, fname, series, 'patch %d' % count)
        if result:
            print '%d warnings for %s:' % (len(result), fname)
            for warn in result:
                print '\t', warn
            print
        count += 1
    print 'Cleaned %d patches' % count
    return series

def GetPatchPrefix(series):
    # Get version string
    version = ''
    if series.get('version'):
        version = ' v%s' % series['version']

    # Get patch name prefix
    prefix = ''
    if series.get('prefix'):
        prefix = '%s ' % series['prefix']
    return '%sPATCH%s' % (prefix, version)

def CreatePatches(count, series):
    """Create a series of patches from the top of the current branch.

    Args:
        count: number of commits to include
    Returns:
        Filename of cover letter
        List of filenames of patch files"""
    if series.get('version'):
        version = '%s ' % series['version']
    cmd = ['git', 'format-patch', '--signoff']
    if series.get('cover'):
        cmd.append('--cover-letter')
    prefix = GetPatchPrefix(series)
    if prefix:
        cmd += ['--subject-prefix=%s' % prefix]
    cmd += ['HEAD~%d' % count]

    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout, stderr = pipe.communicate()
    files = stdout.splitlines()
    #print '%d files' % len(files)
    if series.get('cover'):
       return files[0], files[1:]
    else:
       return None, files

def FindCheckPatch():
    path = os.getcwd()
    while not os.path.ismount(path):
        fname = os.path.join(path, 'src', 'third_party', 'kernel', 'files',
                'scripts', 'checkpatch.pl')
        if os.path.isfile(fname):
            return fname
        path = os.path.dirname(path)
    print 'Could not find checkpatch.pl'
    return None

def CheckPatch(verbose, fname):
    '''Run checkpatch.pl on a file.

    Returns:
        4-tuple containing:
            result: None = checkpatch broken, False=failure, True=ok
            problems: List of problems, each a dict:
                'type'; error or warning
                'msg': text message
                'file' : filename
                'line': line number
            lines: Number of lines'''
    result = None
    error_count, warning_count, lines = 0, 0, 0
    problems = []
    chk = FindCheckPatch()
    item = {}
    if chk:
        cmd = [chk, fname]
        pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, stderr = pipe.communicate()

        # total: 0 errors, 0 warnings, 159 lines checked
        re_stats = re.compile('total: (\\d+) errors, (\d+) warnings, (\d+)')
        re_ok = re.compile('.*has no obvious style problems')
        re_bad = re.compile('.*has style problems, please review')
        re_error = re.compile('ERROR: (.*)')
        re_warning = re.compile('WARNING: (.*)')
        re_file = re.compile('#\d+: FILE: ([^:]*):(\d+):')

        for line in stdout.splitlines():
            if verbose:
                print line
            match = re_stats.match(line)
            if match:
                error_count = int(match.group(1))
                warning_count = int(match.group(2))
                lines = int(match.group(3))
            elif re_ok.match(line):
                result = True
            elif re_bad.match(line):
                result = False
            match = re_error.match(line)
            if match:
                item['msg'] = match.group(1)
                item['type'] = 'error'
            match = re_warning.match(line)
            if match:
                item['msg'] = match.group(1)
                item['type'] = 'warning'
            match = re_file.match(line)
            if match:
                item['file'] = match.group(1)
                item['line'] = int(match.group(2))

                # We consider this message complete now
                # Record it and start the next one
                problems.append(item)
                item = {}
    return result, problems, error_count, warning_count, lines, stdout

def GetWarningMsg(msg_type, fname, line, msg):
    '''Create a message for a given file/line

    Args:
        msg_type: Message type ('error' or 'warning')
        fname: Filename which reports the problem
        line: Line number where it was noticed
        msg: Message to report
    '''
    if msg_type == 'warning':
        msg_type = col.Color(col.YELLOW, msg_type)
    elif msg_type == 'error':
        msg_type = col.Color(col.RED, msg_type)
    return '%s: %s,%d: %s' % (msg_type, fname, line, msg)

def CheckPatches(verbose, args):
    '''Run the checkpatch.pl script on each patch'''
    error_count = 0
    warning_count = 0
    col = Color()

    for fname in args:
        ok, problems, errors, warnings, lines, stdout = CheckPatch(verbose,
                    fname)
        if not ok:
            error_count += errors
            warning_count += warnings
            print '%d errors, %d warnings for %s:' % (errors,
                    warnings, fname)
            if len(problems) != error_count + warning_count:
                print "Internal error: some problems lost"
            for item in problems:
                print GetWarningMsg(item['type'], item['file'], item['line'],
                        item['msg'])
            #print stdout
    if error_count != 0 or warning_count != 0:
        str = 'checkpatch.pl found %d error(s), %d warning(s)' % (
            error_count, warning_count)
        color = col.GREEN
        if warning_count:
            color = col.YELLOW
        if error_count:
            color = col.RED
        print col.Color(color, str)
        return False
    return True

def ApplyPatch(verbose, fname):
    '''Apply a patch with git am to test it
    '''
    cmd = ['git', 'am', fname]
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    stdout, stderr = pipe.communicate()
    re_error = re.compile('^error: patch failed: (.+):(\d+)')
    for line in stderr.splitlines():
        if verbose:
            print line
        match = re_error.match(line)
        if match:
            print GetWarningMsg('warning', match.group(1), int(match.group(2)),
                    'Patch failed')
    return pipe.returncode == 0, stdout

def ApplyPatches(verbose, args):
    '''Apply the patches with git am to make sure all is well'''
    error_count = 0
    col = Color()

    cmd = ['git', 'name-rev', 'HEAD', '--name-only']
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout, stderr = pipe.communicate()
    if pipe.returncode:
        str = 'Could not find current commit name'
        print col.Color(col.RED, str)
        print stdout
        return False
    old_head = stdout.splitlines()[0]

    cmd = ['git', 'checkout', 'HEAD~%d' % len(args)]
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    stdout, stderr = pipe.communicate()
    if pipe.returncode:
        str = 'Could not move to commit before patch series'
        print col.Color(col.RED, str)
        print stdout, stderr
        return False

    for fname in args:
        ok, stdout = ApplyPatch(verbose, fname)
        if not ok:
            print col.Color(col.RED, 'git am returned errors for %s: will '
                    'skip this patch' % fname)
            if verbose:
                print stdout
            error_count += 1
            cmd = ['git', 'am', '--skip']
            pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            stdout, stderr = pipe.communicate()
            if pipe.returncode != 0:
                print col.Color(col.RED, 'Unable to skip patch! Aborting...')
                print stdout
                break

    cmd = ['git', 'checkout', old_head]
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = pipe.communicate()
    if pipe.returncode:
        print col.Color(col.RED, 'Could not move back to head commit')
        print stdout, stderr
    return error_count == 0

def InsertCoverLetter(fname, series, changes, count):
    """Creates a cover letter with the required info

    Args:
        fname: Output filename
        series: Series dictionary, containing element 'cover'
        changes: Change list, dictionary keyed by version 1, 2, 3;
                each item is an unsorted list of changes, one per line
        count: Number of patches in the series
    """
    fd = open(fname, 'r')
    lines = fd.readlines()
    fd.close()

    fd = open(fname, 'w')
    text = series['cover']
    prefix = GetPatchPrefix(series)
    for line in lines:
        if line.startswith('Subject:'):
            line = 'Subject: [%s 0/%d] %s\n' % (prefix, count, text[0])
        elif line.startswith('*** BLURB HERE ***'):
            # First the blurb test
            line = '\n'.join(text[1:]) + '\n'
            if series.get('notes'):
                line += '\n'.join(series['notes']) + '\n'

            # Now the change list
            out = MakeChangeLog(changes)
            line += '\n' + '\n'.join(out)
        fd.write(line)
    fd.close()

def LookupEmail(name):
    """If an email address is an alias, look it up and return the full name

    TODO: Why not just use git's own alias feature?

    Args:
        name: Name or email address

    Returns:
        name, if it is a valid email address,
          or real name, if name is an alias"""
    if '<' in name:
        return name

    # TODO: Turn all this into a class, and read the aliases once
    try:
        fd = open('%s/.config/clean-patch' % os.getenv('HOME'), 'r')
        lines = fd.readlines()
        fd.close()
    except IOError:
        print ('Error: If you want to use aliases, please create a '
            '~/.config/clean-patch file.')
        print
        raise

    re_alias = re.compile('%s: *(.*)' % name)
    for line in lines:
        match = re_alias.match(line)
        if match:
            return match.group(1)
    print "No match for alias '%s'" % name
    return name

def EmailPatches(series, cover_fname, args, dry_run):
    """Email a patch series.

    Args:
        series: dictionary containing destination info:
            'to' : to address
            'cc' : list of cc addresses
        cover_fname: filename of cover letter
        args: list of filenames of patch files
        dry_run: True to just email to yourself as a test"""
    dest = series.get('to')
    if not dest:
        print ("No recipient, please add something like this to a commit\n"
            "Series-to: Fred Bloggs <f.blogs@napier.co.nz>")
        return
    to = LookupEmail(dest)
    cc = ''
    if series.get('cc'):
        cc = ''.join(['-cc "%s" ' % LookupEmail(name)
                    for name in series['cc']])
    if dry_run:
        to = os.getenv('USER')
        cc = ''
    cmd = 'git send-email --annotate --to "%s" %s%s %s' % (to, cc,
        cover_fname and cover_fname or '', ' '.join(args))
    #print cmd
    os.system(cmd)

def CountCommitsToBranch():
    """Returns number of commits between HEAD and the tracking branch.

    This looks back to the tracking branch and works out the number of commits
    since then."""
    cmd = Command()
    pipe = [['git', 'branch'], ['grep', '^*']]
    branch = cmd.RunPipe(pipe, capture=True, oneline=True).split(' ')[1]

    pipe = [['git', 'config', '-l'], ['grep', '^branch\.%s' % branch]]
    stdout = cmd.RunPipe(pipe, capture=True)
    re_keyvalue = re.compile('(\w*)=(.*)')
    dict = {}
    for line in stdout.splitlines():
        m = re_keyvalue.search(line)
        dict[m.group(1)] = m.group(2)
    upstream_branch = dict['merge'].split('/')[-1]

    pipe = [['git', 'log', '--oneline',
                'remotes/%s/%s..' % (dict['remote'], upstream_branch)],
            ['wc', '-l']]
    stdout = cmd.RunPipe(pipe, capture=True, oneline=True)
    patch_count =int(stdout)
    return patch_count

class TestPatch(unittest.TestCase):
    """Test this silly program"""

    def testBasic(self):
        """Test basic filter operation"""
        data='''

From 656c9a8c31fa65859d924cd21da920d6ba537fad Mon Sep 17 00:00:00 2001
From: Simon Glass <sjg@chromium.org>
Date: Thu, 28 Apr 2011 09:58:51 -0700
Subject: [PATCH (resend) 3/7] Tegra2: Add more clock support

This adds functions to enable/disable clocks and reset to on-chip peripherals.

BUG=chromium-os:13875
TEST=build U-Boot for Seaboard, boot

Change-Id: I80fe1d0c0b7dd10aa58ce5bb1d9290b6664d5413

Review URL: http://codereview.chromium.org/6900006

Signed-off-by: Simon Glass <sjg@chromium.org>
---
 arch/arm/cpu/armv7/tegra2/Makefile         |    2 +-
 arch/arm/cpu/armv7/tegra2/ap20.c           |   57 ++----
 arch/arm/cpu/armv7/tegra2/clock.c          |  163 +++++++++++++++++
'''
        expected='''

From 656c9a8c31fa65859d924cd21da920d6ba537fad Mon Sep 17 00:00:00 2001
From: Simon Glass <sjg@chromium.org>
Date: Thu, 28 Apr 2011 09:58:51 -0700
Subject: [PATCH (resend) 3/7] Tegra2: Add more clock support

This adds functions to enable/disable clocks and reset to on-chip peripherals.

Signed-off-by: Simon Glass <sjg@chromium.org>
---
 arch/arm/cpu/armv7/tegra2/Makefile         |    2 +-
 arch/arm/cpu/armv7/tegra2/ap20.c           |   57 ++----
 arch/arm/cpu/armv7/tegra2/clock.c          |  163 +++++++++++++++++
'''
        out = ''
        inhandle, inname = tempfile.mkstemp()
        infd = os.fdopen(inhandle, 'w')
        infd.write(data)
        infd.close()

        exphandle, expname = tempfile.mkstemp()
        expfd = os.fdopen(exphandle, 'w')
        expfd.write(expected)
        expfd.close()

        FixPatch(None, inname)
        rc = os.system('diff -u %s %s' % (inname, expname))
        self.assertEqual(rc, 0)

        os.remove(inname)
        os.remove(expname)

    def GetData(self, data_type):
        data='''
From 4924887af52713cabea78420eff03badea8f0035 Mon Sep 17 00:00:00 2001
From: Simon Glass <sjg@chromium.org>
Date: Thu, 7 Apr 2011 10:14:41 -0700
Subject: [PATCH 1/4] Add microsecond boot time measurement

This defines the basics of a new boot time measurement feature. This allows
logging of very accurate time measurements as the boot proceeds, by using
an available microsecond counter.

%s
---
 README              |   11 ++++++++
 common/bootstage.c  |   50 ++++++++++++++++++++++++++++++++++++
 include/bootstage.h |   71 +++++++++++++++++++++++++++++++++++++++++++++++++++
 include/common.h    |    8 ++++++
 5 files changed, 141 insertions(+), 0 deletions(-)
 create mode 100644 common/bootstage.c
 create mode 100644 include/bootstage.h

diff --git a/README b/README
index 6f3748d..f9e4e65 100644
--- a/README
+++ b/README
@@ -2026,6 +2026,17 @@ The following options need to be configured:
 		example, some LED's) on your board. At the moment,
 		the following checkpoints are implemented:

+- Time boot progress
+		CONFIG_BOOTSTAGE
+
+		Define this option to enable microsecond boot stage timing
+		on supported platforms. For this to work your platform
+		needs to define a function timer_get_us() which returns the
+		number of microseconds since reset. This would normally
+		be done in your SOC or board timer.c file.
+
+		You can add calls to bootstage_mark() to set time markers.
+
 - Standalone program support:
 		CONFIG_STANDALONE_LOAD_ADDR

diff --git a/common/bootstage.c b/common/bootstage.c
new file mode 100644
index 0000000..2234c87
--- /dev/null
+++ b/common/bootstage.c
@@ -0,0 +1,50 @@
+/*
+ * Copyright (c) 2011, Google Inc. All rights reserved.
+ *
+ * See file CREDITS for list of people who contributed to this
+ * project.
+ *
+ * This program is free software; you can redistribute it and/or
+ * modify it under the terms of the GNU General Public License as
+ * published by the Free Software Foundation; either version 2 of
+ * the License, or (at your option) any later version.
+ *
+ * This program is distributed in the hope that it will be useful,
+ * but WITHOUT ANY WARRANTY; without even the implied warranty of
+ * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
+ * GNU General Public License for more details.
+ *
+ * You should have received a copy of the GNU General Public License
+ * along with this program; if not, write to the Free Software
+ * Foundation, Inc., 59 Temple Place, Suite 330, Boston,
+ * MA 02111-1307 USA
+ */
+
+
+/*
+ * This module records the progress of boot and arbitrary commands, and
+ * permits accurate timestamping of each. The records can optionally be
+ * passed to kernel in the ATAGs
+ */
+
+#include <common.h>
+
+
+struct bootstage_record {
+	uint32_t time_us;
+	const char *name;
+};
+
+static struct bootstage_record record[BOOTSTAGE_COUNT];
+
+uint32_t bootstage_mark(enum bootstage_id id, const char *name)
+{
+	struct bootstage_record *rec = &record[id];
+
+	/* Only record the first event for each */
+	if (!rec->name) {
+		rec->time_us = (uint32_t)timer_get_us();
+		rec->name = name;
+	}
+%sreturn rec->time_us;
+}
--
1.7.3.1
'''
        signoff = 'Signed-off-by: Simon Glass <sjg@chromium.org>\n'
        tab = '	'
        if data_type == 'good':
            pass
        elif data_type == 'no-signoff':
            signoff = ''
        elif data_type == 'spaces':
            tab = '   '
        else:
            print 'not implemented'
        return data % (signoff, tab)

    def SetupData(self, data_type):
        inhandle, inname = tempfile.mkstemp()
        infd = os.fdopen(inhandle, 'w')
        data = self.GetData(data_type)
        infd.write(data)
        infd.close()
        return inname

    def testCheckpatch(self):
        """Test checkpatch operation"""
        inname = self.SetupData('good')
        result, errors, warnings, lines, stdout = CheckPatch(inname)
        self.assertEqual(result, True)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(lines, 67)
        os.remove(inname)

        inname = self.SetupData('no-signoff')
        result, errors, warnings, lines, stdout = CheckPatch(inname)
        self.assertEqual(result, False)
        self.assertEqual(len(errors), 1)
        self.assertEqual(warnings, [])
        self.assertEqual(lines, 67)
        os.remove(inname)

        inname = self.SetupData('spaces')
        result, errors, warnings, lines, stdout = CheckPatch(inname)
        self.assertEqual(result, False)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(lines, 67)
        os.remove(inname)

def ShowActions(series, args):
    """Show what actions we will perform"""
    print 'Dry run, so not doing much. But I would do this:'
    print
    print 'Send a total of %d patches with %scover letter.' % (
            len(args), series.get('cover') and 'a ' or 'no ')
    for arg in args:
        print '   %s' % arg
    print
    email = series.get('to')
    print 'To: ', LookupEmail(email) if email else '<none>'
    if series.get('cc'):
        for item in series.get('cc'):
            print 'Cc: ', LookupEmail(item)
    print 'Version: ', series.get('version')
    print 'Prefix: ', series.get('prefix')
    if series.get('cover'):
        print 'Cover: %d lines' % len(series.get('cover'))


parser = OptionParser()
parser.add_option('-t', '--test', action='store_true', dest='test',
                  default=False, help='run tests')
parser.add_option('-c', '--count', dest='count', type='int',
       default=-1, help='Automatically create patches from top n commits')
parser.add_option('-n', '--dry-run', action='store_true', dest='dry_run',
       default=False, help='Do a try run by emailing to yourself')
parser.add_option('-i', '--ignore-errors', action='store_true',
       dest='ignore_errors', default=False,
       help='Send patches email even if patch errors are found')
parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
       default=False, help='Verbose output of errors and warnings')

(options, args) = parser.parse_args()

if options.test:
    sys.argv = [sys.argv[0]]
    unittest.main()
else:
    if options.count == -1:
        # Work out how many patches to send
        options.count = CountCommitsToBranch()

    col = Color()
    if not options.count:
        str = 'No commits found to process - please use -c flag'
        print col.Color(col.RED, str)
        sys.exit(1)

    if options.count:
        # Read the metadata
        series, changes = GetMetaData(options.count)
        #print series['notes']
        cover_fname, args = CreatePatches(options.count, series)
    series = FixPatches(args)
    if series and cover_fname and series.get('cover'):
        InsertCoverLetter(cover_fname, series, changes, options.count)

    # Check that each version has a change log
    if series.get('version'):
        changes_copy = dict(changes)
        for version in range(2, int(series['version']) + 1):
            if changes.get(version):
                del changes_copy[version]
            else:
                str = 'Change log missing for v%d' % version
                print col.Color(col.RED, str)
        for version in changes_copy:
            str = 'Change log for unknown version v%d' % version
            print col.Color(col.RED, str)
    elif changes:
        str = 'Change log exists, but no version is set'
        print col.Color(col.RED, str)

    ok = CheckPatches(options.verbose, args)
    if not ApplyPatches(options.verbose, args):
        ok = False
    if ok or options.ignore_errors:
        if not options.dry_run:
            EmailPatches(series, cover_fname, args, options.dry_run)

    if options.dry_run:
        ShowActions(series, args)
