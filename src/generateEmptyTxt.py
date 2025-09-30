import os, shutil

if __name__ == "__main__":
    negatives = [
        "IMG_1831", "IMG_1832"
    ]
    
    png_dir = "../videos/imgs"
    out_dir = "../yolo_labels"
    
    for d in os.listdir(png_dir):
        if d in negatives:
            for file in os.listdir(os.path.join(png_dir, d)):
                file_name = os.path.splitext(file)[0] + ".txt"
                file_path = os.path.join(out_dir, f"{d}_yolo_labels", file_name)
                with open(file_name, 'w') as f:
                    pass