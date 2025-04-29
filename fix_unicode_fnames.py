#!/usr/bin/env python3

# Find filenames which cannot be backed up to Google Cloud and rename them

import argparse
import os

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--no-write', action='store_true',
                        help="Dry run - don't write any changes")
    parser.add_argument('paths', type=str, nargs='*',
                        help='List of directories to process')
    return parser.parse_args()

def process_path(path, no_write):
    for dirpath, dirnames, fnames in os.walk(path):
        seq = 0
        for fname in fnames:
            new_fname = None
            try:
                check = fname.encode('utf-8')
                if '!' in fname:
                    good_fname = fname
                    new_fname = fname.replace('!', '_pling_')
                    new_path = os.path.join(dirpath, new_fname)
                elif '\n' in fname:
                    good_fname = fname
                    new_fname = fname.replace('\n', '_newline_')
                    new_path = os.path.join(dirpath, new_fname)
                else:
                    continue
            except UnicodeEncodeError:
                pass
            if not new_fname:
                bin_fname = fname.encode('utf-8', errors='ignore')
                good_fname = bin_fname.decode('utf-8')
                print('show', good_fname)

                while True:
                    new_fname = f'bad_{seq}_{good_fname}'
                    new_path = os.path.join(dirpath, new_fname)
                    if not os.path.exists(new_path):
                        break
                    seq += 1

            good_dirpath = dirpath.encode('utf-8', errors='ignore').decode('utf-8')
            #print('dirpath', good_dirpath)
            print(f'Rename in {good_dirpath}: {good_fname} to {new_fname}')
            if not no_write:
                bad_path = os.path.join(dirpath, fname)
                os.rename(bad_path, new_path)
            seq += 1

        for dir in dirnames:
            if '!' in dir:
                bad_path = os.path.join(dirpath, dir)
                new_dir = dir.replace('!', '_pling_')
                new_path = os.path.join(dirpath, new_dir)
                good_dir = dir.encode('utf-8', errors='ignore').decode('utf-8')
                good_new_dir = new_dir.encode('utf-8', errors='ignore').decode('utf-8')
                good_dirpath = dirpath.encode('utf-8', errors='ignore').decode('utf-8')
                print(f'Rename in {good_dirpath}: dir {good_dir} to {good_new_dir}')
                if not no_write:
                    os.rename(bad_path, new_path)

def doit():
    args = parse_args()
    for path in args.paths:
        process_path(path, args.no_write)

if __name__ == "__main__":
    doit()
