import cv2
import os, shutil
from pathlib import Path

# Input directory with .mov files
input_dir = Path(r"./videos/vids")

# Output directory for frames
output_dir = Path(r"./videos/imgs")
output_dir.mkdir(exist_ok=True)

finished_vids_dir = Path(r"./videos/finished_videos")

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
        frame_path = video_out_dir / f"{video_name}frame_{frame_idx:06d}.png"
        cv2.imwrite(str(frame_path), frame)
        frame_idx += 1

    cap.release()
    print(f"Saved {frame_idx} frames to {video_out_dir}")
    shutil.move(os.path.join(input_dir, mov_file.name), os.path.join(finished_vids_dir, mov_file.name))

print("✅ Done extracting frames!")
