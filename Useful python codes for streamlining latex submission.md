---
created: 2023-11-30T18:20
updated: 2025-01-10T10:17
---

# Steps to process a latex file for journal submission


1. Use arxiv_latex_cleaner. [GitHub - google-research/arxiv-latex-cleaner: arXiv LaTeX Cleaner: Easily clean the LaTeX code of your paper to submit to arXiv](https://github.com/google-research/arxiv-latex-cleaner)

```
arxiv_latex_cleaner latex.tex --keep_bib
```


2. Do the following:
## A code that finds all the dependencies of a latex file and puts all of those along with the latex file in a folder called new_folder


```python
import os
import re
import shutil


# Replace with the name of your .tex file

filename = 'Model Reduction of a Piecewise Nonlinear Mechanical_v2a.tex'
filename2 = 'Model Reduction of a Piecewise Nonlinear Mechanical_v2b.tex'

# Base directory of the .tex file
base_dir = os.path.dirname(os.path.abspath(filename))

# Extract graphics path(s) from the .tex file
with open(filename, 'r') as file:
    content = file.read()



# Regular expressions to match various commands

patterns = [
    re.compile(r'\\includegraphics.*\{(.+?)\}'),  # for \includegraphics
    re.compile(r'\\input\{(.+?)\}'),  # for \input
    re.compile(r'\\include\{(.+?)\}'),  # for \include
    re.compile(r'\\bibliography\{(.+?)\}'),  # for \bibliography
]

# Regular expression to match \graphicspath command
graphicspath_pattern = re.compile(r'\\graphicspath\{\{(.+?)\}\}')
graphics_paths = graphicspath_pattern.findall(content)

# Normalize the paths
graphics_paths = [os.path.normpath(path) for path in graphics_paths]

  
# Replace with the name of your new folder
new_folder = 'new_folder'
# Create the new folder if it does not exist
os.makedirs(new_folder, exist_ok=True)

  

# List of possible file extensions supported by LaTeX
image_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.eps']


# Find all matches for each pattern

for pattern in patterns:
    matches = pattern.findall(content)
    for match in matches:
        match = os.path.normpath(match)  # Normalize the file path
        new_path = ''  # Variable to store the new path
        # If dealing with \includegraphics, try different extensions
        if pattern == patterns[0] and not any(match.endswith(ext) for ext in image_extensions):
            found = False  # Flag to check if the file is found with any extension
            for ext in image_extensions:
                file_path = os.path.join(base_dir, match + ext)
                if os.path.exists(file_path):
                    new_path = os.path.join(new_folder, os.path.basename(match + ext))
                    shutil.copy(file_path, new_folder)
                    found = True
                    break

            if not found and graphics_paths:  # If not found, check in graphics_paths
                for ext in image_extensions:
                    for gpath in graphics_paths:
                        file_path = os.path.join(base_dir, gpath, match + ext)
                        if os.path.exists(file_path):
	                        base_path = os.path.basename(match + ext)
                            new_path = os.path.join(new_folder, base_path)
                            shutil.copy(file_path, new_folder)
                            found = True
                            break

                    if found:
                        break

            if not found:
                print(f"Image file not found: {os.path.join(base_dir, match)}")

            else:
                content = content.replace(match, base_path)  # Replace old path with new path in content

        else:
            if pattern == patterns[3] and not match.endswith('.bib'):
                match += '.bib'
                
            file_path = os.path.join(base_dir, match)

            if os.path.exists(file_path):
                new_path = os.path.join(new_folder, os.path.basename(match))
                shutil.copy(file_path, new_folder)
                content = content.replace(match, base_path)  # Replace old path with new path in content

            else:
                print(f"File not found: {file_path}")

# Write the modified content to a new .tex file in the new folder

new_tex_file = os.path.join(new_folder, os.path.basename(filename2))

with open(new_tex_file, 'w') as file:
    file.write(content)
```


3. Then do the following:
## Python code to split each section into different tex files


```python
import os
import re

# Path to the input file and output directory
input_file = 'Manuscript.tex'
output_dir = 'sections'
os.makedirs(output_dir, exist_ok=True)

# Running the complete Python script again on the newly uploaded file
# Resetting variables for the new run
# Modifying the script to generate the main.tex file with all the \include and \includeonly commands.

section_content = []
section_files = []
preamble_content = ''
inside_preamble = True
inside_abstract = False
outfile = None
unmatched_lines = []  # to store lines that seem like sections but are not matched
bib_commands = ''  # to store bibliography and bibliography style commands


# Handle Abstract
begin_abstract_in_line = False
end_abstract_in_line = False

try:
    with open(input_file, 'r') as infile:
        for line in infile:
            
            # Handling Bibliography
            bib_match = re.search(r'\\bibliography{(.+?)}', line)
            bib_filename = bib_match.group(1) if bib_match else None
            if bib_filename:
                bib_commands += f"\\bibliography{{{bib_filename}}}\n"

            # Handling Bibliography Style
            bibstyle_match = re.search(r'\\bibliographystyle{(.+?)}', line)
            bibstyle_filename = bibstyle_match.group(1) if bibstyle_match else None
            if bibstyle_filename:
                bib_commands += f"\\bibliographystyle{{{bibstyle_filename}}}\n"
            
            if '\\begin{abstract}' in line:
                inside_abstract = True
                begin_abstract_in_line = True
                output_file = 'abstract'
                if outfile:
                    outfile.close()
                    outfile = None
                output_file_path = os.path.join(output_dir, f'{output_file}.tex')
                outfile = open(output_file_path, 'w')
                continue

            if '\\end{abstract}' in line:
                inside_abstract = False
                end_abstract_in_line = True
                if outfile:
                    outfile.write('\n\\end{abstract}')
                    outfile.close()
                    outfile = None
                section_content.append(f"\\include{{sections/{output_file}}}")
                section_files.append(f"sections/{output_file}")
                continue

            # Handle other sections or appendices
            match = re.match(r'\\(section\*?|appendix|preamble)\{(.+?)\}', line)
            if line.strip() == '\\begin{document}':
                inside_preamble = False
            elif inside_preamble:
                preamble_content += line
            elif match or line.strip() in ['\\end{document}']:
                if outfile:
                    outfile.close()
                    outfile = None
                
                if line.strip() == '\\end{document}':
                    break
                output_file = match.group(2).strip().replace(" ", "_") if match else None
                if output_file:  # Ensuring output_file is not None or empty
                    output_file_path = os.path.join(output_dir, f'{output_file}.tex')
                    outfile = open(output_file_path, 'w')
                else:  # Collect unmatched lines that seem like sections
                    unmatched_lines.append(line.strip())
                
                section_content.append(f"\\include{{sections/{output_file}}}")
                section_files.append(f"sections/{output_file}")

            if outfile and not inside_preamble:
                if '\\bibliographystyle{' not in line and '\\bibliography{' not in line:
                    if begin_abstract_in_line:
                        outfile.write('\\begin{abstract}\n'+line)
                        begin_abstract_in_line = False
                    else:
                        outfile.write(line)
except Exception as e:
    error_message = str(e)

# After exiting the loop, close the last outfile if it is open
if outfile:
    outfile.close()

# Writing \include for all section files
all_sections_content = '\n'.join(["\\include{"+f"{itr}"+"}" for itr in section_files])

# Add \includeonly to the preamble
preamble_content = preamble_content.split('\\begin{document}')[0]  # Removing everything after \begin{document}
preamble_content += '\n\\includeonly{'
preamble_content += '\n'.join([f"{itr}," for itr in section_files[:-1]])
preamble_content += '\n'+f"{section_files[-1]}"
preamble_content += "\n"+"}"+"\n"


preamble_content += '\\begin{document}\n\\maketitle\n'+'\\begingroup\n\let\clearpage\\relax'

# Write the main file
new_main_file_path = 'main3.tex'
main_file_content = preamble_content + "\n\n" + all_sections_content +'\n\\endgroup' +f"\n{bib_commands}" + "\n\\end{document}"

# Writing the main file content to main.tex in the correct directory
with open(new_main_file_path, 'w') as main_file:
    main_file.write(main_file_content)

# Reading the content of the main.tex file again to verify the corrections
with open(new_main_file_path, 'r') as main_file:
    corrected_new_main_file_content = main_file.read()

# Displaying the corrected main file content
corrected_new_main_file_content
```


3. Every sentence in a new line

```python
import os
import re


def process_latex_file(input_filepath: str, output_filepath: str):
    with open(input_filepath, 'r') as infile:
        latex_content = infile.read()

    # Regular expression to match \begin{} and \end{} environments
    env_pattern = re.compile(r'(\\begin\{.*?\}.*?\\end\{.*?\})', re.DOTALL)

    # Split content into environments and non-environment text
    chunks = re.split(env_pattern, latex_content)

    # Process only the non-environment text
    processed_chunks = []
    for chunk in chunks:
        if chunk.strip().startswith('\\begin'):  # if it's an environment, keep it unchanged
            processed_chunks.append(chunk)
        else:  # otherwise, split into sentences and join with newlines
            sentences = re.split(r'(?<=\.)\s', chunk)
            processed_chunks.append('\n'.join(sentences))

    # Join the processed chunks
    processed_content = ''.join(processed_chunks)

    # Write the processed content to the output file
    with open(output_filepath, 'w') as outfile:
        outfile.write(processed_content)


def process_all_tex_files(root_dir: str, output_dir: str):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.tex') and "_processed" not in filename:
                input_filepath = os.path.join(dirpath, filename)
                output_filepath = os.path.join(output_dir, filename.replace('.tex', '_processed.tex'))
                process_latex_file(input_filepath, output_filepath)



# Example usage
root_dir = r"D:\D\ONEDRIVE\OneDrive - Texas A&M University\CLEMSON_RAJ\Journal_submission\Overleaf Projects (1 items)\Modified_arXiv\\sections\\" # replace with the path to your .tex files
output_dir = 'output'  # replace with the path where you want to save processed files
process_all_tex_files(root_dir, output_dir)

```



6. Then use latexindent.pl on each tex files.

_latexindent is in this folder_

```batch
for %f in (*.tex) do latexindent "%f" > "%~nf_indented.tex"

## Inplace

for %f in (*.tex) do latexindent -w "%f"


```


7. Reassemble

```python
# Make minor adjustments

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


```


6. One last time look over the figures, equations, tables carefully. Generate a latex file that has all these. Check them separately. If needed, mark changes in the PDF and then again change them in the tex file. 

```python
import re

def extract_environments(latex_code, environments):
    """
    Extract specified environments from the LaTeX code.

    :param latex_code: A string containing raw LaTeX code.
    :param environments: A list of environment names to extract.
    :return: A dictionary with environment names as keys and a list of extracted environments as values.
    """
    extracted = {}
    for env in environments:
        pattern = re.compile(r'\\begin\{' + env + r'\}.*?\\end\{' + env + r'\}', re.DOTALL)
        extracted[env] = re.findall(pattern, latex_code)

    return extracted

def write_to_new_file(extracted, output_filename):
    """
    Write the extracted code to a new LaTeX file with a basic preamble.

    :param extracted: A dictionary with extracted environments.
    :param output_filename: The name of the output file.
    """
    preamble = """
\\documentclass{article}
\\usepackage{amsmath}
\\usepackage{graphicx}
\\usepackage{booktabs}
\\usepackage{caption}
\\usepackage{subcaption}
\\begin{document}
"""
    postamble = "\n\\end{document}"

    with open(output_filename, 'w') as f:
        f.write(preamble)
        for env in extracted:
            f.write(f'\n% Extracted {env} environments\n')
            f.write('\n\n'.join(extracted[env]))
        f.write(postamble)

# Example usage
input_filename = '/path/to/your/inputfile.tex'
output_filename = '/path/to/your/outputfile.tex'

# Read the input LaTeX file
with open(input_filename, 'r') as f:
    latex_code = f.read()

# Extract equation, align, table, and figure environments
extracted = extract_environments(latex_code, ['equation', 'align', 'table', 'figure'])

# Write the extracted code to a new LaTeX file
write_to_new_file(extracted, output_filename)

```

7. If needed enhance figures using the code below.

9. Copy all the latex style files to a specific folder

```python
import os
import re
import shutil

def find_and_copy_latex_style_files(latex_file, output_folder):
    # Regular expression to find \usepackage{} commands in LaTeX
    usepackage_re = re.compile(r'\\usepackage\{([^\}]+)\}')
    
    # Open and read the LaTeX file
    with open(latex_file, 'r') as file:
        data = file.read()
    
    # Find all \usepackage{} commands
    packages = usepackage_re.findall(data)
    
    # Search paths for LaTeX style files
    search_paths = ['/usr/local/texlive/2022/texmf-dist/tex/latex/']
    
    # Find and copy the style files
    for package in packages:
        found = False
        for path in search_paths:
            for root, dirs, files in os.walk(path):
                if f'{package}.sty' in files:
                    shutil.copy(os.path.join(root, f'{package}.sty'), output_folder)
                    found = True
                    break
            if found:
                break
        if not found:
            print(f"Warning: Style file for package '{package}' not found.")
            
# Example usage:
# find_and_copy_latex_style_files('path/to/latex/file.tex', 'path/to/output/folder')

```



10. **Submit.**
## Modify Matlab fig files with python code. 

```python
material = {

    "red": {
        0: "#ffebee",
        1: "#ffcdd2",
        2: "#ef9a9a",
        3: "#e57373",
        4: "#ef5350",
        5: "#f44336",
        6: "#e53935",
        7: "#d32f2f",
        8: "#c62828",
        9: "#b71c1c",
    },

    "pink": {

        0: "#fce4ec",

        1: "#f8bbd0",

        2: "#f48fb1",

        3: "#f06292",

        4: "#ec407a",

        5: "#e91e63",

        6: "#d81b60",

        7: "#c2185b",

        8: "#ad1457",

        9: "#880e4f",

    },

    "purple": {

        0: "#f3e5f5",

        1: "#e1bee7",

        2: "#ce93d8",

        3: "#ba68c8",

        4: "#ab47bc",

        5: "#9c27b0",

        6: "#8e24aa",

        7: "#7b1fa2",

        8: "#6a1b9a",

        9: "#4a148c",

    },

    "deep purple": {

        0: "#ede7f6",

        1: "#d1c4e9",

        2: "#b39ddb",

        3: "#9575cd",

        4: "#7e57c2",

        5: "#673ab7",

        6: "#5e35b1",

        7: "#512da8",

        8: "#4527a0",

        9: "#311b92",

    },

    "indigo": {

        0: "#e8eaf6",

        1: "#c5cae9",

        2: "#9fa8da",

        3: "#7986cb",

        4: "#5c6bc0",

        5: "#3f51b5",

        6: "#3949ab",

        7: "#303f9f",

        8: "#283593",

        9: "#1a237e",

    },

    "blue": {

        0: "#e3f2fd",

        1: "#bbdefb",

        2: "#90caf9",

        3: "#64b5f6",

        4: "#42a5f5",

        5: "#2196f3",

        6: "#1e88e5",

        7: "#1976d2",

        8: "#1565c0",

        9: "#0d47a1",

    },

    "light blue": {

        0: "#e1f5fe",

        1: "#b3e5fc",

        2: "#81d4fa",

        3: "#4fc3f7",

        4: "#29b6f6",

        5: "#03a9f4",

        6: "#039be5",

        7: "#0288d1",

        8: "#0277bd",

        9: "#01579b",

    },

    "cyan": {

        0: "#e0f7fa",

        1: "#b2ebf2",

        2: "#80deea",

        3: "#4dd0e1",

        4: "#26c6da",

        5: "#00bcd4",

        6: "#00acc1",

        7: "#0097a7",

        8: "#00838f",

        9: "#006064",

    },

    "teal": {

        0: "#e0f2f1",

        1: "#b2dfdb",

        2: "#80cbc4",

        3: "#4db6ac",

        4: "#26a69a",

        5: "#009688",

        6: "#00897b",

        7: "#00796b",

        8: "#00695c",

        9: "#004d40",

    },

    "green": {

        0: "#e8f5e9",

        1: "#c8e6c9",

        2: "#a5d6a7",

        3: "#81c784",

        4: "#66bb6a",

        5: "#4caf50",

        6: "#43a047",

        7: "#388e3c",

        8: "#2e7d32",

        9: "#1b5e20",

    },

    "light green": {

        0: "#f1f8e9",

        1: "#dcedc8",

        2: "#c5e1a5",

        3: "#aed581",

        4: "#9ccc65",

        5: "#8bc34a",

        6: "#7cb342",

        7: "#689f38",

        8: "#558b2f",

        9: "#33691e",

    },

    "lime": {

        0: "#f9fbe7",

        1: "#f0f4c3",

        2: "#e6ee9c",

        3: "#dce775",

        4: "#d4e157",

        5: "#cddc39",

        6: "#c0ca33",

        7: "#afb42b",

        8: "#9e9d24",

        9: "#827717",

    },

    "yellow": {

        0: "#fffde7",

        1: "#fff9c4",

        2: "#fff59d",

        3: "#fff176",

        4: "#ffee58",

        5: "#ffeb3b",

        6: "#fdd835",

        7: "#fbc02d",

        8: "#f9a825",

        9: "#f57f17",

    },

    "amber": {

        0: "#fff8e1",

        1: "#ffecb3",

        2: "#ffe082",

        3: "#ffd54f",

        4: "#ffca28",

        5: "#ffc107",

        6: "#ffb300",

        7: "#ffa000",

        8: "#ff8f00",

        9: "#ff6f00",

    },

    "orange": {

        0: "#fff3e0",

        1: "#ffe0b2",

        2: "#ffcc80",

        3: "#ffb74d",

        4: "#ffa726",

        5: "#ff9800",

        6: "#fb8c00",

        7: "#f57c00",

        8: "#ef6c00",

        9: "#e65100",

    },

    "deep orange": {

        0: "#fbe9e7",

        1: "#ffccbc",

        2: "#ffab91",

        3: "#ff8a65",

        4: "#ff7043",

        5: "#ff5722",

        6: "#f4511e",

        7: "#e64a19",

        8: "#d84315",

        9: "#bf360c",

    },

    "brown": {

        0: "#efebe9",

        1: "#d7ccc8",

        2: "#bcaaa4",

        3: "#a1887f",

        4: "#8d6e63",

        5: "#795548",

        6: "#6d4c41",

        7: "#5d4037",

        8: "#4e342e",

        9: "#3e2723",

    },

    "grey": {

        0: "#fafafa",

        1: "#f5f5f5",

        2: "#eeeeee",

        3: "#e0e0e0",

        4: "#bdbdbd",

        5: "#9e9e9e",

        6: "#757575",

        7: "#616161",

        8: "#424242",

        9: "#212121",

    },

    "blue grey": {

        0: "#eceff1",

        1: "#cfd8dc",

        2: "#b0bec5",

        3: "#90a4ae",

        4: "#78909c",

        5: "#607d8b",

        6: "#546e7a",

        7: "#455a64",

        8: "#37474f",

        9: "#263238",

    },

}

  

matplotlib.rcParams['mathtext.fontset'] = 'stix'

matplotlib.rcParams['font.family'] = 'STIXGeneral'

# matplotlib.pyplot.title(r'$\mathrm{ABC123}^{123}$')

matplotlib.rcParams['text.usetex']=False

# matplotlib.rcParams['text.latex.unicode']=True

  
  

plt.rcParams["figure.edgecolor"] = "black"

plt.rcParams["figure.facecolor"] = "white"#material["grey"][2]

plt.rcParams["axes.facecolor"] = "white"#material["grey"][2]

plt.rcParams["axes.ymargin"] = 0.1

plt.rcParams["font.sans-serif"] = ["Fira Sans Condensed"]

  
  

plt.rcParams["axes.grid"] = False

plt.rcParams["grid.color"] = "black"

plt.rcParams["grid.linewidth"] = 0.1

  

plt.rcParams['font.size'] = 11

plt.rcParams['axes.linewidth'] = 0.5

plt.rcParams['lines.linewidth'] = 1.5

plt.rcParams['lines.markersize'] = 10

plt.rcParams['axes.spines.right'] = True

plt.rcParams['axes.spines.top'] = True

plt.rcParams['legend.frameon'] = True

plt.rcParams['legend.fontsize'] = 15

plt.rcParams['figure.dpi'] = 150

plt.rcParams['axes.labelsize']=14

plt.rcParams['legend.edgecolor']= '0.9'

  
  

plt.rcParams["lines.marker"] = "o"

plt.rcParams["lines.markeredgewidth"] = 1.5

plt.rcParams["lines.markeredgecolor"] = "auto"

plt.rcParams["lines.markerfacecolor"] = "white"#material["grey"][2]

plt.rcParams["lines.markersize"] = 6

  
  

plt.rcParams['xtick.alignment']='center'

plt.rcParams['xtick.color']= 'black'

plt.rcParams['xtick.direction']= 'out'

  
  

plt.rcParams['xtick.minor.top']= True

plt.rcParams['xtick.minor.bottom']= True

plt.rcParams['xtick.minor.visible']= True

plt.rcParams['xtick.minor.size']= 3.0

plt.rcParams['xtick.minor.top']= True

plt.rcParams['xtick.minor.width']= 0.6

  
  

plt.rcParams['xtick.major.bottom']= True

# plt.rcParams['xtick.major.pad']= 3.5

plt.rcParams['xtick.major.size']= 6.0

plt.rcParams['xtick.major.top']= True

plt.rcParams['xtick.major.width']= 0.8

# plt.rcParams['xtick.minor.pad']= 3.4

  
  

plt.rcParams['ytick.alignment']= 'center_baseline'

plt.rcParams['ytick.color']= 'black'

plt.rcParams['ytick.direction']= 'out'

# plt.rcParams['ytick.labelleft']= True

# plt.rcParams['ytick.labelright']= False

# plt.rcParams['ytick.labelsize']= 'medium'

  
  

plt.rcParams['ytick.major.left']= True

plt.rcParams['ytick.major.pad']= 3.5

plt.rcParams['ytick.major.right']= True

plt.rcParams['ytick.major.size']= 6.0

plt.rcParams['ytick.major.width']= 0.8

  
  

plt.rcParams['ytick.minor.left']= True

plt.rcParams['ytick.minor.pad']= 3.4

plt.rcParams['ytick.minor.right']= True

plt.rcParams['ytick.minor.size']= 3.0

plt.rcParams['ytick.minor.visible']= True

plt.rcParams['ytick.minor.width']= 0.6



#%%

# Load the data file
file_name = 'filename'  # Replace with your file name
data = loadmat(file_name+'.fig')

# Extract children and children's children data from the loaded data

# Explore the 'hgS_070000' key
hgS_contents = fig_contents['hgS_070000']

# Dive into the 'children' field
children_contents = hgS_contents['children'][0, 0]

# Explore the nested 'children' field
children_of_children = children_contents['children'][0, 0]

child_types = [child['type'][0] for child in children_of_children]

# Extract data and structure it with color
structured_data_with_color = []

for child in children_of_children:
    properties = child['properties'][0]
    if 'XData' in properties.dtype.names and 'YData' in properties.dtype.names:
        x_data = properties['XData'][0][0]
        y_data = properties['YData'][0][0]
        
        # Extracting color if available
        color = properties['Color'][0] if 'Color' in properties.dtype.names else None
        
        structured_data_with_color.append({
            "XData": x_data,
            "YData": y_data,
            "Color": color
        })



#%%


# Plotting the structured data
plt.figure(figsize=(5, 3), frameon=True)

ax = plt.subplot(1, 1, 1)

plt.autoscale(enable=True, tight=True)

# Loop through the structured data to plot
for i in range(len(structured_data_with_color)):
    data_point = structured_data_with_color[i]
    # If we choose to use sea-born package
    df = pd.DataFrame({'x': data_point["XData"].ravel(), 'y': data_point["YData"].ravel()})
    clr = tuple(data_point["Color"].ravel())    
    sns.scatterplot(data=df, x='x', y='y', color=clr, edgecolor=clr, s=0.1)

# Setting labels and limits for the plot
plt.xlabel('$F$')
plt.ylabel('$\\dot{w}|_{\\Sigma},x=1}$')
ax.set_xlim(12.45, 12.95)

# Setting the number of x and y ticks
ax.xaxis.set_major_locator(MaxNLocator(nbins=5))  # 4 ticks on x-axis
ax.yaxis.set_major_locator(MaxNLocator(nbins=4))  # 5 ticks on y-axis

# Adjusting plot layout and saving the plot
plt.tight_layout()
plt.savefig(file_name + ".pdf", format='pdf', dpi=600, bbox_inches='tight')

# Displaying the plot
plt.show()

```




## Other resources

[GitHub - gpoore/pythontex: A LaTeX package that executes Python and other code in LaTeX documents, and includes the output](https://github.com/gpoore/pythontex)
