# P — Offline PDF Studio

> A calm, private workspace for everyday PDF and image work.

P keeps file tasks focused and understandable. Choose a tool, preview the result,
make the change, and save the output without sending documents to a website or
learning a complicated editor.

![P — Offline PDF Studio home screen](https://raw.githubusercontent.com/Aditya-602/PI-Studio/main/docs/images/home.png)

## Why people use it

### Your files stay on your device

Everything is processed locally. Sensitive documents, personal photos, and
business files do not need to leave your computer or pass through a third-party
upload service.

### The right tool is easy to find

The Home screen keeps PDF and image workflows in one place. Search by name or
switch between the PDF and Image filters to get to the right action quickly.

### Preview before you commit

PDF pages appear as visual thumbnails wherever page selection matters. You can
inspect pages, open an individual page in the in-app fullscreen viewer, and
make decisions before creating an output file.

### Work with pages visually

Extract or remove pages by clicking the pages you want. Use **Ctrl-click** on
Windows/Linux or **Cmd-click** on macOS to select multiple pages. Reorder a PDF
by dragging its page cards into a new sequence.

### Keep working while jobs run

Long operations run in the background. You can return to Home, open another
tool, and use the Jobs control to see progress or cancel an active operation.

## What you can do

### PDF workflows

| Need | Tools |
| --- | --- |
| Organise documents | Merge PDF, Split PDF, Extract Pages |
| Edit page structure | Remove Pages, Reorder PDF, Rotate PDF |
| Prepare documents | Compress PDF, Protect PDF, Add Page Numbers |
| Check interactive documents | Inspect Form Fields |

### Image workflows

| Need | Tools |
| --- | --- |
| Convert | Images to PDF, PDF to Images |
| Improve files | Compress Image, Resize Image |
| Transform | Rotate & Flip, Remove Background, Crop to Content |
| File compatibility | JPEG, PNG, WebP, HEIC/HEIF, and other formats supported by the installed image codecs |

## Designed for clarity

- **Minimal workspace:** generous spacing, clear hierarchy, and no unnecessary
  side panels.
- **Visual page selection:** see the pages you are acting on instead of typing
  page numbers from memory.
- **Flexible layout:** resize the controls and preview areas with the divider.
- **Safe outputs:** invalid, unreadable, or oversized inputs are rejected before
  an output is created.
- **Keyboard-friendly:** key controls expose accessible names and can be used
  without relying only on a mouse.

## See it in action

### Home

Find the right workflow with search and compact PDF/Image filters.

![Home screen with PDF and Image filters](https://raw.githubusercontent.com/Aditya-602/PI-Studio/main/docs/images/home.png)

### Extract Pages

Preview page thumbnails, select the pages you need, and open any page fullscreen
without leaving the workspace.

![Extract Pages tool screen](https://raw.githubusercontent.com/Aditya-602/PI-Studio/main/docs/images/extract-pages.png)

## Getting started

### Requirements

- Python 3.11 or newer
- A desktop environment supported by PySide6

### Install and launch

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The application opens directly to the local Home workspace. No account,
subscription, or cloud connection is required.

## Use it on another computer

There are two ways to share the app.

### Option 1: Share a packaged desktop app

Once a GitHub release has been created, users can download the correct package
directly:

- **macOS:** [Download for macOS](https://github.com/Aditya-602/PI-Studio/releases/latest/download/PDFToolkit-macOS.zip)
- **Windows:** [Download for Windows](https://github.com/Aditya-602/PI-Studio/releases/latest/download/PDFToolkit-Windows.zip)

These files are generated automatically by the
[`Build desktop apps`](.github/workflows/build-release.yml) workflow whenever
you push a version tag such as `v1.0.0`.

This is the easiest option for someone who should not need Python installed.
Build the package on the same operating system as the computer that will run it:

| Destination | Build on | Result |
| --- | --- | --- |
| Mac | macOS | `dist/PDFToolkit.app` |
| Windows | Windows | `dist/PDFToolkit/` containing `PDFToolkit.exe` |

PyInstaller bundles Python and the application dependencies into the package.
The recipient does **not** need to install Python, PySide6, PyMuPDF, Pillow, or
the HEIC codec separately.

#### Build for macOS

On the Mac used for building:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python build_app.py
```

Send `dist/PDFToolkit.app` to another Mac. A zip file is convenient:

```bash
ditto -c -k --sequesterRsrc --keepParent dist/PDFToolkit.app PDFToolkit-macOS.zip
```

The build must match the recipient’s Mac architecture. Build on an Apple
silicon Mac for Apple silicon Macs, or build on an Intel Mac for Intel Macs.
For one package that supports both, create a universal Python environment and
build with universal-compatible dependencies, then test the result on both
architectures.

An unsigned app may trigger a macOS security warning the first time it opens.
For a public or business distribution, sign and notarize the app with an Apple
Developer account before sharing it.

#### Build for Windows

On the Windows PC used for building, open PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python build_app.py
```

Zip the complete `dist\PDFToolkit\` folder and send it to the other Windows
computer. The recipient should extract the entire folder and start:

```text
PDFToolkit\PDFToolkit.exe
```

Do not send only the `.exe`; the other files in the packaged folder are part of
the application. Windows may show a SmartScreen warning for an unsigned
program. Code-signing the executable is recommended for regular distribution.

### Option 2: Share the source project

Use this when the recipient is a developer who wants to run or modify the
project. They need Python 3.11 or newer and can follow the installation steps
above. On Windows, use `.venv\Scripts\Activate.ps1`; on macOS/Linux, use
`. .venv/bin/activate`.

### Important packaging notes

- Build macOS packages on macOS and Windows packages on Windows.
- Build separately for Apple silicon and Intel Macs when distributing to both.
- Test the packaged app on a clean computer before sharing it widely.
- Keep the complete packaged directory together.
- User files are processed locally; packaging does not add a cloud service or
  account requirement.

## Quality and confidence

The project includes automated checks for PDF and image processing, output
handling, cancellation, background jobs, and validation. Run the main regression
suite with:

```bash
python -m pytest -q
```

## Technical details

This is a local desktop application built with Python, PySide6, PyMuPDF, Pillow,
and `pillow-heif`. PDF and image processing lives in `pdf_toolkit/engine/`;
desktop screens and previews live in `pdf_toolkit/ui/`; background execution is
managed by `pdf_toolkit/workers/`.

The application validates inputs before work begins. Default safeguards include
a 512 MB per-file input limit, a 5,000-page PDF limit, a 100-megapixel image
limit, and an output free-space reserve. HEIC/HEIF support is provided through
the Pillow HEIF codec.

For maintainers, the complete local quality gate is:

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pyright
QT_QPA_PLATFORM=offscreen python -m pytest -q
python -m compileall -q pdf_toolkit main.py tests
```

The packaged desktop build can be created with:

```bash
python build_app.py
```
