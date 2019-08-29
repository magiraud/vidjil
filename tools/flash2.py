from os import listdir, path, makedirs
from os.path import isfile, join
import sys
import shutil
import gzip
import subprocess
import argparse
import shlex
import os

parser = argparse.ArgumentParser(description='Use FLASH2 read merger to make a new fastq file and keep unmerged reads')

parser.add_argument("flash2_dir", help="path to flash2 executable")
parser.add_argument("file_R1", help="forward read file")
parser.add_argument("file_R2", help="reverse read file")
parser.add_argument("output_file", help="output file")
parser.add_argument("-r1", "--keep_r1", help="keep unmerged forward reads", action="store_true")
parser.add_argument("-r2", "--keep_r2", help="keep unmerged reverse reads", action="store_true")
parser.add_argument("-f", "--flash2-options", help="additional options passed to FLASH2", default="")
parser.add_argument("-k", "--keep", help="keep temporary files (may take lots of disk space in the end)", action = 'store_true')


args  = parser.parse_args()
f_r1  = args.file_R1
f_r2  = args.file_R2
f_out = args.output_file


exit_code = subprocess.call(['%s/flash2' % args.flash2_dir,
 f_r1, f_r2,
 "-d", f_out,
 # "-j", "1"]
                # + shlex.split(args.flash2_options)
])

if exit_code > 0:
    raise EnvironmentError("Flash2 failed")

try :
    with gzip.open(f_out+".fastq.gz", 'w') as outFile:
        with open(f_out+'.extendedFrags.fastq', 'rb') as f1:
            shutil.copyfileobj(f1, outFile)
        if (args.keep_r1):
            with open(f_out+'.notCombined_1.fastq', 'rb') as f2:
                shutil.copyfileobj(f2, outFile)
        if (args.keep_r2):
            with open(f_out+'.notCombined_2.fastq', 'rb') as f3:
                shutil.copyfileobj(f3, outFile)
        if not args.keep:
            os.remove(f_out+'.extendedFrags.fastq')
            os.remove(f_out+'.notCombined_1.fastq')
            os.remove(f_out+'.notCombined_2.fastq')
        ## Remove the histogram provide by Flash2
        os.remove(f_out+'.hist')
        os.remove(f_out+'.histogram')
except IOError :
    os.remove(f_out)
    raise
