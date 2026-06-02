import json
import html
import os
import re
import shlex
import shutil
import stat
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_WORKER_IMAGE = "am009/latexdiff-web-worker"
ONLINE_LATEXDIFF_URL = "https://3142.nl/latex-diff/"
WORKSPACE_MARKER = ".pub_assist_latexdiff_workspace"

DEFAULT_SUBMISSION_STYLE = {
    "new_text": {
        "color": [0, 0, 255],
        "style": "underline_wave",
    },
    "old_text": {
        "color": [255, 0, 0],
        "style": "strikeout",
    },
}


class LatexdiffWorkerError(RuntimeError):
    """Raised when the git-latexdiff-web Docker worker fails."""


class LocalLatexdiffError(RuntimeError):
    """Raised when local latexdiff or LaTeX compilation fails."""


class OnlineLatexdiffError(RuntimeError):
    """Raised when the online latexdiff form fails."""


def _as_path(path):
    return Path(path).expanduser().resolve()


def _zip_directory(source_dir, target_zip):
    source_dir = _as_path(source_dir)
    target_zip = _as_path(target_zip)

    with zipfile.ZipFile(target_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir).as_posix())


def _materialize_zip(source, target_zip):
    source_path = _as_path(source)
    target_zip = _as_path(target_zip)

    if not source_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {source_path}")

    if source_path.is_dir():
        _zip_directory(source_path, target_zip)
    elif source_path.is_file() and source_path.suffix.lower() == ".zip":
        shutil.copy2(source_path, target_zip)
    else:
        raise ValueError(
            "Input must be a LaTeX project folder or an Overleaf-style .zip file: "
            f"{source_path}"
        )


def _extract_zip(zip_path, destination):
    destination = _as_path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(_as_path(zip_path)) as archive:
        archive.extractall(destination)


