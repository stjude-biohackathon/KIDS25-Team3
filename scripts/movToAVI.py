import os

input_directory = ".\\videos\\vids"
output_directory = ".\\videos\\vids_avi"

if "vids_avi" not in os.listdir(".\\videos"):
    os.mkdir('.\\videos\\vids_avi')

def main():
    for file_name in os.listdir(input_directory):
        # clip = VideoFileClip(f"{input_directory}\\{file_name}")
        # clip.write_videofile(f"{output_directory}\\{file_name[:-4]}_yuv420p.avi", codec='rawvideo', audio_codec='pcm_s16le', ffmpeg_params=['-pixel_format','yuv420p'])
        os.system(f"ffmpeg -i {input_directory}\\{file_name} -c:v rawvideo -c:a pcm_s16le {output_directory}\\{file_name[:-4]}.avi")
if __name__ == "__main__":
    main()