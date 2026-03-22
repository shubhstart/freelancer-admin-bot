import shutil
import os

src = r"C:\Users\SHUBHAM KUMAR\Desktop\My_Agent_Project3"
dst = r"C:\Users\SHUBHAM KUMAR\Desktop\My_Agent_Project3_Free"

if not os.path.exists(dst):
    shutil.copytree(src, dst)
    print(f"Copied {src} to {dst}")
else:
    print(f"Destination {dst} already exists.")
