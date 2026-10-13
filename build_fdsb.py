"""Build FDSB for Android (arm64) using the same flow as flet-android-background's own build.py:

    1. `flet build apk`  -> generates build/flutter (+ site-packages, python-app)
    2. patch flet-android-notifications (if it is a dependency)
    3. configure_android_project(...) from flet-android-background
    4. small Gradle patches (applicationId, Kotlin plugin)
    5. `flutter build apk|appbundle` with the SERIOUS_PYTHON_* environment

Examples:
    python build_fdsb.py --clean                 # debug APK, fresh generation (recommended the first time)
    python build_fdsb.py                         # debug APK
    python build_fdsb.py --release               # release APK (signed with the keystore from pyproject.toml)
    python build_fdsb.py --release --aab         # release AAB (arm64 only)
Release builds increment build_number.txt; debug builds do not.
"""
import argparse
import getpass
import io
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
FLUTTER_DIR = BUILD / "flutter"
APP_ID = "com.freedesingstudiobot.FDSB"  # must match the package registered in Google Play Console

os.environ.setdefault("JAVA_HOME", r"C:\Users\NTC\java\17.0.13+11")
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

parser = argparse.ArgumentParser()
parser.add_argument("--release", action="store_true", help="release build (default: debug)")
parser.add_argument("--aab", action="store_true", help="build an App Bundle instead of an APK")
parser.add_argument("--clean", action="store_true", help="delete build/flutter, site-packages and hash first")
parser.add_argument("--service-type", choices=["dataSync", "shortService", "specialUse"], default="dataSync")
parser.add_argument("--service-subtype", default="", help="required for specialUse")
parser.add_argument("--build-number", type=int, default=None)
parser.add_argument("--no-restore-dart", action="store_true", help="skip the usesChronometer/showWhen cleanup")
options = parser.parse_args()

if options.service_type == "specialUse" and not options.service_subtype.strip():
    raise SystemExit("specialUse requires --service-subtype (Google Play reviews it).")

mode = "release" if options.release else "debug"
config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
release_name = config["project"]["version"]
dependencies = " ".join(config["project"].get("dependencies", []))
uses_notifications = "flet-android-notifications" in dependencies
uses_background = "flet-android-background" in dependencies.replace("_", "-")
if not uses_background:
    raise SystemExit("flet-android-background is not listed in pyproject.toml dependencies.")

number_file = ROOT / "build_number.txt"
if options.build_number is not None:
    build_number = options.build_number
else:
    last = int(number_file.read_text().strip() or 0) if number_file.exists() else 0
    build_number = last + 1
print(f"==> mode={mode} version={release_name} build_number={build_number} service={options.service_type}", flush=True)


def set_signing_env():
    """Release only: key_store/key_alias from pyproject.toml, password from env or a prompt."""
    sign = config.get("tool", {}).get("flet", {}).get("android", {}).get("signing", {})
    store = os.environ.get("FLET_ANDROID_SIGNING_KEY_STORE") or sign.get("key_store")
    alias = os.environ.get("FLET_ANDROID_SIGNING_KEY_ALIAS") or sign.get("key_alias")
    if not store or not alias:
        raise SystemExit("Missing key_store/key_alias ([tool.flet.android.signing] in pyproject.toml).")
    store_path = Path(store)
    if not store_path.is_absolute():
        store_path = ROOT / store_path
    if not store_path.exists():
        raise SystemExit(f"Keystore not found: {store_path}")
    password = os.environ.get("FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD") or getpass.getpass("Keystore password: ")
    os.environ["FLET_ANDROID_SIGNING_KEY_STORE"] = str(store_path)
    os.environ["FLET_ANDROID_SIGNING_KEY_ALIAS"] = alias
    os.environ["FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD"] = password
    os.environ.setdefault("FLET_ANDROID_SIGNING_KEY_PASSWORD", password)


if options.release:
    set_signing_env()

if options.clean:
    for path in (FLUTTER_DIR, BUILD / "site-packages", BUILD / "python-app"):
        shutil.rmtree(path, ignore_errors=True)
BUILD.mkdir(exist_ok=True)
# force flet to regenerate the project; .hash is a directory in flet's build (a file in some versions)
hash_path = BUILD / ".hash"
if hash_path.is_dir():
    shutil.rmtree(hash_path, ignore_errors=True)
elif hash_path.exists():
    hash_path.unlink()

# -- 1) flet build: generates the Flutter project, site-packages and the python app -------------
log_path = BUILD / "generate.log"
print(f"==> flet build apk (log: {log_path})", flush=True)
with log_path.open("w", encoding="utf-8") as log:
    result = subprocess.run(
        [sys.executable, "-m", "flet.cli", "build", "apk",
         "--exclude", "app_data", ".git", ".hash", "build", "__pycache__", "*.spec",
         "--arch", "arm64-v8a", "--no-rich-output", "--yes", "--skip-flutter-doctor",
         "--flutter-build-args=--debug", "-v"],
        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
    )
if result.returncode:
    text = re.sub(r"\s+", " ", log_path.read_text(encoding="utf-8", errors="replace"))
    failures = re.findall(r"Execution failed for task '([^']+)'", text)
    if not (FLUTTER_DIR / "android/app/build.gradle.kts").exists():
        raise SystemExit(f"flet build failed and no Flutter project was generated; see {log_path}")
    # The Gradle step inside flet fails before our patches are applied; that is expected.
    print(f"  -> flet exited with {result.returncode}; failed tasks: {failures or 'unknown'} (continuing)", flush=True)

