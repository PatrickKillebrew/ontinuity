#!/bin/sh
set -eu

# Provider-neutral compiler for the Ontinuity HTTPS narrow waist.
#
# PREPARE is local. It freezes the complete request into a private curl-config
# receipt and companion bundle. CHECK is local. The only network transition is
# deliberately the top-level host-visible command. --disable must be first so a
# user-level curl configuration cannot modify the frozen request:
#
#     curl --disable --config - < REQUEST.curl
#
# VERIFY is local and interprets the captured response. A host denial explicitly
# reported before curl starts permits the identical command to be retried. Once
# curl has started, a missing response is UNKNOWN and must fail-stop because the
# request may have reached the server.

CLIENT_VERSION=2
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
ENDPOINTS_FILE="$SCRIPT_DIR/../ONTINUITY_ENDPOINTS.conf"

die() {
    printf 'ontinuity_https: %s\n' "$*" >&2
    exit 64
}

usage() {
    cat >&2 <<'EOF'
usage:
  ontinuity_https.sh prepare admission main admission_request BODY.json - REQUEST.curl
  ontinuity_https.sh prepare capability ENGINE OP BODY.json CAPABILITY_FILE REQUEST.curl
  ontinuity_https.sh prepare operator ENGINE OP BODY.json DIAG_KEY_FILE REQUEST.curl
  ontinuity_https.sh check REQUEST.curl
  ontinuity_https.sh verify REQUEST.curl

After CHECK, send with this exact top-level command:
  curl --disable --config - < REQUEST.curl

ENGINE is exactly main or farm. Admission is MAIN-only. REQUEST.curl and its
companion bundle must not already exist. Credential files must have mode 600.
EOF
    exit 64
}

safe_path() {
    case "$1" in
        ''|*[!A-Za-z0-9_./-]*) return 1 ;;
        *) return 0 ;;
    esac
}

file_mode() {
    stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1"
}

file_hash() {
    sha256sum "$1" | awk '{print $1}'
}

validate_engine() {
    case "$1" in
        main|farm) return 0 ;;
        *) die "engine must be exactly main or farm" ;;
    esac
}

validate_operation() {
    case "$1" in
        ''|*[!a-z0-9_]*) die "operation must be a lowercase Ontinuity name" ;;
    esac
}

engine_endpoint() {
    engine_name=$1
    [ -f "$ENDPOINTS_FILE" ] || die "reviewed endpoint registry is absent"
    endpoint=$(sed -n "s/^${engine_name}=//p" "$ENDPOINTS_FILE")
    [ -n "$endpoint" ] || die "endpoint registry lacks $engine_name"
    [ "$(printf '%s\n' "$endpoint" | wc -l | tr -d ' ')" -eq 1 ] || \
        die "endpoint registry repeats $engine_name"
    case "$endpoint" in
        https://*/*|*'?'*|*'#'*|*/)
            die "endpoint registry has an unsafe $engine_name URL"
            ;;
        https://*) printf '%s' "$endpoint" ;;
        *) die "endpoint registry requires HTTPS" ;;
    esac
}

meta_field() {
    key=$1
    file=$2
    value=$(sed -n "s/^${key}=//p" "$file")
    [ -n "$value" ] || die "request metadata lacks $key"
    [ "$(printf '%s\n' "$value" | wc -l | tr -d ' ')" -eq 1 ] || \
        die "request metadata repeats $key"
    printf '%s' "$value"
}

