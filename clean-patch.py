#!/usr/bin/python

# Patch creatiion and submission script
# Clean up patches ready for upstream by removing Chrome OS-specific things

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

(for u-boot it looks up ~/.config/clean-patch for lines like:
u-boot: "U-Boot Mailing List" <u-boot@lists.denx.de>
)
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
    '|Reviewed-on:|Reviewed-by:|Tested-by:')

# Lines which are allowed after a TEST= line
re_allowed_after_test = re.compile('^Signed-off-by:')

# The start of the cover letter
re_cover = re.compile('^Cover-letter:')

# Patch series
re_series = re.compile('^Series-(\w*): *(.*)')

# Copyright
re_copyright = re.compile('\+ \* Copyright \(c\) 2011, Google Inc. '
    'All rights reserved.')



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


def FixPatchStream(infd, outfd, series):
    """Copy a stream from infd to outfd, filtering out unwanting things.

    Args:
        infd: Input stream
        outfd: Output stream
        series: Dictionary to hold patch series information
    Returns:
        List of warnings, or [] if none.
        Updated series dictionary"""
    skip_blank = False          # True to skip a single blank line
    found_test = False          # Found a TEST= line
    lines_after_test = 0        # MNumber of lines found after TEST=
    patch_started = False       # Have we see a '---' line yet?
    warn = []                   # List of warnings we have collected
    linenum = 1                 # Output line number we are up to
    in_cover = False            # True if we are in the cover letter
    cover = None                # The cover letter contents
    while True:
        line = infd.readline()
        if not line:
            break

        line = line.rstrip('\n')
        #print '.%s.' % line

        # TODO: fix up this code
        series_match = re_series.match(line)
        if re_prog.match(line):
            skip_blank = True
            if line.startswith('TEST='):
                found_test = True
        elif skip_blank and not line.strip():
            skip_blank = False
        elif re_cover.match(line):
            in_cover = True
            cover = []
        elif in_cover:
            if line == 'END':
                in_cover = False
                skip_blank = True
            else:
                cover.append(line)
        elif re_copyright.match(line):
            outfd.write('+ * Copyright (c) 2011 The Chromium OS Authors.\n')
            warn.append("Changed copyright from '%s'" % line)
        elif series_match:
            name = series_match.group(1)
            value = series_match.group(2)
            if name in series:
                series[name].append(value)
            else:
                series[name] = value
            skip_blank = True
        else:
            pos = 1
            for ch in line:
                if ord(ch) > 0x80:
                    warn.append('Line %d/%d has funny ascii character' %
                        (linenum, pos))
                pos += 1

            outfd.write(line)
            outfd.write('\n')
            linenum += 1
            skip_blank = False
            if patch_started:
                pass
            elif line.startswith('---'):
                patch_started = True
            elif found_test:
                if not re_allowed_after_test.match(line):
                    lines_after_test += 1
    if lines_after_test:
        warn.append('Found %d lines after TEST=' % lines_after_test)
    if cover:
        series['cover'] = cover
    return warn

def GetMetaData(count):
    """Reads out patch series metadata from the commits"""
    cmd = Command()
    pipe = [['git', 'log', '-n%d' % count]]
    stdout = cmd.RunPipe(pipe, capture=True).splitlines()

def FixPatch(backup_dir, fname, series):
    """Fix up a patch file, putting a backup in back_dir (if not None).

    Returns a list of errors, or [] if all ok."""
    handle, tmpname = tempfile.mkstemp()
    out = os.fdopen(handle, 'w')
    fd = open(fname, 'r')
    result = FixPatchStream(fd, out, series)
    fd.close()
    out.close()
    if backup_dir:
        shutil.copy(fname, os.path.join(backup_dir, os.path.basename(fname)))
    shutil.move(tmpname, fname)
    return result

def FixPatches(fnames):
    """Fix up a list of patches identified by filename"""
    backup_dir = tempfile.mkdtemp('clean-patch')
    count = 0
    series = {'cc' : []}
    for fname in fnames:
        result = FixPatch(backup_dir, fname, series)
        if result:
            print '%d warnings for %s:' % (len(result), fname)
            for warn in result:
                print '\t', warn
            print
        count += 1
    print 'Cleaned %d patches' % count
    return series

