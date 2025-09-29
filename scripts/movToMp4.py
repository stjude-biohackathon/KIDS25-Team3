import os
from moviepy.editor import VideoFileClip

folder_path = r"C:\Users\jzhang29\Projects\Archive\KIDS25-Team3\videos\vids_mp4"

for filename in os.listdir(folder_path):
    if filename.lower().endswith(".mov"):
        mov_path = os.path.join(folder_path, filename)
        mp4_filename = os.path.splitext(filename)[0] + ".mp4"
        mp4_path = os.path.join(folder_path, mp4_filename)
        
        print(f"Converting {filename} to {mp4_filename}...")
        
        # Load the .mov video
        clip = VideoFileClip(mov_path)
        # Write it as .mp4
        clip.write_videofile(mp4_path, codec="libx264", audio_codec="aac")
        clip.close()

print("Conversion complete!")
