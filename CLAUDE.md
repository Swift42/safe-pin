## Supply chain safety — ALWAYS ENFORCE

When installing, adding, or updating dependencies with pip, npm, or composer:
- ALWAYS use the corresponding skill (`/pip`, `/npm`, `/composer`) to pin versions securely.
- NEVER run `pip install`, `npm install`, `composer require`, or equivalent with unpinned versions.
- Every dependency must be pinned to an exact version that is at least 7 days old, with hash verification.
- If you are about to install a package without using the skill, stop and use the skill first.
