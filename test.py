import os
import random
import subprocess
import concurrent.futures
import csv
import re
from tqdm import tqdm
import time
import sys
import threading
import io

DESIGN_NAME = "fpu"  # Updated to match your output
DESIGN_LOCATION = f"abc/project/{DESIGN_NAME}_orig.bench"
SCRIPT_LOCATION = DESIGN_NAME + "/" + "scripts"
UPDATES_AIG_LOCATION = DESIGN_NAME + "/" + "updatedAIG"
OUTPUT_LOCATION = DESIGN_NAME + "/" + "outputs"
CSV_OUTPUT = DESIGN_NAME + "/" + "dataset.csv"

# Commands list
COMMANDS = ["rewrite -z","rewrite -l", "rewrite", "balance", "resub", "refactor", "resub -z", "refactor -z"]

NUM_FILES = 50000
NUM_COMMANDS = 20
MAX_WORKERS = os.cpu_count()
BUFFER_SIZE = 100  # Number of rows to buffer before writing to file

# Lock for CSV writing
csv_lock = threading.Lock()

# Thread-local storage for string buffers
thread_local = threading.local()

class CSVBufferManager:
    def __init__(self, filename, header):
        self.filename = filename
        self.header = header
        self.buffers = {}  # Dictionary to store buffers for each thread
        self.buffer_lock = threading.Lock()
        
        # Initialize the CSV file with headers
        with open(self.filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(self.header)
    
    def get_buffer(self, thread_id):
        """Get or create a buffer for the current thread"""
        with self.buffer_lock:
            if thread_id not in self.buffers:
                self.buffers[thread_id] = []
            return self.buffers[thread_id]
    
    def add_row(self, thread_id, row):
        """Add a row to the thread's buffer and flush if needed"""
        buffer = self.get_buffer(thread_id)
        buffer.append(row)
        
        # If buffer reached the threshold, flush it
        if len(buffer) >= BUFFER_SIZE:
            self.flush_buffer(thread_id)
    
    def flush_buffer(self, thread_id):
        """Write the buffer content to the CSV file"""
        with self.buffer_lock:
            if thread_id in self.buffers and self.buffers[thread_id]:
                buffer = self.buffers[thread_id]
                self.buffers[thread_id] = []  # Reset buffer
                
                # Only acquire the file lock when we have data to write
                with csv_lock:
                    with open(self.filename, 'a', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerows(buffer)
    
    def flush_all(self):
        """Flush all buffers at the end of processing"""
        with self.buffer_lock:
            thread_ids = list(self.buffers.keys())
            
        for thread_id in thread_ids:
            self.flush_buffer(thread_id)

def parse_output(output_file, commands):
    """Parse the ABC output file to extract AND gate counts and levels"""
    and_counts = []
    levels = []
    
    try:
        with open(output_file, 'r') as f:
            content = f.read()
        
        # Manual parsing approach which is more reliable for your format
        lines = content.splitlines()
        matches = []
        for line in lines:
            if "and =" in line and "lev =" in line:
                parts = line.split("and =")[1].split("lev =")
                and_count = int(parts[0].strip())
                level = int(parts[1].strip())
                matches.append((str(and_count), str(level)))
        
        # Skip the initial stats (first match) and get stats for each command
        for match in matches[1:NUM_COMMANDS+1]:
            and_count, level = match
            and_counts.append(int(and_count))
            levels.append(int(level))
        
        # Ensure we have exactly NUM_COMMANDS entries
        while len(and_counts) < NUM_COMMANDS:
            and_counts.append(None)
            levels.append(None)
        
        # Trim to exact NUM_COMMANDS entries if we have too many
        and_counts = and_counts[:NUM_COMMANDS]
        levels = levels[:NUM_COMMANDS]
        
        return commands, and_counts, levels
    except Exception as e:
        print(f"Error parsing output file {output_file}: {e}")
        return commands, [None] * NUM_COMMANDS, [None] * NUM_COMMANDS

def process_file(i, buffer_manager):
    """Process a single test case and buffer results for CSV generation"""
    try:
        thread_id = threading.get_ident()
        script_file_path = os.path.join(SCRIPT_LOCATION, f"s{i}.txt")
        output_file_path = os.path.join(OUTPUT_LOCATION, str(i))
        
        # Generate random commands (avoiding consecutive repetition)
        commands = []
        last_command = None
        for _ in range(NUM_COMMANDS):
            command = random.choice(COMMANDS)
            while command == last_command:
                command = random.choice(COMMANDS)
            commands.append(command)
            last_command = command
        
        # Write script file
        with open(script_file_path, "w") as f:
            f.write(f"read_bench {DESIGN_LOCATION}\n")
            f.write("source -s abc/abc.rc\n")
            f.write("strash\n")
            f.write("print_stats\n")
            
            for cmd in commands:
                f.write(f"{cmd}\n")
                f.write("print_stats\n")
            
            # f.write(f"write_bench -l {UPDATES_AIG_LOCATION}/{i}.bench\n")
            f.write("dch\n")
        
        # Execute script
        subprocess.run(f"abc/abc -f {script_file_path} > {output_file_path}", shell=True)
        
        # Parse output
        commands, and_counts, levels = parse_output(output_file_path, commands)
        
        # Create row data in proper order
        row = []
        # First add all command steps
        for cmd in commands:
            row.append(cmd)
        # Then add all AND gate counts
        for and_count in and_counts:
            row.append(and_count)
        # Finally add all levels
        for level in levels:
            row.append(level)
        
        # Add row to buffer
        buffer_manager.add_row(thread_id, row)
        
        return True
    except Exception as e:
        print(f"Error processing file {i}: {e}")
        return False

def run():
    # Create necessary directories
    os.makedirs(DESIGN_NAME, exist_ok=True)
    os.makedirs(SCRIPT_LOCATION, exist_ok=True)
    os.makedirs(UPDATES_AIG_LOCATION, exist_ok=True)
    os.makedirs(OUTPUT_LOCATION, exist_ok=True)

    # Prepare CSV header
    header = []
    for i in range(1, NUM_COMMANDS+1):
        header.append(f'Step{i}')
    for i in range(1, NUM_COMMANDS+1):
        header.append(f'AND{i}')
    for i in range(1, NUM_COMMANDS+1):
        header.append(f'Level{i}')
    
    # Initialize buffer manager
    buffer_manager = CSVBufferManager(CSV_OUTPUT, header)
    
    # Process files in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit tasks
        futures = [executor.submit(process_file, i, buffer_manager) for i in range(NUM_FILES)]
        
        # Monitor progress
        for _ in tqdm(concurrent.futures.as_completed(futures), total=NUM_FILES, desc="Processing files"):
            pass
    
    # Ensure all remaining buffered data is written
    buffer_manager.flush_all()

if __name__ == "__main__":
    run()
