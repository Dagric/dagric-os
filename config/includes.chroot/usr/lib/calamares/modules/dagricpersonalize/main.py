# SPDX-License-Identifier: GPL-3.0-or-later
import sys
sys.path.insert(0, "/usr/lib/dagric")
from install_profile import GS_KEY, parse_profile, apply_to_target
import libcalamares


def pretty_name():
    return "Prepare your Dagric desktop"


def run():
    # Read only our allowlisted key. Never dump GlobalStorage: it has passwords.
    value = libcalamares.globalstorage.value(GS_KEY)
    try:
        parse_profile(value)
        operation = libcalamares.job.configuration.get("operation")
        if operation == "validate":
            return None  # This runs BEFORE partition jobs or any disk writes.
        if operation != "apply":
            raise ValueError("Unknown personalization operation")
        apply_to_target(libcalamares.globalstorage.value("rootMountPoint"),
                        libcalamares.globalstorage.value("username"), value)
    except (OSError, ValueError, TypeError) as error:
        return ("Your desktop choices could not be prepared", str(error))
    return None