def _copy_tree_contents(source, destination):
    source = _as_path(source)
    destination = _as_path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def _run_command(command, cwd, use_cmd=False):
    run_command = ["cmd", "/c"] + command if use_cmd else command
    result = subprocess.run(
        run_command,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )

    return {
        "command": format_command(run_command),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _compile_pdf_from_diff_tex(
    diff_tex,
    workspace,
    pdflatex_executable="pdflatex",
    use_cmd=False,
):
    diff_tex = _as_path(diff_tex)
    workspace = _as_path(workspace)
    main_file_name = diff_tex.name
    compile_dir = diff_tex.parent
    pdf_path = compile_dir / f"{diff_tex.stem}.pdf"
    commands = []

    for command in [
        [pdflatex_executable, "-interaction=nonstopmode", "-halt-on-error", main_file_name],
        [pdflatex_executable, "-interaction=nonstopmode", "-halt-on-error", main_file_name],
    ]:
        result = _run_command(command, cwd=compile_dir, use_cmd=use_cmd)
        commands.append(result)
        if result["returncode"] != 0:
            return {
                "returncode": result["returncode"],
                "commands": commands,
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "diff_pdf": str(workspace / "diff.pdf"),
                "diff_tex": str(diff_tex),
            }

    if pdf_path.exists():
        shutil.copy2(pdf_path, workspace / "diff.pdf")

    return {
        "returncode": 0 if (workspace / "diff.pdf").exists() else 1,
        "commands": commands,
        "stdout": "\n".join(command["stdout"] for command in commands if command["stdout"]),
        "stderr": "\n".join(command["stderr"] for command in commands if command["stderr"]),
        "diff_pdf": str(workspace / "diff.pdf"),
        "diff_tex": str(diff_tex),
    }


def _extract_online_diff_tex(response_text):
    textareas = re.findall(r"<textarea\b[^>]*>(.*?)</textarea>", response_text, flags=re.IGNORECASE | re.DOTALL)
    if len(textareas) < 3:
        raise OnlineLatexdiffError(
            "The online latexdiff response did not contain a diff textarea. "
            "The service may have changed, rejected the input, or failed to run latexdiff."
        )

    return html.unescape(textareas[-1]).replace("\r\n", "\n")


def _make_writable(path):
    try:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    except OSError:
        pass


def _make_tree_writable(path):
    path = Path(path)
    if not path.exists():
        return

    for root, dirs, files in os.walk(path):
        for name in files:
            _make_writable(Path(root) / name)
        for name in dirs:
            _make_writable(Path(root) / name)
    _make_writable(path)


def _rmtree_onexc(func, path, exc):
    _make_writable(path)
    func(path)


def _rmtree_onerror(func, path, exc_info):
    _make_writable(path)
    func(path)


def _rmtree_with_retries(path, attempts=5, delay_seconds=0.4):
    path = Path(path)
    last_error = None

    for attempt in range(attempts):
        try:
            _make_tree_writable(path)
            try:
                shutil.rmtree(path, onexc=_rmtree_onexc)
            except TypeError:
                shutil.rmtree(path, onerror=_rmtree_onerror)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            time.sleep(delay_seconds * (attempt + 1))

    if last_error:
        raise last_error


def _quarantine_workspace(workspace):
    workspace = Path(workspace)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    stale_workspace = workspace.with_name(
        f"{workspace.name}_stale_{timestamp}_{os.getpid()}"
    )
    workspace.rename(stale_workspace)
    return stale_workspace


def _reset_workspace(workspace):
    marker = workspace / WORKSPACE_MARKER

    if not marker.exists():
        raise FileExistsError(
            f"Refusing to overwrite {workspace} because it was not created by this helper. "
            f"Choose an empty/new workspace_dir or manually remove the directory."
        )

    try:
        _rmtree_with_retries(workspace)
    except OSError as exc:
        try:
            _quarantine_workspace(workspace)
        except OSError as quarantine_exc:
            raise PermissionError(
                f"Could not clear the previous latexdiff workspace: {workspace}\n\n"
                "Windows is denying access to one or more files, often because "
                "Docker, OneDrive, Explorer, or an antivirus scanner still has a "
                "handle open. Close viewers/terminals using this folder or choose "
                "a fresh workspace folder such as latexdiff_runs/current_2, then rerun."
            ) from quarantine_exc


def _zip_names(zip_path):
    with zipfile.ZipFile(_as_path(zip_path)) as archive:
        return [name for name in archive.namelist() if not name.endswith("/")]


def _read_zip_member_text(zip_path, member_name):
    normalized_member = str(member_name).replace("\\", "/")

    with zipfile.ZipFile(_as_path(zip_path)) as archive:
        names = archive.namelist()
        matches = [
            name for name in names
            if name.replace("\\", "/") == normalized_member
        ]
        if not matches:
            matches = [
                name for name in names
                if name.replace("\\", "/").endswith("/" + normalized_member)
            ]
        if not matches:
            return ""
        return archive.read(matches[0]).decode("utf-8", errors="replace")


def _normalize_bib_name(name):
    name = name.strip().strip("{}").replace("\\", "/").lstrip("./")
    if not name:
        return ""
    return name if name.lower().endswith(".bib") else f"{name}.bib"


def _declared_bib_files(tex_text):
    declared = []

    for match in re.finditer(r"\\bibliography\s*\{([^}]*)\}", tex_text):
        declared.extend(_normalize_bib_name(part) for part in match.group(1).split(","))

    for match in re.finditer(
        r"\\(?:addbibresource|addglobalbib|addsectionbib)(?:\[[^\]]*\])?\s*\{([^}]*)\}",
        tex_text,
    ):
        declared.append(_normalize_bib_name(match.group(1)))

    return sorted({name for name in declared if name})


def _zip_has_bib_file(zip_names, bib_name):
    normalized = bib_name.replace("\\", "/").lstrip("./")
    return any(
        name.replace("\\", "/") == normalized
        or name.replace("\\", "/").endswith("/" + normalized)
        for name in zip_names
    )


def _validate_bibliography_assets(old_zip, new_zip, main_tex, bib):
    mode = (bib or "").strip().lower() if isinstance(bib, str) else bib
    if mode not in {"bibtex", "biber"}:
        return

    old_names = _zip_names(old_zip)
    new_names = _zip_names(new_zip)
    old_tex = _read_zip_member_text(old_zip, main_tex)
    new_tex = _read_zip_member_text(new_zip, main_tex)
    expected_bibs = sorted(set(_declared_bib_files(old_tex) + _declared_bib_files(new_tex)))

    old_bibs = sorted(name for name in old_names if name.lower().endswith(".bib"))
    new_bibs = sorted(name for name in new_names if name.lower().endswith(".bib"))

    missing = []
    if expected_bibs:
        for bib_file in expected_bibs:
            if not _zip_has_bib_file(old_names, bib_file):
                missing.append(f"old.zip is missing {bib_file}")
            if not _zip_has_bib_file(new_names, bib_file):
                missing.append(f"new.zip is missing {bib_file}")
    else:
        if not old_bibs:
            missing.append("old.zip does not contain any .bib files")
        if not new_bibs:
            missing.append("new.zip does not contain any .bib files")

    if not missing:
        return

    raise ValueError(
        f"Bibliography mode is {mode!r}, but the required .bib files were not found. "
        "Docker/local latexdiff will run BibTeX/Biber in this mode, and it fails when "
        "the bibliography database is absent.\n\n"
        + "\n".join(f"- {item}" for item in missing)
        + "\n\nFix: either add the .bib file(s) to both old and new projects, "
        "or set bib=None / choose Bibliography mode 'none' if you are using generated "
        ".bbl files or do not need bibliography regeneration."
    )


def normalize_bib_mode(bib):
    if bib is None:
        return None
    if not isinstance(bib, str):
        raise ValueError("bib must be 'bibtex', 'biber', 'none', or None.")

    mode = bib.strip().lower()
    if mode in {"", "none", "null", "no", "false"}:
        return None
    if mode in {"bibtex", "biber"}:
        return mode

    raise ValueError("bib must be 'bibtex', 'biber', 'none', or None.")


def build_config(main_tex, bib=None, style=None, other_cmdlines=""):
    """
    Build the config.json consumed by am009/git-latexdiff-web's worker image.

    style can be a latexdiff style string such as "UNDERLINE", a custom style
    dictionary, or None for Pub Assist's submission-oriented default.
    """
    bib = normalize_bib_mode(bib)

    return {
        "other_cmdlines": other_cmdlines or "",
        "style": DEFAULT_SUBMISSION_STYLE if style is None else style,
        "main_tex": main_tex,
        "bib": bib,
    }


def prepare_latexdiff_workspace(
    old_project,
    new_project,
    main_tex,
    workspace_dir="latexdiff_runs/current",
    bib=None,
    style=None,
    other_cmdlines="",
    overwrite=True,
):
    """
    Create the old.zip, new.zip, and config.json layout expected by the worker.

    old_project and new_project can each be either a project folder or a .zip.
    """
    workspace = _as_path(workspace_dir)

    if workspace.exists():
        if not overwrite:
            raise FileExistsError(
                f"Workspace already exists: {workspace}. Set overwrite=True to replace it."
            )
        _reset_workspace(workspace)

    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / WORKSPACE_MARKER).write_text(
        "Generated by Pub Assist latexdiff_web.py.\n",
        encoding="utf-8",
    )

    old_zip = workspace / "old.zip"
    new_zip = workspace / "new.zip"
    config_path = workspace / "config.json"

    _materialize_zip(old_project, old_zip)
    _materialize_zip(new_project, new_zip)
    bib = normalize_bib_mode(bib)
    _validate_bibliography_assets(old_zip, new_zip, main_tex, bib)

    config = build_config(
        main_tex=main_tex,
        bib=bib,
        style=style,
        other_cmdlines=other_cmdlines,
    )
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    return {
        "workspace": str(workspace),
        "old_zip": str(old_zip),
        "new_zip": str(new_zip),
        "config_json": str(config_path),
        "config": config,
        "docker_command": docker_worker_command(workspace),
    }


