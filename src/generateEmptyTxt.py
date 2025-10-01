import os, shutil

if __name__ == "__main__":
    negatives = [
        "IMG_1831", "IMG_1832"
    ] # videos without any tracked objects
    
    png_dir = "../videos/imgs"
    out_dir = "../yolo_labels"
    
    for d in os.listdir(png_dir):
        if d in negatives:
            for file in os.listdir(os.path.join(png_dir, d)):
                file_name = os.path.splitext(file)[0] + ".txt"
                file_path = os.path.join(out_dir, f"{d}_yolo_labels", file_name)
                if os.path.exists(file_path):
                    continue
                print('creating file')
                with open(file_path, 'w') as f:
                    pass