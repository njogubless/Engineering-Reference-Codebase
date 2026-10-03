# Firebase (emulators only)

The project id `demo-reference` starts with `demo-`, which the Firebase
Emulator Suite treats as an offline-only project: no real Firebase project,
no credentials, nothing leaves the machine.

```bash
cd firebase
firebase emulators:start            # Auth :9099, Firestore :8080
make check-firebase                 # (from the repo root) emulator-backed tests
```

| File | Purpose |
|---|---|
| `firebase.json` | emulator ports; rules and index files |
| `firestore.rules` | security rules: deny by default; Phase 4 completes and tests them |
| `firestore.indexes.json` | composite index the posts query needs in real Firestore (the emulator does not enforce indexes) |

Using a real project later means: create it, add the apps (FlutterFire
CLI generates `firebase_options.dart`), deploy rules and indexes, and give
the backends `FIREBASE_PROJECT_ID` plus service-account credentials through
the platform's secret store. Never commit service-account JSON.
