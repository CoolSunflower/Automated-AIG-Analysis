import csv
import re

def parse_abc_output(content):
    # Initialize lists to store commands and stats
    commands = []
    and_values = []
    level_values = []
    
    # Extract commands and their corresponding stats
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        # Use a more flexible regex to match "abc" followed by any number of digits
        if re.match(r'abc \d+> ', lines[i]) and i+1 < len(lines):
            # Extract command after "abc XX> " - find the position of "> " and take everything after it
            cmd_start = lines[i].find("> ") + 2
            cmd = lines[i][cmd_start:].strip()
            
            # Skip reading print_stats lines as commands
            if cmd == "print_stats" or cmd == "strash" or cmd == "read project/fpu_orig.bench" or cmd == "source -s /abc.rc":
                i += 1
                continue
                
            # Check if the next line is a print_stats command
            if i+1 < len(lines) and re.match(r'abc \d+> print_stats', lines[i+1]):
                # Look for stats in the line after print_stats
                if i+2 < len(lines) and "[1;37m" in lines[i+2]:
                    stats_match = re.search(r'and =\s+(\d+)\s+lev = (\d+)', lines[i+2])
                    if stats_match:
                        and_val = stats_match.group(1)
                        level_val = stats_match.group(2)
                        
                        commands.append(cmd)
                        and_values.append(and_val)
                        level_values.append(level_val)
        
        i += 1
    
    # Group into recipes 
    all_recipes = []
    for i in range(0, len(commands), 20):
        if i + 20 <= len(commands):
            recipe_commands = commands[i:i+20]
            recipe_and = and_values[i:i+20]
            recipe_level = level_values[i:i+20]
            
            recipe_row = recipe_commands + recipe_and + recipe_level
            all_recipes.append(recipe_row)
    
    return all_recipes

def write_csv(recipes, output_file):
    header = [f"Step{i+1}" for i in range(20)] + \
             [f"AND{i+1}" for i in range(20)] + \
             [f"Level{i+1}" for i in range(20)]
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(recipes)
    
    print(f"Dataset saved to {output_file}")

# Main execution
output_file = "fpu/dataset.csv"

# Use the content from your file directly
with open("fpu/all_print_stats.txt", 'r') as f:
    content = f.read()

recipes = parse_abc_output(content)
write_csv(recipes, output_file)