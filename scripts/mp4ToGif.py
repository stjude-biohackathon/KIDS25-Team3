import os

input_dir = ".\\resources"

if "sam2.mp4" not in os.listdir(input_dir):
    raise FileNotFoundError("sam2.mp4 not found in .\\resources")

file_name = f"{input_dir}\\sam2.mp4"

def main():
    if "palette.png" not in os.listdir(input_dir):
        raise FileNotFoundError(f"palette.png not found in {input_dir}")
    os.system(f'ffmpeg -i {file_name} -i {input_dir}\\palette.png -lavfi "paletteuse" {file_name[:-4]}.gif')
if __name__ == "__main__":
    main()
