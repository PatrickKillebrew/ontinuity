# Ontinuity HTTPS request protocol v2

This is the provider-neutral narrow waist for model-seat access. It does not
disable or replace a model's other tools. It makes an already-settled Ontinuity
transition explicit, reproducible, and rejectable at the server boundary.

## Canonical client boundary

`live/tools/ontinuity_https.sh prepare` is local and performs no network access.
It accepts a logical engine (`main` or `farm`), operation, exact JSON body file,
and—except for public admission—a mode-600 credential file. It creates a private
curl-config receipt and frozen companion files. `check` verifies their hashes.

The only model-seat network transition is visibly:

```sh
curl --disable --config - < REQUEST.curl
```

`--disable` is deliberately the first curl argument, so curl cannot load a
user-level default configuration before the frozen standard-input config. No
caller may prepend environment assignments or add flags. The process still
inherits the host platform's admitted network environment, including its proxy,
DNS, and TLS trust configuration. That environment is the runtime trust boundary
which makes sandbox egress possible; it is not caller-selected protocol state.

`verify` reads the captured headers and body. It requires the returned request ID
to equal the prepared ID for admission and capability modes. Operator-root mode is
a recovery/service compatibility path and does not claim model-seat conformance.

## Compiled envelope

Every admission or capability request carries:

- `X-Ontinuity-Client-Version: 2`
- `X-Ontinuity-Request-ID: <32 lowercase hexadecimal characters>`
- `X-Ontinuity-Request-SHA256: <64 lowercase hexadecimal characters>`

The request ID is a fresh 128-bit random value for each `prepare`. The digest is
SHA-256 of this UTF-8 byte sequence, including its final newline:

```text
client_version=2
mode=<admission|capability>
operation=<operation>
request_id=<request-id>
body_sha256=<sha256 of exact HTTP body bytes>
credential_sha256=<sha256 of exact bearer token bytes, or ->
```

MAIN recomputes the digest from the received path, body, and bearer token. Missing,
malformed, or mismatched envelopes fail with HTTP 428 before any box relay. The
designed `__probe__` 403 also requires a valid envelope. This digest is a protocol-
conformance check, not cryptographic proof that a particular executable produced
the request; the capability remains the authorization control.

## Duplicate and ambiguous transitions

The four B1 operations that can claim or mutate mailbox state are
`mailbox_send`, `mailbox_fetch`, `mailbox_ack`, and `you_there`. Before relaying one,
MAIN atomically records its request ID and fingerprint in the private persistent
capability registry. A crash-releasing SQLite transaction lock serializes the
registry's complete load/prune/modify/replace cycle across engine processes; the
JSON registry remains the backward-compatible record. The lock database contains
no bearer token or signing secret and is mode 600.

- A new ID is relayed once.
- A completed duplicate with the same fingerprint returns the bounded saved
  response and `X-Ontinuity-Replayed: true`; it is not relayed again.
- An ID reused with different bytes fails with HTTP 409.
- A duplicate whose earlier relay is still in progress or has an unknown outcome
  fails with HTTP 409 and is not relayed again.
- Transition records are private, size/count bounded, and expire after 24 hours.
- The box response is consumed as a bounded byte stream before decoding. Mutable
  operation responses may not exceed the 64 KiB replay bound; all other courier
  responses have a separate 16 MiB ceiling. An oversized or interrupted mutable
  response leaves the transition `unknown`, so it cannot be relayed again.

An intentional repeat is a new `prepare`, which produces a new request ID. A host
denial explicitly reported before curl starts may retry the unchanged receipt. If
curl started and no HTTP result was captured, the caller stops; it does not create
a replacement request.

## Portability boundary

The protocol uses ordinary HTTPS, JSON, headers, SHA-256, and a curl config read
from standard input. Model lineage and hosting provider are not protocol fields.
`live/ONTINUITY_ENDPOINTS.conf` maps logical engines to current HTTPS endpoints;
changing hosting changes that reviewed registry, not the boot state machine.

This boundary enforces the request and authorization protocol, not executable
attestation. A platform that must make every alternate HTTP executable powerless
must keep the bearer outside the model and expose this same intent contract through
a trusted transport executor. That is an authority-placement layer, not a reason
to add another client path to this protocol.
