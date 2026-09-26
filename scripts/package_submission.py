import zipfile
from pathlib import Path

def make_zip():
    zip_name = "tireless_hand_code.zip"
    exclude_dirs = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache", ".system_generated", "videos_l2"}
    
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in Path(".").rglob("*"):
            if any(part in exclude_dirs for part in p.parts):
                continue
            if p.is_file() and p.name != zip_name and not p.name.endswith(".webm"):
                zf.write(p, arcname=str(p))
    
    print(f"[+] Successfully created {zip_name} ({Path(zip_name).stat().st_size / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    make_zip()