def CreatePatches(count):
    """Create a series of patches from the top of the current branch.

    Args:
        count: number of commits to include
    Returns:
        Filename of cover letter
        List of filenames of patch files"""
    cmd = ['git', 'format-patch', '--signoff', '--cover-letter',
        'HEAD~%d' % count]

    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout, stderr = pipe.communicate()
    files = stdout.splitlines()
    #print '%d files' % len(files)
    return files[0], files[1:]

def FindCheckPatch():
    path = os.getcwd()
    while not os.path.ismount(path):
        fname = os.path.join(path, 'src', 'third_party', 'kernel-next',
                'scripts', 'checkpatch.pl')
        if os.path.isfile(fname):
            return fname
        path = os.path.dirname(path)
    print 'Could not find checkpatch.pl'
    return None

def CheckPatch(fname):
    '''Run checkpatch.pl on a file.

    Returns:
        4-tuple containing:
            result: None = checkpatch broken, False=failure, True=ok
            errors: Number of errors
            warnings: Number of warnings
            lines: Number of lines'''
    result = None
    error_count, warning_count, lines = 0, 0, 0
    warnings = []
    errors = []
    chk = FindCheckPatch()
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

        for line in stdout.splitlines():
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
                errors.append(match.group(1))
            match = re_warning.match(line)
            if match:
                warnings.append(match.group(1))
    return result, errors, warnings, lines, stdout

def CheckPatches(args):
    '''Run the checkpatch.pl script on each patch'''
    error_count = 0
    warning_count = 0
    for fname in args:
        ok, errors, warnings, lines, stdout = CheckPatch(fname)
        if not ok:
            error_count += len(errors)
            warning_count += len(warnings)
            print '%d errors, %d warnings for %s:' % (len(errors),
                    len(warnings), fname)
            for line in errors + warnings:
                print line
            print stdout
    if error_count != 0 or warning_count != 0:
        print 'checkpatch.pl found %d error(s), %d warning(s)' % (
            error_count, warning_count)
        return False
    return True

def InsertCoverLetter(fname, series, count):
    """Insert the given text into the cover letter"""
    #script = '-e s|Subject:.*|Subject: [PATCH 0/%d] %s|' % (count, text[0])
    #cmd = 'sed -i "%s" %s' % (script, fname)
    #print cmd
    #os.system(cmd)
    fd = open(fname, 'r')
    lines = fd.readlines()
    fd.close()

    fd = open(fname, 'w')
    text = series['cover']

    # Get version string
    version = ''
    if series.get('version'):
        version = ' v%s' % series['version']

    # Get patch name prefix
    prefix = ''
    if series.get('prefix'):
        prefix = '%s ' % series['prefix']

    for line in lines:
        if line.startswith('Subject:'):
            line = 'Subject: [%sPATCH 0/%d%s] %s\n' % (prefix, count,
                    version, text[0])
        elif line.startswith('*** BLURB HERE ***'):
            line = '\n'.join(text[1:])
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
    if not series.get('to'):
        print ('No destination, please add Series-to: '
            'Fred Bloggs <f.blogs@napier.co.nz> to a commit')
    to = LookupEmail(series['to'])
    cc = ''
    if series.get('cc'):
        cc = ''.join(['-cc "%s" ' % LookupEmail(name) for name in series['cc']])
    if dry_run:
        to = os.getenv('USER')
        cc = ''
    cmd = 'git send-email --annotate --to "%s" %s%s %s' % (to, cc, cover_fname,
        ' '.join(args))
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

(options, args) = parser.parse_args()

if options.test:
    sys.argv = [sys.argv[0]]
    unittest.main()
else:
    if options.count == -1:
        # Work out how many patches to send
        options.count = CountCommitsToBranch()

    if options.count:
        # Read the metadata
        seies = GetMetaData(options.count)
        cover_fname, args = CreatePatches(options.count)
    series = FixPatches(args)
    if series and cover_fname:
        InsertCoverLetter(cover_fname, series, options.count)
    if CheckPatches(args) or options.ignore_errors:
        EmailPatches(series, cover_fname, args, options.dry_run)
        pass

