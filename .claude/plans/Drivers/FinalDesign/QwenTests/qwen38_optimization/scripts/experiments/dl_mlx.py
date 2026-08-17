from huggingface_hub import snapshot_download
p = snapshot_download("mlx-community/Qwen3.8-27B-4bit",
                      max_workers=2, resume_download=True)
print("DOWNLOADED TO:", p)
