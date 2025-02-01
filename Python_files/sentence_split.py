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
