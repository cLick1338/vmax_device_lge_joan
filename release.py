# Vmax
"""Create local signing keys, sign joan builds, and check native properties."""

import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[3]
KEYS = ROOT / ".repo/local_keys/joan"
BASE_KEYS = ("releasekey", "platform", "shared", "media", "networkstack",
             "bluetooth", "nfc", "sdk_sandbox")
SUBJECT = "/O=Vmax/OU=joan/CN=joan release"


def run(*args, **kwargs):
    subprocess.run([str(arg) for arg in args], check=True, cwd=ROOT, **kwargs)


def make_key(name, apex=False):
    prefix = KEYS / name
    cert, private = Path(str(prefix) + ".x509.pem"), Path(str(prefix) + ".pk8")
    if cert.exists() != private.exists():
        raise RuntimeError(f"Incomplete key pair: {prefix}")
    if not cert.exists():
        print(f"Generating {name}", flush=True)
        with tempfile.TemporaryDirectory(prefix="joan-key-") as temporary:
            pem = Path(temporary) / "private.pem"
            temporary_cert = Path(temporary) / "certificate.pem"
            temporary_private = Path(temporary) / "private.pk8"
            run("openssl", "genrsa", "-out", pem, "4096" if apex else "2048")
            run("openssl", "req", "-new", "-x509", "-sha256", "-key", pem,
                "-out", temporary_cert, "-days", "10000", "-subj", SUBJECT)
            run("openssl", "pkcs8", "-in", pem, "-topk8", "-outform", "DER",
                "-out", temporary_private, "-nocrypt")
            temporary_cert.replace(cert)
            temporary_private.replace(private)
    if apex and not Path(str(prefix) + ".pem").exists():
        run("openssl", "pkcs8", "-inform", "DER", "-in", private,
            "-nocrypt", "-out", str(prefix) + ".pem")
    return str(prefix.relative_to(ROOT))


def make_base_keys():
    os.umask(0o077)
    KEYS.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in BASE_KEYS:
        make_key(name)
    # SELinux signer definitions resolve testkey relative to the default key directory.
    for suffix in (".pk8", ".x509.pem"):
        alias = KEYS / ("testkey" + suffix)
        if not alias.exists():
            alias.symlink_to("releasekey" + suffix)


def records(data):
    for line in data.decode().splitlines():
        yield dict(re.findall(r'(\w+)="([^"]*)"', line))


def properties(archive):
    for name in ("SYSTEM/build.prop", "SYSTEM/system/build.prop"):
        if name in archive.namelist():
            return dict(line.split("=", 1) for line in
                        archive.read(name).decode().splitlines()
                        if "=" in line and not line.startswith("#"))
    raise RuntimeError("No system build.prop in target files")


def verify_props(props, signed, variant):
    if variant not in ("user", "userdebug"):
        raise RuntimeError(f"Unsupported release variant: {variant}")
    expected = {"ro.build.type": variant, "ro.build.flavor": f"lineage_joan-{variant}",
                "ro.debuggable": "0" if variant == "user" else "1", "ro.secure": "1"}
    if signed:
        expected["ro.build.tags"] = "release-keys"
    for name, value in expected.items():
        actual = props.get(name)
        if actual != value:
            raise RuntimeError(f"{name}: expected {value!r}, got {actual!r}")
    display = props.get("ro.build.display.id", "")
    if "eng." in display or (signed and any(tag in display for tag in ("test-keys", "dev-keys"))):
        raise RuntimeError(f"Unexpected display ID: {display}")
    for name in (*expected, "ro.build.display.id"):
        print(f"{name}={props.get(name)}")


