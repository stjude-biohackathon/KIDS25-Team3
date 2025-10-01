#!/usr/bin/env python3
"""
General bounding box extraction script for any video with SAM2 annotations
Usage: python extract_boxes_general.py --video VIDEO_FILE --annotations ANNOTATION_FILE [options]
"""

import json
import cv2
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os
from pathlib import Path
from ultralytics.models.sam import SAM2VideoPredictor

def load_annotations(json_path):
    """Load annotations from JSON file"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data

def mask_to_bbox(mask, threshold=0.5):
    """Convert mask to bounding box coordinates"""
    binary_mask = mask > threshold
    
    if not binary_mask.any():
        return None
    
    # Find coordinates of mask pixels
    coords = np.where(binary_mask)
    y_min, y_max = coords[0].min(), coords[0].max()
    x_min, x_max = coords[1].min(), coords[1].max()
    
    return {
        'x_min': int(x_min),
        'y_min': int(y_min),
        'x_max': int(x_max),
        'y_max': int(y_max),
        'width': int(x_max - x_min),
        'height': int(y_max - y_min),
        'center_x': int((x_min + x_max) / 2),
        'center_y': int((y_min + y_max) / 2),
        'area': int(binary_mask.sum())
    }

def create_subset_video(input_video, output_video, max_frames):
    """Create a subset video with only the first max_frames frames"""
    if os.path.exists(output_video):
        print(f"Subset video already exists: {output_video}")
        cap = cv2.VideoCapture(output_video)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        return frame_count
    
    cap = cv2.VideoCapture(input_video)
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
    
    frame_count = 0
    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        out.write(frame)
        frame_count += 1
    
    cap.release()
    out.release()
    
    print(f"Created subset video with {frame_count} frames: {output_video}")
    return frame_count

def main():
    parser = argparse.ArgumentParser(description='Extract bounding boxes from video using SAM2 annotations')
    parser.add_argument('--video', required=True, help='Input video file (e.g., IMG_1824.mov)')
    parser.add_argument('--annotations', required=True, help='Annotation JSON file (e.g., IMG_1824_frame_000000_annotations.json)')
    parser.add_argument('--output', help='Output JSON file (default: auto-generated from video name)')
    parser.add_argument('--fg-points', type=int, default=3, help='Number of foreground points to use (default: 3)')
    parser.add_argument('--bg-points', type=int, default=3, help='Number of background points to use (default: 3)')
    parser.add_argument('--max-frames', type=int, help='Maximum frames to process (default: all frames)')
    parser.add_argument('--conf', type=float, default=0.25, help='Confidence threshold (default: 0.25)')
    parser.add_argument('--imgsz', type=int, default=1024, help='Image size for processing (default: 1024)')
    parser.add_argument('--model', default='sam2_b.pt', help='SAM2 model file (default: sam2_b.pt)')
    parser.add_argument('--coverage-threshold', type=float, default=0.1, help='Minimum coverage for valid detection (default: 0.1)')
    parser.add_argument('--no-visualization', action='store_true', help='Skip creating visualization plots')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}")
        return
    
    if not os.path.exists(args.annotations):
        print(f"Error: Annotation file not found: {args.annotations}")
        return
    
    # Generate output filename if not provided
    if args.output is None:
        video_stem = Path(args.video).stem
        args.output = f"{video_stem}_bounding_boxes.json"
    
    print(f"Processing: {args.video}")
    print(f"Annotations: {args.annotations}")
    print(f"Output: {args.output}")
    
    # Load annotations
    data = load_annotations(args.annotations)
    
    # Extract points
    available_fg = len(data['foreground_points'])
    available_bg = len(data['background_points'])
    
    fg_points = data['foreground_points'][:args.fg_points]
    bg_points = data['background_points'][:args.bg_points]
    
    print(f"Image dimensions: {data['image_size']}")
    print(f"Available points: {available_fg} foreground, {available_bg} background")
    print(f"Using: {len(fg_points)} foreground, {len(bg_points)} background points")
    print(f"Foreground points: {fg_points}")
    print(f"Background points: {bg_points}")
    
    # Determine video to process
    video_to_process = args.video
    actual_frames = None
    
    if args.max_frames:
        # Create subset video
        video_stem = Path(args.video).stem
        subset_video = f"{video_stem}_subset_{args.max_frames}.mp4"
        actual_frames = create_subset_video(args.video, subset_video, args.max_frames)
        video_to_process = subset_video
        print(f"Processing subset: {actual_frames} frames")
    
    # Create SAM2VideoPredictor
    overrides = dict(
        conf=args.conf,
        task="segment",
        mode="predict",
        imgsz=args.imgsz,
        model=args.model
    )
    
    predictor = SAM2VideoPredictor(overrides=overrides)
    
    # Combine points and labels
    points_combined = fg_points + bg_points
    labels_combined = [1] * len(fg_points) + [0] * len(bg_points)
    
    print(f"Points: {points_combined}")
    print(f"Labels: {labels_combined}")
    
    # Run inference
    print(f"Running SAM2 inference on {video_to_process}...")
    results = predictor(
        source=video_to_process,
        points=[points_combined],
        labels=[labels_combined]
    )
    
    print(f"Inference completed! Results type: {type(results)}, length: {len(results)}")
    
    # Extract bounding boxes for all frames
    all_boxes = []
    valid_frames = 0
    
    for frame_idx, result in enumerate(results):
        frame_data = {
            'frame_index': frame_idx,
            'bbox': None,
            'mask_coverage': 0.0,
            'has_detection': False
        }
        
        if hasattr(result, 'masks') and result.masks is not None:
            try:
                mask = result.masks[0].data[0].cpu().numpy()
                coverage = (mask > 0.5).sum() / mask.size * 100
                
                frame_data['mask_coverage'] = coverage
                
                if coverage > args.coverage_threshold:
                    bbox = mask_to_bbox(mask)
                    if bbox:
                        frame_data['bbox'] = bbox
                        frame_data['has_detection'] = True
                        valid_frames += 1
                
            except Exception as e:
                print(f"Error processing frame {frame_idx}: {e}")
        
        all_boxes.append(frame_data)
        
        # Print progress every 50 frames
        if frame_idx % 50 == 0:
            print(f"Processed frame {frame_idx}, valid detections so far: {valid_frames}")
    
    # Save results to JSON
    output_data = {
        'video_source': args.video,
        'annotation_source': args.annotations,
        'processing_parameters': {
            'fg_points_used': len(fg_points),
            'bg_points_used': len(bg_points),
            'max_frames': args.max_frames,
            'conf': args.conf,
            'imgsz': args.imgsz,
            'model': args.model,
            'coverage_threshold': args.coverage_threshold
        },
        'total_frames': len(results),
        'valid_detections': valid_frames,
        'image_dimensions': data['image_size'],
        'input_points': {
            'foreground': fg_points,
            'background': bg_points,
            'combined': points_combined,
            'labels': labels_combined,
            'available_foreground': available_fg,
            'available_background': available_bg
        },
        'frames': all_boxes
    }
    
    # Add subset info if applicable
    if args.max_frames:
        output_data['subset_info'] = {
            'subset_video': video_to_process,
            'max_frames_requested': args.max_frames,
            'actual_frames_processed': actual_frames
        }
    
    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nResults Summary:")
    print(f"- Video processed: {video_to_process}")
    print(f"- Total frames processed: {len(results)}")
    print(f"- Frames with valid detections: {valid_frames}")
    print(f"- Detection rate: {valid_frames/len(results)*100:.1f}%")
    print(f"- Results saved to: {args.output}")
    
    # Create visualization if requested
    if not args.no_visualization:
        video_stem = Path(args.video).stem
        create_summary_visualization(all_boxes, points_combined, labels_combined, 
                                   data['image_size'], video_stem, args.video)

def create_summary_visualization(all_boxes, points, labels, image_size, video_name, video_path):
    """Create a summary visualization of the tracking results"""
    
    # Extract data for plotting
    frame_indices = [frame['frame_index'] for frame in all_boxes]
    coverages = [frame['mask_coverage'] for frame in all_boxes]
    center_xs = [frame['bbox']['center_x'] if frame['bbox'] else None for frame in all_boxes]
    center_ys = [frame['bbox']['center_y'] if frame['bbox'] else None for frame in all_boxes]
    
    # Create plots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot 1: Mask coverage over time
    axes[0, 0].plot(frame_indices, coverages, 'b-', alpha=0.7)
    axes[0, 0].set_xlabel('Frame Index')
    axes[0, 0].set_ylabel('Mask Coverage (%)')
    axes[0, 0].set_title(f'Mask Coverage Over Time - {video_name}')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Plot 2: Center X position over time
    valid_frames = [i for i, x in enumerate(center_xs) if x is not None]
    valid_x = [x for x in center_xs if x is not None]
    
    if valid_x:
        axes[0, 1].plot(valid_frames, valid_x, 'r-', alpha=0.7)
        axes[0, 1].set_xlabel('Frame Index')
        axes[0, 1].set_ylabel('Center X Position')
        axes[0, 1].set_title('Horizontal Movement')
        axes[0, 1].grid(True, alpha=0.3)
    else:
        axes[0, 1].text(0.5, 0.5, 'No valid detections', ha='center', va='center', transform=axes[0, 1].transAxes)
        axes[0, 1].set_title('Horizontal Movement')
    
    # Plot 3: Center Y position over time
    valid_y = [y for y in center_ys if y is not None]
    
    if valid_y:
        axes[1, 0].plot(valid_frames, valid_y, 'g-', alpha=0.7)
        axes[1, 0].set_xlabel('Frame Index')
        axes[1, 0].set_ylabel('Center Y Position')
        axes[1, 0].set_title('Vertical Movement')
        axes[1, 0].grid(True, alpha=0.3)
    else:
        axes[1, 0].text(0.5, 0.5, 'No valid detections', ha='center', va='center', transform=axes[1, 0].transAxes)
        axes[1, 0].set_title('Vertical Movement')
    
    # Plot 4: Input points reference
    # Try to find first frame image
    video_stem = Path(video_path).stem
    possible_frame_paths = [
        f"{video_stem}_frames/frame_000000.jpg",
        f"{video_stem}_frames/frame_000000.png",
        f"frames/frame_000000.jpg",
        f"frames/frame_000000.png"
    ]
    
    frame_image = None
    for frame_path in possible_frame_paths:
        if os.path.exists(frame_path):
            frame_image = cv2.imread(frame_path)
            if frame_image is not None:
                break
    
    if frame_image is not None:
        image_rgb = cv2.cvtColor(frame_image, cv2.COLOR_BGR2RGB)
        axes[1, 1].imshow(image_rgb)
        
        for point, label in zip(points, labels):
            x, y = point
            color = 'go' if label == 1 else 'ro'
            axes[1, 1].plot(x, y, color, markersize=8, markeredgecolor='white', markeredgewidth=2)
        
        axes[1, 1].set_title(f'Input Points Reference - {video_name}')
        axes[1, 1].axis('off')
    else:
        axes[1, 1].text(0.5, 0.5, f'First frame not found\nImage size: {image_size[0]}x{image_size[1]}\nPoints: {len(points)}', 
                       ha='center', va='center', transform=axes[1, 1].transAxes)
        axes[1, 1].set_title(f'{video_name} Info')
    
    plt.tight_layout()
    output_plot = f'{video_name}_tracking_summary.png'
    plt.savefig(output_plot, dpi=150, bbox_inches='tight')
    plt.show()
    
    print(f"Tracking summary visualization saved as '{output_plot}'")

if __name__ == "__main__":
    main()