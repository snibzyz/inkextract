INKEXTRACT - Translation Toolkit (Windows portable bundle)
============================================================

How to use
----------
1. Double-click "Start.bat".
2. The app opens in your default browser.
3. To quit: close the black command window or press Ctrl+C.

That's it. No install required, no Python download, no venv setup.
Everything is already inside this folder.


Where do I put my files?
------------------------
Use the "workspace" folder next to Start.bat:

    workspace/
      0-input/    <- put source .txt / .docx files here
      1-fix/      <- intermediate
      2-clean/    <- cleaned outputs
      3-merge/    <- merged outputs
      4-separate/ <- split outputs
      output/     <- final results
      vocab/      <- vocab/glossary files


Updates
-------
The app checks GitHub for new versions on each launch. If an update
is found you'll see a banner at the top of the page; click "Update now"
and the new version will be applied the next time you run Start.bat.

Or download the latest release manually:
    https://github.com/snibzyz/inkextract/releases/latest


Troubleshooting
---------------
- "Windows protected your PC" / SmartScreen warning: click "More info"
  then "Run anyway" (this happens for any unsigned app).
- Browser doesn't open automatically: copy the URL printed in the
  black console window (e.g. http://localhost:8501) into your browser.
- App won't start: try deleting the ".venv" or "__pycache__" folders
  inside this directory and run Start.bat again.
