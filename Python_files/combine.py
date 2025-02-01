import os
import re

# Input files and directories
main_file_path = 'main3.tex'
sections_dir = 'sections'

# Output file
output_file_path = 'reassembled_document.tex'

# Open the main file and read its content
with open(main_file_path, 'r') as main_file:
    main_content = main_file.read()


# Function to replace \include*{filename} with the content of the file
def replacer(match):
    filename = match.group(1)  # Get the filename from the regex match
    filepath = f"{filename}.tex"
    with open(filepath, 'r') as file:
        return file.read()

# Use a regex to find all \include*{filename} commands and replace them
replaced_content = re.sub(r'\\include\{(.+?)\}', replacer, main_content)

# Write the replaced content to the output file
with open(output_file_path, 'w') as output_file:
    output_file.write(replaced_content)