def docker_worker_command(workspace_dir, image=DEFAULT_WORKER_IMAGE, debug=False):
    workspace = _as_path(workspace_dir)
    command = ["docker", "run", "--rm"]

    if debug:
        command.extend(["-e", "DEBUG=1"])

    command.extend(["-v", f"{workspace}:/work", image])
    return command


def format_command(command):
    command = [str(part) for part in command]

    if os.name == "nt":
        return subprocess.list2cmdline(command)

    return " ".join(shlex.quote(part) for part in command)


def _read_worker_main_tex(workspace):
    config_path = workspace / "config.json"
    if not config_path.exists():
        return None

    try:
        return json.loads(config_path.read_text(encoding="utf-8")).get("main_tex")
    except (OSError, json.JSONDecodeError):
        return None


def _worker_diff_tex_candidates(workspace, main_tex):
    if not main_tex:
        return []

    candidates = [workspace / "git-latexdiff" / "new" / main_tex]
    for folder in sorted(workspace.glob("git-latexdiff*")):
        if folder.is_dir():
            candidates.append(folder / "new" / main_tex)

    seen = set()
    unique_candidates = []
    for path in candidates:
        resolved = str(path)
        if resolved not in seen:
            unique_candidates.append(path)
            seen.add(resolved)
    return unique_candidates


