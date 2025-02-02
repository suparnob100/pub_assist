import os
import re

class LatexBeautifier:
    def __init__(self, indent_size=4, comment_column=80):
        """
        Initialize the LaTeX beautifier with customizable indentation size and comment column.
        :param indent_size: Number of spaces for each indentation level.
        :param comment_column: Column position for aligning comments.
        """
        self.indent_size = indent_size
        self.comment_column = comment_column
        self.indent_level = 0
        self.comment_pattern = re.compile(r'(?<!\\)%.*$')  # Matches LaTeX comments
        self.begin_pattern = re.compile(r'\\begin\{([a-zA-Z]+)\}')
        self.end_pattern = re.compile(r'\\end\{([a-zA-Z]+)\}')
        self.equation_envs = {'align', 'equation', 'gather', 'multline'}
        self.float_envs = {'figure', 'table'}
        self.float_header = "%%%%%%%%%%%%\n%%% float %%\n%%%%%%%%%%%%"

    def beautify(self, latex_code):
        """
        Beautifies the given LaTeX code by formatting indentation and aligning comments.
        :param latex_code: Raw LaTeX code as a string.
        :return: Beautified LaTeX code as a string.
        """
        lines = latex_code.splitlines()
        beautified_lines = []
        float_header_added = False

        for line in lines:
            stripped_line = line.rstrip()
            if not stripped_line:  # Skip empty lines
                beautified_lines.append("")
                continue

            # Handle comments
            comment_match = self.comment_pattern.search(stripped_line)
            comment = ""
            if comment_match:
                comment = comment_match.group(0).strip()  # Preserve the comment
                stripped_line = stripped_line[:comment_match.start()].rstrip()

            # Update indentation level based on LaTeX commands
            begin_match = self.begin_pattern.match(stripped_line)
            end_match = self.end_pattern.match(stripped_line)

            if begin_match:
                env_name = begin_match.group(1)
                if env_name in self.float_envs and not float_header_added:
                    beautified_lines.extend(self._add_float_header())
                    float_header_added = True

                if env_name in self.equation_envs:
                    beautified_lines.append(self._indent() + stripped_line + comment)
                else:
                    beautified_lines.append(self._indent() + stripped_line)
                    self.indent_level += 1
            elif end_match:
                env_name = end_match.group(1)
                if env_name in self.float_envs:
                    float_header_added = False

                if env_name in self.equation_envs:
                    beautified_lines.append(self._indent() + stripped_line + comment)
                else:
                    self.indent_level -= 1
                    beautified_lines.append(self._indent() + stripped_line)
            else:
                beautified_lines.append(self._indent() + stripped_line)

            # Align comments if present
            if comment:
                last_line = beautified_lines[-1]
                comment_position = max(len(last_line), self.comment_column)
                padding = ' ' * (comment_position - len(last_line))
                beautified_lines[-1] = last_line + padding + comment

        return "\n".join(beautified_lines)

    def _indent(self):
        """
        Returns the current indentation string based on the indentation level.
        """
        return " " * (self.indent_size * self.indent_level)

    def _add_float_header(self):
        """
        Adds the float header with proper indentation.
        """
        header_lines = self.float_header.splitlines()
        return [self._indent() + line for line in header_lines]

def process_all_tex_files(root_dir, file, output_dir,comment_column=80,indent_size=4):
    """
    Processes all .tex files in the root directory and writes beautified versions to the output directory.
    :param root_dir: Directory containing the .tex files.
    :param output_dir: Directory to write the beautified .tex files.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # for root, _, files in os.walk(root_dir):
    #     for file in files:
    #         if file.endswith('.tex'):
    input_filepath = os.path.join(root_dir, file)
    output_filepath = os.path.join(output_dir, file[:-4]+'_beautiful.tex')

    with open(input_filepath, 'r', encoding='utf-8') as infile:
        latex_content = infile.read()

    beautifier = LatexBeautifier(indent_size=indent_size, comment_column=comment_column)
    beautified_latex = beautifier.beautify(latex_content)

    with open(output_filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(beautified_latex)

    print(f"Processed and wrote beautified file: {output_filepath}")