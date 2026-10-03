# Flutter reference app

Flutter 3.41 + Riverpod 3 + Dio. A patterns demo app: each screen demonstrates one engineering pattern.

```bash
make -C ../.. setup-flutter
make -C ../.. run-flutter       # Chrome on :5420 → Django on :8410
flutter run -d emulator-5554 --dart-define-from-file=config/development.android-emulator.json
make -C ../.. check-flutter     # format, analyze, test, web build
```

| Path | What it demonstrates |
|---|---|
| `lib/main.dart` | global error capture, fail-fast config, provider overrides, Riverpod retry off |
| `lib/core/config/` | validated `--dart-define` configuration ([config/README.md](config/README.md)) |
| `lib/core/errors/` | sealed `AppError` hierarchy, exhaustive `userMessage` |
| `lib/core/networking/` | Dio client: request ID, logging, idempotent-only retry with jitter, error mapping |
| `lib/features/auth/` | session `Notifier`, auth interceptor, sign-in screen |
| `lib/features/posts/` | repository interface with REST and Firestore implementations, `AsyncNotifier` infinite list, optimistic publish |
| `lib/features/diagnostics/` | Phase 1 demo: data → application (FutureProvider.autoDispose + cancel on dispose) → presentation |

Layout: feature-first with layers inside each feature ([ADR 0004](../../docs/adr/0004-feature-first-flutter-layout.md)).
Firebase arrives in Phases 2–3.