def _first_existing(paths):
    for path in paths:
        if path and path.exists():
            return path
    return None


def _worker_pdf_candidate(workspace):
    diff_pdf = workspace / "diff.pdf"
    if diff_pdf.exists():
        return diff_pdf

    candidates = []
    for folder in sorted(workspace.glob("git-latexdiff*")):
        if not folder.is_dir():
            continue
        for pdf in sorted(folder.rglob("*.pdf")):
            try:
                rel_parts = pdf.relative_to(folder).parts
            except ValueError:
                rel_parts = ()
            # Avoid copying a project-supplied PDF from the extracted old/new trees.
            if rel_parts and rel_parts[0] in {"old", "new"}:
                continue
            candidates.append(pdf)

    return candidates[0] if candidates else None


def _collect_worker_artifacts(workspace, main_tex):
    candidates = [
        workspace / "diff.pdf",
        workspace / "diff.tex",
        workspace / "config.json",
        workspace / "old.zip",
        workspace / "new.zip",
        workspace / "git-latexdiff" / "old-main-fl.tex",
        workspace / "git-latexdiff" / "new-main-fl.tex",
    ]
    candidates.extend(_worker_diff_tex_candidates(workspace, main_tex))

    for folder in sorted(workspace.glob("git-latexdiff*")):
        if not folder.is_dir():
            continue
        candidates.extend(sorted(folder.rglob("*.pdf")))

    existing = []
    seen = set()
    for path in candidates:
        if not path.exists():
            continue
        try:
            display = str(path.relative_to(workspace))
        except ValueError:
            display = str(path)
        if display not in seen:
            existing.append(display)
            seen.add(display)

    return existing


