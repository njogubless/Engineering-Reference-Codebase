"""Settings entry point for pytest and mypy.

Not a second configuration: it only selects the committed `.env.test` file
(unless the environment already says otherwise, as CI may) and then loads
the one real settings module.
"""

import os
from pathlib import Path

os.environ.setdefault("DJANGO_ENV_FILE", str(Path(__file__).resolve().parent.parent / ".env.test"))

from config.settings import *  # noqa: F403

# Speed only: Argon2 is deliberately slow (~50 ms per hash). Never use this outside tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
