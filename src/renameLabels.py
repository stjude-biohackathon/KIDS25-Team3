import os, shutil

if __name__ == "__main__":
    make_dir = "../yolo_labels/combined"
    os.makedirs(make_dir, exist_ok=True)
    label_dir = "../yolo_labels"
    for d in os.listdir(label_dir): # yolo_labels/
        if not os.path.isdir(os.path.join(label_dir, d)) or d == 'combined':
            continue
        
        p = os.path.join(label_dir, d)      # yolo_labels/IMG...
        for file in os.listdir(p):
            print(os.path.splitext(file))
            if file == 'classes.txt' or os.path.splitext(file)[1] != '.txt':
                continue
            
            src_path = os.path.join(p, file)    # yolo_labels/IMG.../frame000000.txt
            if "IMG" in file:
                d = ''
            dst_path = os.path.join(make_dir, d.replace("_yolo_labels", "") + file) # yolo_labels/combined/IMG...frame000000.txt
            shutil.move(src_path, dst_path)
