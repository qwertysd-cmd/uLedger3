yell() { echo -e "\n❌ ERROR"; echo "$0: $*" >&2; }
affirm() { echo -e "\n✅ AFFIRM"; echo "$0: $*" >&2; }
warn() { echo -e "\n⚠️  WARNING"; echo "$0: $*" >&2; }
info() { echo -e "\nℹ️  INFO"; echo "$0: $*" >&2; }
die() { yell "$*"; exit 111; }
try() { "$@" || die "cannot $*"; }

redirect() { a="$1"; shift; "$@" > "$a"; }
silent() { redirect /dev/null "$@"; }

run_and_expect_error() {
  local command="$1"
  local error="$2"

  local output
  output=$(eval "$command" 2>&1 > /dev/null)
  local status=$?

  # Check if exit status is non-zero (usually an unhandled exception exits with non-zero)
  if [ $status -eq 0 ]; then
    yell "$command exited with status 0, expected failure with $error."
    return 1
  fi

  echo "$output" | grep -q "$error"
}
