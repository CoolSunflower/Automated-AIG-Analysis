"""
abc/abc -f test.txt > hello.txt

OR
"""
import subprocess

# Path to ABC binary (update if needed)
abc_path = "./abc/abc"

# Commands to be executed inside ABC
abc_commands = """
source -s abc.rc
read_bench abc/project/bc0_orig.bench;
strash;
print_stats
"""

# Run ABC as a subprocess
process = subprocess.Popen(abc_path, 
                           stdin=subprocess.PIPE, 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE, 
                           text=True)

# Send commands to ABC
stdout, stderr = process.communicate(abc_commands)

# Save output
with open("abc_output.txt", "w") as f:
    f.write(stdout)

# Print output
print("ABC Output:\n", stdout)

# Print errors (if any)
if stderr:
    print("ABC Errors:\n", stderr)
