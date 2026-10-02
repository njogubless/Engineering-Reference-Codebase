# Build configuration

Values are compiled into the app with `--dart-define-from-file`:

```bash
flutter run -d chrome --dart-define-from-file=config/development.json
flutter run -d emulator-5554 --dart-define-from-file=config/development.android-emulator.json
```

| Key | Meaning |
|---|---|
| `API_BASE_URL` | Backend base URL. Django runs on `:8410`, FastAPI on `:8420`. The Android emulator reaches the host machine at `10.0.2.2`, not `localhost`. |
| `ENVIRONMENT` | `development` · `test` · `staging` · `production` |

Everything here ends up inside the app binary and can be extracted from it,
so these files must never contain secrets. Staging and production files are
created by CI from its own variables rather than committed.

Missing or invalid values stop the app at startup with a configuration
error screen (`AppConfig.parse`).
