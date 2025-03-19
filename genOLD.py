"""
This file generates test cases for the given design, it also runs the test cases and parses the output to create a structured document.
"""

import os
import random
import subprocess
from tqdm import tqdm
import time
import sys

DESIGN_NAME = "fpu"
DESIGN_LOCATION = f"abc/project/{DESIGN_NAME}_orig.bench"
SCRIPT_LOCATION = DESIGN_NAME + "/" + "scripts"
UPDATES_AIG_LOCATION = DESIGN_NAME + "/" + "updatedAIG"
OUTPUT_LOCATION = DESIGN_NAME + "/" + "outputs"

# ADD MORE COMMANDS
COMMANDS = ["rewrite -z","rewrite -l", "rewrite", "balance", "resub", "refactor", "resub -z", "refactor -z"]

NUM_FILES = 10
NUM_COMMANDS = 20

def run():
    os.makedirs(DESIGN_NAME, exist_ok=True)
    os.makedirs(SCRIPT_LOCATION, exist_ok=True)
    os.makedirs(UPDATES_AIG_LOCATION, exist_ok=True)
    os.makedirs(OUTPUT_LOCATION, exist_ok=True)

    # Generate files and execute command in ABC
    for i in tqdm(range(NUM_FILES)):
        script_file_path = os.path.join(SCRIPT_LOCATION, f"s{i}.txt")

        with open(script_file_path, "w") as f:


            f.write(f"read_bench {DESIGN_LOCATION}\n")
            f.write("source -s abc/abc.rc\n")
            f.write("strash\n")
            f.write("print_stats\n")
            
            # Generate 20 non-repeating consecutive commands
            last_command = None
            for _ in range(NUM_COMMANDS):
                command = random.choice(COMMANDS)
                while command == last_command:  # Ensure no consecutive repetition
                    command = random.choice(COMMANDS)
                f.write(f"{command}\n")
                last_command = command  # Update last used command
                f.write("print_stats\n")
            f.write(f"write_bench -l {UPDATES_AIG_LOCATION}/{i}.bench\n")
            f.write("dch\n")

        # execute script
        subprocess.run(f"abc/abc -f {script_file_path} > {OUTPUT_LOCATION}/{i}", shell=True)

if __name__ == "__main__":
    run()