# Security policy

## Reporting a problem

Please report a security problem privately, not in a public issue. Use GitHub's private
reporting: open the repository's **Security** tab and choose **Report a vulnerability**.

Include the edition and version, what an attacker could do, and the steps to reproduce it. You
will get a reply when the report has been read.

## What counts

Examples:

- The skill or the hook installs, downloads, enables or connects something without the user's
  approval.
- The hook or `scout-probe` stores message text, file contents or credentials, or writes outside
  the folders listed in [docs/INSTALL.md](docs/INSTALL.md).
- The hook's state files can be read or changed by another user on the same machine.

## Supported versions

Only the latest version gets fixes.
