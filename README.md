# PI-Studio

> A calm, private workspace for everyday PDF and image work.

PI-Studio keeps file tasks focused and understandable. Choose a tool, preview the result,
make the change, and save the output without sending documents to a website or
learning a complicated editor.

> **Closed-source product:** This repository contains the public product
> documentation only. The application source code is not distributed here.

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

## Download the app

Download the packaged desktop application for your operating system. No Python
installation, account, subscription, or cloud connection is required.

Once a GitHub release has been created, users can download the correct package
directly:

- **macOS:** [Download PI-Studio for macOS](https://github.com/Aditya-602/PI-Studio/releases/latest/download/PI-Studio-macOS.zip)
- **Windows:** [Download PI-Studio for Windows](https://github.com/Aditya-602/PI-Studio/releases/latest/download/PI-Studio-Windows.zip)

The downloadable packages are built and tested by the PI-Studio maintainers.
The source repository is intentionally private and is not included in the
public GitHub repository.

### macOS

The macOS package is distributed as a zip containing the PI-Studio app. On the
first launch, macOS may ask you to confirm that you want to open an app
downloaded from the internet. For the safest experience, download only from
the official release link above.

### Windows

Extract the complete downloaded PI-Studio folder before launching
`PI-Studio.exe`. Do not move only the executable out of the folder because the
other packaged files are required.

## Privacy and security

PI-Studio processes files locally and does not require an account or upload
documents to a cloud service. Keep the application updated and download
installers only from the official PI-Studio GitHub releases.

## Technical details

PI-Studio is a closed-source desktop application for macOS and Windows. The
public repository intentionally contains this README only; implementation
details, build configuration, and automated tests are maintained privately.