def run_latexdiff_worker(
    workspace_dir,
    image=DEFAULT_WORKER_IMAGE,
    debug=False,
    pull_image=False,
    use_cmd=False,
    check=True,
):
    """
    Run the Docker worker and return stdout, stderr, and expected output paths.
    """
    workspace = _as_path(workspace_dir)
    main_tex = _read_worker_main_tex(workspace)

    if pull_image:
        pull_command = ["docker", "pull", image]
        subprocess.run(["cmd", "/c"] + pull_command if use_cmd else pull_command, check=True)

    command = docker_worker_command(workspace, image=image, debug=debug)
    run_command = ["cmd", "/c"] + command if use_cmd else command
    result = subprocess.run(
        run_command,
        cwd=str(workspace),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )

    root_diff_tex = workspace / "diff.tex"
    worker_diff_tex = _first_existing(_worker_diff_tex_candidates(workspace, main_tex))
    if worker_diff_tex and not root_diff_tex.exists():
        shutil.copy2(worker_diff_tex, root_diff_tex)

    diff_pdf = workspace / "diff.pdf"
    pdf_candidate = _worker_pdf_candidate(workspace)
    if pdf_candidate and pdf_candidate != diff_pdf and not diff_pdf.exists():
        shutil.copy2(pdf_candidate, diff_pdf)

    effective_returncode = result.returncode
    postprocess_error = ""
    if result.returncode == 0 and not diff_pdf.exists():
        effective_returncode = 1
        postprocess_error = (
            "Docker worker exited successfully, but Pub Assist could not find "
            f"{diff_pdf}. The worker should create diff.pdf at the mounted "
            "workspace root. Inspect artifact_files and Docker stdout/stderr."
        )

    stderr = result.stderr
    if postprocess_error:
        stderr = "\n".join(part for part in [stderr, postprocess_error] if part)

    output = {
        "command": format_command(run_command),
        "returncode": effective_returncode,
        "stdout": result.stdout,
        "stderr": stderr,
        "diff_pdf": str(diff_pdf),
        "diff_tex": str(root_diff_tex if root_diff_tex.exists() else (worker_diff_tex or root_diff_tex)),
        "diff_project": str(workspace / "git-latexdiff" / "new"),
        "artifact_files": _collect_worker_artifacts(workspace, main_tex),
        "docker_image": image,
        "docker_pull_command": format_command(["docker", "pull", image]),
    }

    if check and output["returncode"] != 0:
        raise LatexdiffWorkerError(
            "git-latexdiff-web worker failed with exit code "
            f"{output['returncode']}.\n\nCommand:\n{output['command']}\n\n"
            f"Expected outputs:\n{output['diff_pdf']}\n{output['diff_tex']}\n\n"
            f"Artifacts found:\n{json.dumps(output['artifact_files'], indent=2)}\n\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{stderr}"
        )

    return output