prepare() {
    [ "$#" -eq 6 ] || usage
    mode=$1
    engine_name=$2
    operation=$3
    source_body=$4
    source_credential=$5
    request_file=$6

    case "$mode" in
        admission|capability|operator) ;;
        *) die "mode must be admission, capability, or operator" ;;
    esac
    validate_engine "$engine_name"
    validate_operation "$operation"
    case "$request_file" in
        *.curl) ;;
        *) die "request receipt must end in .curl" ;;
    esac

    if [ "$mode" = admission ]; then
        [ "$engine_name" = main ] || die "admission is MAIN-only"
        [ "$operation" = admission_request ] || \
            die "admission operation must be admission_request"
        [ "$source_credential" = - ] || die "admission takes no credential"
        credential_sha256=-
        credential=
    else
        [ -f "$source_credential" ] && [ -r "$source_credential" ] || \
            die "credential file is not readable"
        [ "$(file_mode "$source_credential")" = 600 ] || \
            die "credential file must have mode 600"
        safe_path "$source_credential" || die "credential-file path is unsafe"
        credential_lines=$(awk 'END { print NR }' "$source_credential")
        [ "$credential_lines" -eq 1 ] || die "credential file must contain one line"
        if LC_ALL=C grep -q '[[:cntrl:]]' "$source_credential"; then
            die "credential contains a control character"
        fi
        IFS= read -r credential < "$source_credential" || true
        [ -n "${credential:-}" ] || die "credential file is empty"
        case "$credential" in
            *[!A-Za-z0-9._~+/-]*) die "credential contains an unsafe byte" ;;
        esac
        credential_sha256=$(printf '%s' "$credential" | sha256sum | awk '{print $1}')
    fi

    [ -f "$source_body" ] && [ -r "$source_body" ] || \
        die "JSON body file is not readable"
    safe_path "$source_body" || die "body-file path is unsafe"
    body_bytes=$(wc -c < "$source_body" | tr -d ' ')
    body_limit=2097152
    [ "$mode" = admission ] && body_limit=16384
    [ "$mode" = capability ] && body_limit=65536
    [ "$body_bytes" -le "$body_limit" ] || \
        die "JSON body exceeds the $mode request bound"
    body_sha256=$(file_hash "$source_body")

    safe_path "$request_file" || die "request-receipt path is unsafe"
    [ ! -e "$request_file" ] || die "request receipt already exists"
    bundle="${request_file}.d"
    [ ! -e "$bundle" ] || die "request bundle already exists"
    request_parent=$(dirname "$request_file")
    [ -d "$request_parent" ] || die "request-receipt directory is absent"
    case "$(file_mode "$request_parent")" in
        700|600) ;;
        *) die "request-receipt directory must be private" ;;
    esac

    max_time=30
    [ "$operation" = you_there ] && max_time=105
    engine=$(engine_endpoint "$engine_name")
    if [ "$mode" = admission ]; then
        url="$engine/diag/admission/request"
    else
        url="$engine/diag/op/$operation"
    fi

    request_id=$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')
    [ "${#request_id}" -eq 32 ] || die "could not generate request id"
    request_sha256=$(
        printf '%s\n' \
            "client_version=$CLIENT_VERSION" \
            "mode=$mode" \
            "operation=$operation" \
            "request_id=$request_id" \
            "body_sha256=$body_sha256" \
            "credential_sha256=$credential_sha256" | sha256sum | awk '{print $1}'
    )

    umask 077
    mkdir "$bundle"
    trap 'rm -f "$bundle/body.json" "$bundle/response.json" "$bundle/response.headers" "$bundle/request.meta" "$request_file"; rmdir "$bundle" 2>/dev/null || true' EXIT HUP INT TERM
    cp "$source_body" "$bundle/body.json"
    chmod 400 "$bundle/body.json"
    : > "$bundle/response.json"
    : > "$bundle/response.headers"
    chmod 600 "$bundle/response.json" "$bundle/response.headers"

    {
        printf '%s\n' 'silent'
        printf '%s\n' 'show-error'
        printf '%s\n' 'connect-timeout = 10'
        printf 'max-time = %s\n' "$max_time"
        printf '%s\n' 'request = "POST"'
        printf 'url = "%s"\n' "$url"
        printf '%s\n' 'header = "Content-Type: application/json"'
        printf '%s\n' 'header = "Accept: application/json"'
        printf '%s\n' 'header = "User-Agent: Ontinuity-HTTPS/2"'
        printf '%s\n' 'header = "X-Ontinuity-Client-Version: 2"'
        printf 'header = "X-Ontinuity-Request-ID: %s"\n' "$request_id"
        printf 'header = "X-Ontinuity-Request-SHA256: %s"\n' "$request_sha256"
        if [ "$mode" = capability ]; then
            printf 'header = "Authorization: Bearer %s"\n' "$credential"
        elif [ "$mode" = operator ]; then
            printf 'header = "X-Diag-Key: %s"\n' "$credential"
        fi
        printf 'data-binary = "@%s/body.json"\n' "$bundle"
        printf 'output = "%s/response.json"\n' "$bundle"
        printf 'dump-header = "%s/response.headers"\n' "$bundle"
        printf '%s\n' 'write-out = "ONTINUITY_HTTP_STATUS=%{http_code}\\n"'
        printf '%s\n' 'max-redirs = 0'
        printf '%s\n' 'proto = "=https"'
    } > "$request_file"
    chmod 600 "$request_file"
    config_sha256=$(file_hash "$request_file")

    {
        printf 'client_version=%s\n' "$CLIENT_VERSION"
        printf 'mode=%s\n' "$mode"
        printf 'engine=%s\n' "$engine_name"
        printf 'operation=%s\n' "$operation"
        printf 'request_id=%s\n' "$request_id"
        printf 'request_sha256=%s\n' "$request_sha256"
        printf 'config_sha256=%s\n' "$config_sha256"
        printf 'body_sha256=%s\n' "$(file_hash "$bundle/body.json")"
        printf 'credential_sha256=%s\n' "$credential_sha256"
    } > "$bundle/request.meta"
    chmod 400 "$bundle/request.meta"
    trap - EXIT HUP INT TERM

    printf 'ONTINUITY_REQUEST_READY=%s\n' "$request_file"
    printf 'ONTINUITY_REQUEST_ID=%s\n' "$request_id"
    printf 'ONTINUITY_SEND_EXACT=curl --disable --config - < %s\n' "$request_file"
}

