import os
import json
import logging
import tempfile
import numpy as np

logger = logging.getLogger(__name__)

# Try importing cv2 and mediapipe
try:
    import cv2
    import mediapipe as mp
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV or MediaPipe is not installed. Python face filter processing will be bypassed.")

def process_video_filters(input_path, output_path, filter_id, filter_config=None):
    if not OPENCV_AVAILABLE:
        # Fallback: copy file directly
        import shutil
        shutil.copy(input_path, output_path)
        return False
        
    try:
        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.3
        )
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            logger.error(f"Failed to open input video {input_path}")
            return False
            
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        
        # VP8 is excellent for webm container
        fourcc = cv2.VideoWriter_fourcc(*'VP80')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # Map filter IDs to static files
        filter_images = {
            'dog_face': 'static/filters/dog_face_filter.png',
            'cowboy_hat': 'static/filters/cowboy_hat.png',
            'glasses': 'static/filters/glasses.png',
            'glasses1': 'static/filters/glasses1.png',
            'glasses2': 'static/filters/glasses2.png',
            'glasses3': 'static/filters/glasses3.png',
            'moustache': 'static/filters/moustache.png',
            'mustache1': 'static/filters/mustache1.png',
            'left_eye': 'static/filters/left_eye.png',
            'right_eye': 'static/filters/right_eye.png'
        }
        
        # Load overlay image(s)
        filter_img = None
        img_path = filter_images.get(filter_id)
        if img_path and os.path.exists(img_path):
            filter_img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
            
        left_eye_img = None
        right_eye_img = None
        if filter_id == 'fire_eyes':
            le_path = filter_images.get('left_eye')
            re_path = filter_images.get('right_eye')
            if os.path.exists(le_path):
                left_eye_img = cv2.imread(le_path, cv2.IMREAD_UNCHANGED)
            if os.path.exists(re_path):
                right_eye_img = cv2.imread(re_path, cv2.IMREAD_UNCHANGED)

        # Draw frame by frame
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            h_frame, w_frame, _ = frame.shape
            
            # Run MediaPipe face mesh
            results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            if results.multi_face_landmarks and (filter_img is not None or filter_id == 'fire_eyes'):
                landmarks = results.multi_face_landmarks[0].landmark
                
                def get_pt(idx):
                    return int(landmarks[idx].x * w_frame), int(landmarks[idx].y * h_frame)
                
                try:
                    lex, ley = get_pt(33) # Left eye corner
                    rex, rey = get_pt(263) # Right eye corner
                    noseX, noseY = get_pt(4) # Nose tip
                    foreheadX, foreheadY = get_pt(10) # Forehead
                    
                    # Calculate scale
                    dx = rex - lex
                    dy = rey - ley
                    eye_dist = int(np.sqrt(dx*dx + dy*dy))
                    
                    if filter_id == 'fire_eyes' and left_eye_img is not None and right_eye_img is not None:
                        # Draw fire eyes on left and right eye positions
                        w = int(eye_dist * 2.3)
                        h = int(eye_dist * 2.3)
                        overlay_png(frame, left_eye_img, lex - w//2, ley - h//2, w, h)
                        overlay_png(frame, right_eye_img, rex - w//2, rey - h//2, w, h)
                        
                    elif filter_img is not None:
                        # Position based on filter type
                        if filter_id == 'dog_face':
                            w = int(eye_dist * 6.0)
                            h = int(eye_dist * 6.0)
                            x = foreheadX - w // 2
                            y = foreheadY - h // 2 + int(eye_dist * 0.4)
                        elif filter_id == 'cowboy_hat':
                            w = int(eye_dist * 7.0)
                            h = int(eye_dist * 5.0)
                            x = foreheadX - w // 2
                            y = foreheadY - h + int(eye_dist * 0.4)
                        elif filter_id.startswith('glasses'):
                            w = int(eye_dist * 3.75)
                            h = int(eye_dist * 1.6)
                            x = (lex + rex) // 2 - w // 2
                            y = (ley + rey) // 2 - h // 2
                        elif filter_id in ('moustache', 'mustache1'):
                            w = int(eye_dist * 3.05)
                            h = int(eye_dist * 1.1)
                            x = noseX - w // 2
                            y = noseY + int(eye_dist * 0.7)
                        else:
                            # Default eyewear center on eyes
                            w = int(eye_dist * 3.5)
                            h = int(eye_dist * 1.5)
                            x = (lex + rex) // 2 - w // 2
                            y = (ley + rey) // 2 - h // 2
                            
                        overlay_png(frame, filter_img, x, y, w, h)
                        
                except Exception as e:
                    logger.error(f"Error drawing overlay on frame: {e}")
                    
            out.write(frame)
            
        cap.release()
        out.release()
        face_mesh.close()
        return True
    except Exception as e:
        logger.error(f"Video filter processing failed: {e}")
        return False

def overlay_png(frame, overlay_img, x, y, w, h):
    if w <= 0 or h <= 0:
        return
        
    # Resize overlay
    overlay_resized = cv2.resize(overlay_img, (w, h))
    
    # Extract color and alpha channels
    overlay_rgb = overlay_resized[:, :, :3]
    overlay_alpha = overlay_resized[:, :, 3] / 255.0
    
    # Get ROI coordinates on frame
    y1, y2 = max(0, y), min(frame.shape[0], y + h)
    x1, x2 = max(0, x), min(frame.shape[1], x + w)
    
    # Adjust overlay crop if it goes off-screen
    oy1 = max(0, -y)
    oy2 = oy1 + (y2 - y1)
    ox1 = max(0, -x)
    ox2 = ox1 + (x2 - x1)
    
    if y2 > y1 and x2 > x1:
        alpha = overlay_alpha[oy1:oy2, ox1:ox2, np.newaxis]
        rgb = overlay_rgb[oy1:oy2, ox1:ox2]
        
        # Blend channels
        frame[y1:y2, x1:x2] = (1.0 - alpha) * frame[y1:y2, x1:x2] + alpha * rgb