# -- 2) flet-android-notifications patch ----------------------------------------------------------
if uses_notifications:
    print("==> patching flet-android-notifications", flush=True)
    try:
        from flet_android_notifications.patcher import patch_android_project
        patch_android_project(FLUTTER_DIR)
    except ImportError:
        subprocess.run(["flet-android-notifications-patch", "--project-root", str(FLUTTER_DIR)], check=True)
    if not options.no_restore_dart:
        pkg = BUILD / "flutter-packages" / "flet_android_notifications"
        for dart in pkg.rglob("*.dart") if pkg.exists() else []:
            old = dart.read_text(encoding="utf-8")
            new = re.sub(r",\s*usesChronometer:\s*true", "", old)
            new = re.sub(r"usesChronometer:\s*true\s*,?", "", new)
            new = re.sub(r",\s*showWhen:\s*true", "", new)
            new = re.sub(r"showWhen:\s*true\s*,?", "", new)
            if new != old:
                dart.write_text(new, encoding="utf-8")
                print(f"  -> cleaned {dart.name}", flush=True)

# -- 3) flet-android-background -------------------------------------------------------------------
print(f"==> configure_android_project(service_type={options.service_type})", flush=True)
from flet_android_background.android import configure_android_project

kwargs = {"service_type": options.service_type}
if options.service_subtype.strip():
    kwargs["subtype"] = options.service_subtype.strip()
configure_android_project(FLUTTER_DIR, **kwargs)

# -- 4) Gradle patches (after the library, which may touch build.gradle.kts as well) ---------------
gradle_file = FLUTTER_DIR / "android/app/build.gradle.kts"
gradle = gradle_file.read_text(encoding="utf-8")
gradle, count = re.subn(r'applicationId\s*=\s*"[^"]*"', f'applicationId = "{APP_ID}"', gradle, count=1)
if not count:
    raise SystemExit(f"applicationId not found in {gradle_file}")
# The generated template assumes "built-in Kotlin"; on AGP 8.x nothing compiled MainActivity.kt
# (':app:compileDebugKotlin' did not exist -> ClassNotFoundException at launch).
if not re.search(r"org\.jetbrains\.kotlin\.android|kotlin-android", gradle):
    gradle = re.sub(r'(id\("com\.android\.application"\))',
                    r'\1\n    id("org.jetbrains.kotlin.android")', gradle, count=1)
    print("  -> applied org.jetbrains.kotlin.android plugin", flush=True)
gradle_file.write_text(gradle, encoding="utf-8")

# -- 5) flutter build -------------------------------------------------------------------------------
flutter = os.environ.get("FLUTTER_BIN") or shutil.which("flutter")
if not flutter:
    raise SystemExit("Set FLUTTER_BIN or add Flutter to PATH.")
env = dict(os.environ, SERIOUS_PYTHON_SITE_PACKAGES=str(BUILD / "site-packages"))
if (BUILD / "python-app").exists():
    env["SERIOUS_PYTHON_APP"] = str(BUILD / "python-app")
if (BUILD / ".python-version").exists():
    env["SERIOUS_PYTHON_VERSION"] = (BUILD / ".python-version").read_text().strip()

target = "appbundle" if options.aab else "apk"
command = [flutter, "build", target, f"--{mode}", "--build-name", release_name,
           "--build-number", str(build_number), "--target-platform", "android-arm64"]
print("==> " + " ".join(command), flush=True)
subprocess.run(command, cwd=FLUTTER_DIR, env=env, check=True)

if options.aab:
    source = FLUTTER_DIR / f"build/app/outputs/bundle/{mode}/app-{mode}.aab"
    out = BUILD / f"FDSB-{release_name}-b{build_number}-{mode}.aab"
else:
    source = FLUTTER_DIR / f"build/app/outputs/flutter-apk/app-{mode}.apk"
    out = BUILD / f"FDSB-arm64-{mode}.apk"
if not source.exists():
    raise SystemExit(f"Output not found: {source}")
shutil.copy2(source, out)

# -- 6) checks ----------------------------------------------------------------------------------------
with zipfile.ZipFile(out) as archive:
    names = archive.namelist()
    for name in names:
        if name.endswith("sitepackages.zip"):
            with zipfile.ZipFile(io.BytesIO(archive.read(name))) as inner:
                if inner.testzip() is not None:
                    raise RuntimeError(f"Corrupt {name}")
                entries = " ".join(inner.namelist())
                for module in ("flet/", "flet_android_background/"):
                    print(f"  -> sitepackages: {module} {'OK' if module in entries else 'MISSING'}", flush=True)
    has_main = any(n.endswith(".dex") and b"com/fdsb/fdsb/MainActivity" in archive.read(n) for n in names)
    print(f"  -> MainActivity in dex: {'OK' if has_main else 'MISSING (app will crash at launch)'}", flush=True)
    if not has_main:
        raise SystemExit("MainActivity was not compiled into the package.")

if options.release:
    number_file.write_text(str(build_number))
    print(f"  -> build number {build_number} saved (next: {build_number + 1})", flush=True)
print(out)