def run_local_latexdiff(
    workspace_dir,
    latexdiff_executable="latexdiff",
    pdflatex_executable="pdflatex",
    bibtex_executable="bibtex",
    biber_executable="biber",
    compile_pdf=True,
    use_cmd=False,
    check=True,
):
    """
    Run latexdiff locally using MiKTeX/TeX Live tools instead of Docker.

    The workspace must already contain old.zip, new.zip, and config.json from
    prepare_latexdiff_workspace().
    """
    workspace = _as_path(workspace_dir)
    config_path = workspace / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    main_tex = config["main_tex"]
    bib = config.get("bib")
    style = config.get("style")
    other_cmdlines = config.get("other_cmdlines") or ""

    local_dir = workspace / "local-latexdiff"
    if local_dir.exists():
        shutil.rmtree(local_dir)

    old_dir = local_dir / "old"
    new_dir = local_dir / "new"
    build_dir = local_dir / "build"

    _extract_zip(workspace / "old.zip", old_dir)
    _extract_zip(workspace / "new.zip", new_dir)

    # Compile against new files, but keep old-only assets available for deleted floats.
    _copy_tree_contents(old_dir, build_dir)
    _copy_tree_contents(new_dir, build_dir)

    old_tex = old_dir / main_tex
    new_tex = new_dir / main_tex
    diff_tex = build_dir / main_tex

    if not old_tex.exists():
        raise FileNotFoundError(f"Old project does not contain {main_tex}: {old_tex}")
    if not new_tex.exists():
        raise FileNotFoundError(f"New project does not contain {main_tex}: {new_tex}")

    latexdiff_command = [latexdiff_executable, "--flatten"]

    if style is None or isinstance(style, dict):
        latexdiff_command.append("--type=UNDERLINE")
    elif isinstance(style, str):
        latexdiff_command.append(f"--type={style}")

    if other_cmdlines:
        latexdiff_command.extend(shlex.split(other_cmdlines))

    latexdiff_command.extend([str(old_tex), str(new_tex)])

    run_latexdiff_command = ["cmd", "/c"] + latexdiff_command if use_cmd else latexdiff_command
    latexdiff_result = subprocess.run(
        run_latexdiff_command,
        cwd=str(workspace),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )

    if latexdiff_result.stdout:
        diff_tex.parent.mkdir(parents=True, exist_ok=True)
        diff_tex.write_text(latexdiff_result.stdout, encoding="utf-8")

    commands = [
        {
            "command": format_command(run_latexdiff_command),
            "returncode": latexdiff_result.returncode,
            "stdout": latexdiff_result.stdout,
            "stderr": latexdiff_result.stderr,
        }
    ]

    if latexdiff_result.returncode != 0:
        output = {
            "returncode": latexdiff_result.returncode,
            "commands": commands,
            "stdout": latexdiff_result.stdout,
            "stderr": latexdiff_result.stderr,
            "diff_pdf": str(workspace / "diff.pdf"),
            "diff_project": str(build_dir),
            "diff_tex": str(diff_tex),
        }

        if check:
            raise LocalLatexdiffError(
                "local latexdiff failed.\n\nCommand:\n"
                f"{commands[0]['command']}\n\nstderr:\n{latexdiff_result.stderr}"
            )

        return output

    pdf_path = build_dir / f"{Path(main_tex).stem}.pdf"

    if compile_pdf:
        main_file_name = Path(main_tex).name
        compile_dir = diff_tex.parent
        compile_sequence = [
            [pdflatex_executable, "-interaction=nonstopmode", "-halt-on-error", main_file_name],
        ]

        if bib == "bibtex":
            compile_sequence.append([bibtex_executable, Path(main_tex).stem])
        elif bib == "biber":
            compile_sequence.append([biber_executable, Path(main_tex).stem])

        compile_sequence.extend([
            [pdflatex_executable, "-interaction=nonstopmode", "-halt-on-error", main_file_name],
            [pdflatex_executable, "-interaction=nonstopmode", "-halt-on-error", main_file_name],
        ])

        for command in compile_sequence:
            result = _run_command(command, cwd=compile_dir, use_cmd=use_cmd)
            commands.append(result)

            if result["returncode"] != 0:
                output = {
                    "returncode": result["returncode"],
                    "commands": commands,
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                    "diff_pdf": str(workspace / "diff.pdf"),
                    "diff_project": str(build_dir),
                    "diff_tex": str(diff_tex),
                }

                if check:
                    raise LocalLatexdiffError(
                        "local LaTeX compilation failed.\n\nCommand:\n"
                        f"{result['command']}\n\nstdout:\n{result['stdout']}\n\nstderr:\n{result['stderr']}"
                    )

                return output

        if pdf_path.exists():
            shutil.copy2(pdf_path, workspace / "diff.pdf")

    output = {
        "returncode": 0 if (not compile_pdf or (workspace / "diff.pdf").exists()) else 1,
        "commands": commands,
        "stdout": "\n".join(command["stdout"] for command in commands if command["stdout"]),
        "stderr": "\n".join(command["stderr"] for command in commands if command["stderr"]),
        "diff_pdf": str(workspace / "diff.pdf"),
        "diff_project": str(build_dir),
        "diff_tex": str(diff_tex),
    }

    if check and output["returncode"] != 0:
        raise LocalLatexdiffError("local latexdiff finished without creating diff.pdf")

    return output


