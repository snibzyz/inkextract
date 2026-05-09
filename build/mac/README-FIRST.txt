INKEXTRACT - Translation Toolkit (macOS portable bundle)
============================================================

How to use
----------
1. Double-click "Start.command".

   First time only: macOS may show a security warning ("can't verify
   the developer"). To bypass:
       - Right-click "Start.command" -> Open
       - Click "Open" in the dialog
   You only need to do this once. Subsequent launches just double-click.

2. The app opens in your default browser.
3. To quit: close the Terminal window or press Ctrl+C.

That's it. No install required, no Python download, no venv setup.
Everything is already inside this folder.


If macOS still blocks the app
-----------------------------
Open Terminal, drag this folder onto the Terminal window to get its
path, then run:

    xattr -cr "<paste folder path>"

This clears the quarantine flag macOS sets on downloaded files.


Where do I put my files?
------------------------
Use the "workspace" folder next to Start.command:

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
and the new version will be applied the next time you run Start.command.

Or download the latest release manually:
    https://github.com/snibzyz/inkextract/releases/latest


Troubleshooting
---------------
- "App is damaged and can't be opened" -> run the xattr command above.
- Browser doesn't open: copy the URL printed in the Terminal
  (e.g. http://localhost:8501) into your browser manually.
