#!/usr/bin/env python3
import argparse
import base64
import logging
import os
import shutil
import subprocess
import sys
import tempfile

import markdown

CHROME_GUESSES_LINUX = [
    "/usr/bin/google-chrome",
    "/usr/bin/chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]

def guess_chrome_path() -> str:
    """
    Guess the path of Chrome/Chromium on Linux (Ubuntu).
    """
    guesses = CHROME_GUESSES_LINUX
    for guess in guesses:
        if os.path.exists(guess):
            logging.info("Found Chrome or Chromium at " + guess)
            return guess
    raise ValueError("Could not find Chrome. Please set CHROME_PATH.")


def title(md: str) -> str:
    """
    Return the contents of the first markdown heading in md, which we
    assume to be the title of the document.
    """
    for line in md.splitlines():
        if line.startswith("# "):  # starts with exactly one '#'
            return line.lstrip("#").strip()
    raise ValueError(
        "Cannot find any lines that look like markdown h1 headings to use as the title"
    )


def make_html(md: str) -> str:
    """
    Compile md to HTML with necessary preamble and postamble.
    """
    return "".join(
        (
            "<html lang='ko'>",  # Set language to Korean
            "<head>",
            "<meta charset='UTF-8'>",
            "<style>",
            "body { font-family: 'Malgun Gothic', 'Nanum Gothic', sans-serif; }",  # Korean font support
            "</style>",
            "</head>",
            "<body>",
            markdown.markdown(md, extensions=["smarty", "abbr"]),
            "</body>",
            "</html>",
        )
    )


def write_pdf(html: str, prefix: str = "resume", chrome: str = "") -> None:
    """
    Write HTML to PDF.
    """
    chrome = chrome or guess_chrome_path()
    html64 = base64.b64encode(html.encode("utf-8"))
    options = [
        "--no-sandbox",
        "--headless",
        "--print-to-pdf-no-header",
        "--no-pdf-header-footer",
        "--disable-gpu",
        "--crash-dumps-dir=/tmp",
        "--user-data-dir=/tmp",
    ]
    tmpdir = tempfile.mkdtemp(prefix="resume.md_")
    options.append(f"--crash-dumps-dir={tmpdir}")
    options.append(f"--user-data-dir={tmpdir}")

    try:
        subprocess.run(
            [
                chrome,
                *options,
                f"--print-to-pdf={prefix}.pdf",
                "data:text/html;base64," + html64.decode("utf-8"),
            ],
            check=True,
        )
        logging.info(f"Wrote {prefix}.pdf")
    except subprocess.CalledProcessError as exc:
        raise exc
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file",
        help="markdown input file [resume.md]",
        default="resume.md",
        nargs="?",
    )
    parser.add_argument(
        "--no-pdf",
        help="Do not write pdf output",
        action="store_true",
    )
    parser.add_argument(
        "--chrome-path",
        help="Path to Chrome or Chromium executable",
    )
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.quiet:
        logging.basicConfig(level=logging.WARN, format="%(message)s")
    elif args.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    prefix, _ = os.path.splitext(os.path.abspath(args.file))

    with open(args.file, encoding="utf-8") as mdfp:
        md = mdfp.read()
    html = make_html(md)

    if not args.no_pdf:
        write_pdf(html, prefix=prefix, chrome=args.chrome_path)
