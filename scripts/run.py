import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Lista de scripts a ejecutar en orden
scripts = [
    "get_cards.py",
    "post_cards.py",
    "post_comments.py",
    "post_images-s3.py"
]

for script in scripts:
    print(f"\nEjecutando {script}...\n")
    ret = subprocess.run(["python", script])
    if ret.returncode != 0:
        print(f"\n{script} terminó con error (código {ret.returncode}).")
        break

print("\nProceso completado.")
