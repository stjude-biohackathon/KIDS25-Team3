import cv2
import os
from pathlib import Path

# Input directory with .mov files
input_dir = Path(r"")

# Output directory for frames
output_dir = Path(r"")
output_dir.mkdir(exist_ok=True)

# Loop through all .mov files
for mov_file in input_dir.glob("*.mov"):
    print(f"Processing {mov_file.name}...")

    # Make a subfolder for each video’s frames
    video_name = mov_file.stem
    video_out_dir = output_dir / video_name
    video_out_dir.mkdir(exist_ok=True)

    # Open video
    cap = cv2.VideoCapture(str(mov_file))
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break  # no more frames

        # Save each frame as PNG
        frame_path = video_out_dir / f"frame_{frame_idx:06d}.png"
        cv2.imwrite(str(frame_path), frame)
        frame_idx += 1

    cap.release()
    print(f"Saved {frame_idx} frames to {video_out_dir}")

print("✅ Done extracting frames!")
