# Friction Log

## Entry 1: Pasting code into the Lambda console editor
- Task: Update a Python Lambda function (ring_event_handler) with new code, working entirely from a mobile phone browser.
- Steps: Opened the function in the Lambda console, pasted the full Python file into the code editor, clicked Deploy, ran a test.
- Expected: The pasted code keeps its indentation and the function runs.
- Actual: The function failed with "unexpected indent"; the indentation of the pasted file was shifted.
- Severity: Medium (blocks deployment, but a workaround exists).
- Workaround: Created a .zip of the file and uploaded it via Code > Upload from > .zip file.
- Suggestion: Make zip/file upload more prominent for mobile users, or preserve indentation and warn when a paste changes it.

## Entry 2: Creating a CloudFront distribution
- Task: Host the static frontend (S3 + CloudFront) for the Fire TV web app.
- Steps: Created an S3 bucket with the HTML files, then tried to create a CloudFront distribution.
- Expected: The distribution is created.
- Actual: Creation failed with an "account must be verified" error, with no clear indication of how long verification takes or what to do next.
- Severity: Medium to high in a time-limited hackathon.
- Workaround: Hosted the frontend on GitHub Pages instead.
- Suggestion: Show verification status and expected wait time in the console, with a direct link to start verification, especially for new accounts.