check_request() {
    [ "$#" -eq 1 ] || usage
    request_file=$1
    bundle="${request_file}.d"
    meta="$bundle/request.meta"
    [ -f "$request_file" ] && [ -f "$meta" ] || die "request receipt is absent"
    [ "$(file_mode "$request_file")" = 600 ] || die "request receipt mode changed"
    [ "$(file_mode "$meta")" = 400 ] || die "request metadata mode changed"
    [ "$(file_mode "$bundle/body.json")" = 400 ] || die "request body mode changed"
    [ "$(file_mode "$bundle/response.json")" = 600 ] || die "response mode changed"
    [ "$(file_mode "$bundle/response.headers")" = 600 ] || die "header mode changed"

    expected_config=$(meta_field config_sha256 "$meta")
    expected_body=$(meta_field body_sha256 "$meta")
    [ "$(file_hash "$request_file")" = "$expected_config" ] || \
        die "request receipt bytes changed after prepare"
    [ "$(file_hash "$bundle/body.json")" = "$expected_body" ] || \
        die "request body bytes changed after prepare"
    printf 'ONTINUITY_REQUEST_CHECK=PASS\n'
    printf 'ONTINUITY_SEND_EXACT=curl --disable --config - < %s\n' "$request_file"
}

verify() {
    [ "$#" -eq 1 ] || usage
    request_file=$1
    check_request "$request_file" >/dev/null
    bundle="${request_file}.d"
    meta="$bundle/request.meta"
    mode=$(meta_field mode "$meta")
    operation=$(meta_field operation "$meta")
    request_id=$(meta_field request_id "$meta")
    status=$(awk '/^HTTP\// { code=$2 } END { print code }' \
        "$bundle/response.headers" | tr -d '\r')
    if [ -z "$status" ]; then
        printf 'ONTINUITY_SEND_UNPROVED=%s\n' "$request_file" >&2
        exit 75
    fi
    if [ "$mode" != operator ]; then
        response_request_id=$(awk -F': *' '
            tolower($1) == "x-ontinuity-request-id" { value=$2 }
            END { gsub("\r", "", value); print value }
        ' "$bundle/response.headers")
        [ "$response_request_id" = "$request_id" ] || {
            printf 'ONTINUITY_RESPONSE_ID_MISMATCH=%s\n' "$request_file" >&2
            exit 75
        }
    fi
    cat "$bundle/response.json"
    printf '\nONTINUITY_HTTP_STATUS=%s\n' "$status" >&2
    case "$status" in
        2??) exit 0 ;;
        403)
            [ "$mode" = capability ] && [ "$operation" = __probe__ ] && exit 0
            exit 22
            ;;
        *) exit 22 ;;
    esac
}

[ "$#" -ge 1 ] || usage
command=$1
shift
case "$command" in
    prepare) prepare "$@" ;;
    check) check_request "$@" ;;
    verify) verify "$@" ;;
    *) usage ;;
esac
