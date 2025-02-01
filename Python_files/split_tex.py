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
