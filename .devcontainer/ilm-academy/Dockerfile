FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

# The base image lists the Yarn apt repository, whose signing key has expired: `apt-get update` then fails
# (exit 100) and the SSH server feature cannot install, so the codespace falls back to a recovery container.
# Nothing here uses Yarn.
RUN rm -f /etc/apt/sources.list.d/yarn.list
