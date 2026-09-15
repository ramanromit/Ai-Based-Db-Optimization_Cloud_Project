import os
import subprocess
import sys

def download_ieee_dataset(output_dir: str = "data/raw"):
    """
    Attempts to download the official IEEE-CIS dataset via Kaggle CLI.
    If credentials are not found, falls back to generating a synthetic dataset.
    """
    os.makedirs(output_dir, exist_ok=True)
    kaggle_json = os.path.expanduser("~/.kaggle/kaggle.json")
    
    if os.path.exists(kaggle_json) or os.getenv("KAGGLE_USERNAME"):
        print("Found Kaggle credentials. Attempting official dataset download...")
        try:
            cmd = ["kaggle", "competitions", "download", "-c", "ieee-fraud-detection", "-p", output_dir]
            subprocess.run(cmd, check=True)
            print(f"Dataset successfully downloaded to {output_dir}")
            return
        except Exception as e:
            print(f"Kaggle download failed: {e}. Falling back to synthetic generator.")
    else:
        print("No Kaggle credentials found (~/.kaggle/kaggle.json). Using synthetic IEEE-CIS generator.")
        
    from data.generator import generate_synthetic_ieee_cis_dataset
    generate_synthetic_ieee_cis_dataset(10000, output_path=os.path.join(output_dir, "train_transaction.csv"))

if __name__ == "__main__":
    download_ieee_dataset()
