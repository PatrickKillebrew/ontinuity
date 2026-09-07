# B1 iPad Keyboard Helper private-transfer receipt — 2026-09-06

This value-free receipt records the authorized mechanical separation of the
iPad Keyboard Helper from the public Ontinuity repository. The helper is a
separate project built using Ontinuity; it is not an Ontinuity component,
runtime route, authority role, seat type, or public artifact.

Patrick Killebrew explicitly confirmed this destination:

- repository: `PatrickKillebrew/ontinuity-intake-data` (private)
- branch: `main`
- project root: `projects/ipad-keyboard-helper/`

The transfer used MAIN's authenticated relay-courier and the private-repository
credential resolved from the Railway vault. No credential value appears in
this receipt. Before the first write, the authenticated repository lookup
returned HTTP 404 for the intended target path rather than an authentication
failure. No other private-project path was opened or inventoried.

Each file was committed separately, then read back from `main` through the
authenticated repository adapter. The returned bytes matched the local source
bytes exactly:

| Private path | Commit | SHA-256 | Result |
|---|---|---|---|
| `projects/ipad-keyboard-helper/README.md` | `7b216ebdcf1c6be4094326e0fa72c14afeaf879f` | `3274b5298f433c2a90d6930f1568b7de6ee7c1261466db7a398be179ec6bf6e1` | exact readback |
| `projects/ipad-keyboard-helper/helper.py` | `d0b1c6fe217be7197040c1de5c26c7c28c8b4041` | `225122da64d8926a83e8f0b2589e6dcfeb7e676a21699863d85c58b4bd82dfe8` | exact readback |
| `projects/ipad-keyboard-helper/CONTRACT.md` | `880f59e2e58dbf42bade7ccc6e08e5f0226bce0e` | `806c8058e4bf668939705bad8796e133cf08e665a7cd8b96ac0df0faa29db5c7` | exact readback |
| `projects/ipad-keyboard-helper/CORPUS.md` | `5882fece8addc8c64a88d687fde966f014af6424` | `caf9729ab0f151bd61bb1c130ede920f7db9eb46e45a4f569aa7b804bd64c556` | exact readback |
| `projects/ipad-keyboard-helper/template.html` | `166413e242ecb88aee3476598ddf10e6073d63bc` | `3a7795d297f910615ce9f8aca49c65e12ff0ead331df579918732d595cfd8640` | exact readback |

The helper, contract, and corpus hashes are the byte-preservation identities
bound before transfer. The template identity binds the intentionally
credential-blanked, fail-closed copy; the README was authored solely to state
the private-project boundary. After exact readback, the box transfer staging
file's current content was replaced with a value-free cleared marker.

This receipt proves private placement and public-project separation only. It
does not claim an Ontinuity commit, signoff, installation, deployment,
credential revocation, B1 acceptance, or live behavior.