def sign(target, output):
    make_base_keys()
    target = target.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target) as archive:
        variant = properties(archive).get("ro.build.type")
        verify_props(properties(archive), signed=False, variant=variant)
    build_number = re.sub(
        r"[^A-Za-z0-9._-]", "_", os.environ.get("BUILD_NUMBER", "unknown"))
    ota = output / f"lineage_joan-{variant}-{build_number}-signed-ota.zip"
    if ota.exists():
        raise RuntimeError(f"Refusing to overwrite release artifact: {ota}")
    host = ROOT / os.environ.get("OUT_DIR", "out") / "host/linux-x86/bin"
    java = Path(os.environ.get("ANDROID_JAVA_HOME", ROOT / "prebuilts/jdk/jdk21/linux-x86"))
    os.environ["PATH"] = os.pathsep.join((str(host), str(java / "bin"), os.environ["PATH"]))
    args = [host / "sign_target_files_apks", "-o", "-d", KEYS]
    with zipfile.ZipFile(target) as archive:
        apks = list(records(archive.read("META/apkcerts.txt")))
        installed = {Path(name).name for name in archive.namelist()
                     if name.endswith(".apk")}
        certs = set()
        for entry in apks:
            cert = entry["certificate"]
            # Include production Mainline APK keys, including APKs inside APEXes.
            if (entry["name"] in installed or
                    (cert.startswith("packages/modules/") and "/tests/" not in cert)):
                if cert not in ("PRESIGNED", "EXTERNAL"):
                    certs.add(cert.removesuffix(".x509.pem"))
        for cert in sorted(certs):
            if cert.startswith(str(KEYS.relative_to(ROOT)) + "/"):
                name = Path(cert).name
            elif cert.startswith("build/make/target/product/security/"):
                name = Path(cert).name
                name = "releasekey" if name in ("testkey", "devkey") else name
            else:
                name = "apk-" + Path(cert).name + "-" + hashlib.sha256(
                    cert.encode()).hexdigest()[:12]
            args.extend(("-k", f"{cert}={make_key(name)}"))
        installed_apex = {Path(name).name.replace(".capex", ".apex")
                          for name in archive.namelist()
                          if name.endswith((".apex", ".capex"))}
        for entry in records(archive.read("META/apexkeys.txt")):
            if entry["name"] not in installed_apex:
                continue
            if entry["private_key"] == "PRESIGNED":
                continue
            name = entry["name"].removesuffix(".apex")
            key = make_key(name, apex=True)
            args.extend(("--extra_apks", f"{entry['name']}={key}",
                         "--extra_apex_payload_key", f"{entry['name']}={key}.pem"))
    with tempfile.TemporaryDirectory(prefix=".sign-", dir=output) as temporary:
        signed = Path(temporary) / "signed-target_files.zip"
        staged_ota = Path(temporary) / ota.name
        run(*args, target, signed)
        with zipfile.ZipFile(signed) as archive:
            verify_props(properties(archive), signed=True, variant=variant)
        run(host / "ota_from_target_files", "-k", KEYS / "releasekey",
            "--block", "--backup=true", signed, staged_ota)
        staged_ota.replace(ota)
    print(f"\nINSTALL IN RECOVERY (ADB SIDELOAD): {ota}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("keys")
    signing = commands.add_parser("sign")
    signing.add_argument("target", type=Path)
    signing.add_argument("output", type=Path)
    verify = commands.add_parser("verify")
    verify.add_argument("target", type=Path)
    verify.add_argument("--variant", choices=("user", "userdebug"), default="userdebug")
    device = commands.add_parser("verify-device")
    device.add_argument("--adb", default="adb")
    device.add_argument("--variant", choices=("user", "userdebug"), default="userdebug")
    args = parser.parse_args()
    if args.command == "keys":
        make_base_keys()
    elif args.command == "sign":
        sign(args.target, args.output)
    elif args.command == "verify":
        with zipfile.ZipFile(args.target) as archive:
            verify_props(properties(archive), signed=True, variant=args.variant)
    else:
        data = subprocess.check_output([args.adb, "shell", "getprop"], text=True)
        verify_props(dict(re.findall(r"\[([^]]+)\]: \[([^]]*)\]", data)),
                     signed=True, variant=args.variant)


if __name__ == "__main__":
    main()