def run_online_latexdiff(
    workspace_dir,
    service_url=ONLINE_LATEXDIFF_URL,
    pdflatex_executable="pdflatex",
    compile_pdf=True,
    timeout=120,
    use_cmd=False,
    check=True,
):
    """
    Use the online form at https://3142.nl/latex-diff/ to generate diff .tex.

    This mode sends only the old and new main .tex file contents to the
    third-party website. It does not upload project zips, bibliography files,
    figures, or style files. The returned diff .tex is compiled locally.
    """
    workspace = _as_path(workspace_dir)
    config_path = workspace / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    main_tex = config["main_tex"]

    online_dir = workspace / "online-latexdiff"
    if online_dir.exists():
        shutil.rmtree(online_dir)

    old_dir = online_dir / "old"
    new_dir = online_dir / "new"
    build_dir = online_dir / "build"

    _extract_zip(workspace / "old.zip", old_dir)
    _extract_zip(workspace / "new.zip", new_dir)

    # Build against the new project files, with old-only assets copied first.
    _copy_tree_contents(old_dir, build_dir)
    _copy_tree_contents(new_dir, build_dir)

    old_tex = old_dir / main_tex
    new_tex = new_dir / main_tex
    diff_tex = build_dir / main_tex

    if not old_tex.exists():
        raise FileNotFoundError(f"Old project does not contain {main_tex}: {old_tex}")
    if not new_tex.exists():
        raise FileNotFoundError(f"New project does not contain {main_tex}: {new_tex}")

    old_text = old_tex.read_text(encoding="utf-8", errors="replace")
    new_text = new_tex.read_text(encoding="utf-8", errors="replace")

    data = urllib.parse.urlencode({"old": old_text, "new": new_text}).encode("utf-8")
    request = urllib.request.Request(
        service_url,
        data=data,
        headers={
            "User-Agent": "pub-assist-online-latexdiff/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    command_label = f"POST {service_url} with old/new main .tex fields"
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            response_text = response.read().decode(charset, errors="replace")
    except urllib.error.URLError as exc:
        output = {
            "returncode": 1,
            "commands": [{"command": command_label, "returncode": 1, "stdout": "", "stderr": str(exc)}],
            "stdout": "",
            "stderr": str(exc),
            "diff_pdf": str(workspace / "diff.pdf"),
            "diff_project": str(build_dir),
            "diff_tex": str(diff_tex),
        }
        if check:
            raise OnlineLatexdiffError(f"Online latexdiff request failed: {exc}") from exc
        return output

    try:
        diff_tex_text = _extract_online_diff_tex(response_text)
    except OnlineLatexdiffError as exc:
        output = {
            "returncode": 1,
            "commands": [{"command": command_label, "returncode": 1, "stdout": response_text, "stderr": str(exc)}],
            "stdout": response_text,
            "stderr": str(exc),
            "diff_pdf": str(workspace / "diff.pdf"),
            "diff_project": str(build_dir),
            "diff_tex": str(diff_tex),
        }
        if check:
            raise
        return output

    diff_tex.parent.mkdir(parents=True, exist_ok=True)
    diff_tex.write_text(diff_tex_text, encoding="utf-8")

    commands = [
        {
            "command": command_label,
            "returncode": 0,
            "stdout": f"Received {len(diff_tex_text)} characters of diff .tex from {service_url}",
            "stderr": "",
        }
    ]

    if compile_pdf:
        compile_result = _compile_pdf_from_diff_tex(
            diff_tex=diff_tex,
            workspace=workspace,
            pdflatex_executable=pdflatex_executable,
            use_cmd=use_cmd,
        )
        commands.extend(compile_result.get("commands", []))

        output = {
            "returncode": compile_result["returncode"],
            "commands": commands,
            "stdout": "\n".join([commands[0]["stdout"], compile_result.get("stdout", "")]).strip(),
            "stderr": compile_result.get("stderr", ""),
            "diff_pdf": str(workspace / "diff.pdf"),
            "diff_project": str(build_dir),
            "diff_tex": str(diff_tex),
        }
    else:
        output = {
            "returncode": 0,
            "commands": commands,
            "stdout": commands[0]["stdout"],
            "stderr": "",
            "diff_pdf": str(workspace / "diff.pdf"),
            "diff_project": str(build_dir),
            "diff_tex": str(diff_tex),
        }

    if check and output["returncode"] != 0:
        raise OnlineLatexdiffError(
            "online latexdiff generated a diff .tex, but local pdflatex failed.\n\n"
            f"stdout:\n{output['stdout']}\n\nstderr:\n{output['stderr']}"
        )

    return output
