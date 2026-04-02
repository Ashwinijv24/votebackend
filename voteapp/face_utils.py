import cv2
import numpy as np
from PIL import Image
import io
import json
import os
import tempfile

# Try to import face recognition libraries
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
    print("✓ face_recognition loaded successfully")
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("⚠ face_recognition not available")

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
    print("✓ DeepFace loaded successfully")
except ImportError:
    DEEPFACE_AVAILABLE = False
    print("⚠ DeepFace not available, using basic OpenCV")

def detect_face_in_image(image_file):
    """
    Detect faces in an uploaded image file using DeepFace or OpenCV.
    
    Returns:
        dict: {
            'success': bool,
            'face_count': int,
            'message': str,
            'encoding': str (JSON encoded face features),
            'confidence': float
        }
    """
    try:
        # Read image file
        image_file.seek(0)
        image_bytes = image_file.read()
        image_file.seek(0)  # Reset file pointer
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {
                'success': False,
                'face_count': 0,
                'message': 'Invalid image file. Could not read image.',
                'encoding': None,
                'confidence': 0.0
            }
        
        # Try face_recognition first (most accurate and simple)
        if FACE_RECOGNITION_AVAILABLE:
            return _detect_with_face_recognition(img)
        elif DEEPFACE_AVAILABLE:
            return _detect_with_deepface(img)
        else:
            return _detect_with_opencv(img)
        
    except Exception as e:
        return {
            'success': False,
            'face_count': 0,
            'message': f'Error processing image: {str(e)}',
            'encoding': None,
            'confidence': 0.0
        }


def _detect_with_face_recognition(img):
    """Detect face using face_recognition library (most accurate)"""
    try:
        # Convert BGR to RGB (face_recognition uses RGB)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Find all face locations with stricter parameters
        # Using 'cnn' model for better accuracy (slower but more accurate)
        # Fallback to 'hog' if cnn not available
        try:
            face_locations = face_recognition.face_locations(rgb_img, model='cnn', number_of_times_to_upsample=1)
        except:
            face_locations = face_recognition.face_locations(rgb_img, model='hog', number_of_times_to_upsample=1)
        
        face_count = len(face_locations)
        
        # No face detected
        if face_count == 0:
            return {
                'success': False,
                'face_count': 0,
                'message': 'No face detected in the image. Please upload a clear front-facing photo.',
                'encoding': None,
                'confidence': 0.0
            }
        
        # Multiple faces detected - but validate they're real faces
        if face_count > 1:
            # Filter out small/invalid detections
            valid_faces = []
            img_area = img.shape[0] * img.shape[1]
            
            for face_loc in face_locations:
                top, right, bottom, left = face_loc
                face_area = (bottom - top) * (right - left)
                # Face must be at least 2% of image area to be considered valid
                if face_area > (img_area * 0.02):
                    valid_faces.append(face_loc)
            
            if len(valid_faces) > 1:
                return {
                    'success': False,
                    'face_count': len(valid_faces),
                    'message': f'Multiple faces detected ({len(valid_faces)} faces). Please upload an image with only one person.',
                    'encoding': None,
                    'confidence': 0.0
                }
            elif len(valid_faces) == 1:
                face_locations = valid_faces
                face_count = 1
            else:
                return {
                    'success': False,
                    'face_count': 0,
                    'message': 'No valid face detected. Please upload a clearer image.',
                    'encoding': None,
                    'confidence': 0.0
                }
        
        # Exactly one face - generate encoding
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations, num_jitters=2)
        
        if len(face_encodings) > 0:
            encoding = face_encodings[0]
            encoding_json = json.dumps(encoding.tolist())
            
            # Calculate confidence based on face size
            top, right, bottom, left = face_locations[0]
            face_area = (bottom - top) * (right - left)
            img_area = img.shape[0] * img.shape[1]
            confidence = min((face_area / img_area) * 100, 100.0)
            
            return {
                'success': True,
                'face_count': 1,
                'message': 'Face detected successfully with face_recognition!',
                'encoding': encoding_json,
                'confidence': round(confidence, 2)
            }
        else:
            return {
                'success': False,
                'face_count': 1,
                'message': 'Face detected but encoding failed.',
                'encoding': None,
                'confidence': 0.0
            }
    
    except Exception as e:
        return {
            'success': False,
            'face_count': 0,
            'message': f'face_recognition error: {str(e)}',
            'encoding': None,
            'confidence': 0.0
        }


def _detect_with_deepface(img):
    """Detect face using DeepFace (more accurate)"""
    try:
        # Save image temporarily for DeepFace
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            cv2.imwrite(tmp_file.name, img)
            tmp_path = tmp_file.name
        
        try:
            # Extract faces using DeepFace with stricter confidence
            faces = DeepFace.extract_faces(
                img_path=tmp_path,
                detector_backend='opencv',
                enforce_detection=False,
                align=True
            )
            
            # Filter faces with good confidence (>70%)
            valid_faces = [f for f in faces if f.get('confidence', 0) > 0.7]
            
            # If no high-confidence faces, try with lower threshold (>50%)
            if len(valid_faces) == 0:
                valid_faces = [f for f in faces if f.get('confidence', 0) > 0.5]
            
            face_count = len(valid_faces)
            
            # Filter by face size to remove false positives
            if face_count > 1:
                img_area = img.shape[0] * img.shape[1]
                filtered_faces = []
                
                for face in valid_faces:
                    facial_area = face.get('facial_area', {})
                    w = facial_area.get('w', 0)
                    h = facial_area.get('h', 0)
                    face_area = w * h
                    
                    # Face must be at least 3% of image area
                    if face_area > (img_area * 0.03):
                        filtered_faces.append(face)
                
                valid_faces = filtered_faces
                face_count = len(valid_faces)
            
            # No face detected
            if face_count == 0:
                return {
                    'success': False,
                    'face_count': 0,
                    'message': 'No face detected in the image. Please upload a clear front-facing photo.',
                    'encoding': None,
                    'confidence': 0.0
                }
            
            # Multiple faces detected
            if face_count > 1:
                return {
                    'success': False,
                    'face_count': face_count,
                    'message': f'Multiple faces detected ({face_count} faces). Please upload an image with only one person.',
                    'encoding': None,
                    'confidence': 0.0
                }
            
            # Exactly one face - generate embedding using Facenet512
            try:
                embedding_objs = DeepFace.represent(
                    img_path=tmp_path,
                    model_name='Facenet512',
                    detector_backend='opencv',
                    enforce_detection=False,
                    align=True
                )
                
                if embedding_objs and len(embedding_objs) > 0:
                    embedding = embedding_objs[0]['embedding']
                    encoding_json = json.dumps(embedding)
                    
                    # Get confidence from face detection
                    confidence = valid_faces[0].get('confidence', 0.9) * 100
                    
                    return {
                        'success': True,
                        'face_count': 1,
                        'message': 'Face detected successfully with DeepFace!',
                        'encoding': encoding_json,
                        'confidence': round(confidence, 2)
                    }
                else:
                    raise Exception("Could not generate face embedding")
                    
            except Exception as e:
                return {
                    'success': False,
                    'face_count': 1,
                    'message': f'Face detected but encoding failed: {str(e)}',
                    'encoding': None,
                    'confidence': 0.0
                }
        
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        return {
            'success': False,
            'face_count': 0,
            'message': f'DeepFace error: {str(e)}',
            'encoding': None,
            'confidence': 0.0
        }


def _detect_with_opencv(img):
    """Fallback: Detect face using basic OpenCV"""
    try:
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Load Haar Cascade for face detection
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Detect faces with stricter parameters to reduce false positives
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,  # Increased from 1.1 for better accuracy
            minNeighbors=6,   # Increased from 5 to reduce false positives
            minSize=(50, 50), # Increased minimum size
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        face_count = len(faces)
        
        # Filter by face size to remove false positives
        if face_count > 1:
            img_area = img.shape[0] * img.shape[1]
            valid_faces = []
            
            for (x, y, w, h) in faces:
                face_area = w * h
                # Face must be at least 2% of image area
                if face_area > (img_area * 0.02):
                    valid_faces.append((x, y, w, h))
            
            faces = np.array(valid_faces) if valid_faces else np.array([])
            face_count = len(faces)
        
        # No face detected
        if face_count == 0:
            return {
                'success': False,
                'face_count': 0,
                'message': 'No face detected in the image. Please upload a clear front-facing photo.',
                'encoding': None,
                'confidence': 0.0
            }
        
        # Multiple faces detected
        if face_count > 1:
            return {
                'success': False,
                'face_count': face_count,
                'message': f'Multiple faces detected ({face_count} faces). Please upload an image with only one person.',
                'encoding': None,
                'confidence': 0.0
            }
        
        # Exactly one face detected - extract features
        (x, y, w, h) = faces[0]
        
        # Extract face region
        face_roi = gray[y:y+h, x:x+w]
        
        # Resize to standard size for encoding
        face_roi_resized = cv2.resize(face_roi, (128, 128))
        
        # Create a simple feature encoding (flattened normalized pixel values)
        face_features = face_roi_resized.flatten().astype(float)
        face_features = face_features / 255.0  # Normalize
        
        # Convert to list for JSON serialization
        encoding_list = face_features.tolist()
        encoding_json = json.dumps(encoding_list)
        
        # Calculate confidence based on face size
        img_area = img.shape[0] * img.shape[1]
        face_area = w * h
        confidence = min((face_area / img_area) * 100, 100.0)
        
        return {
            'success': True,
            'face_count': 1,
            'message': 'Face detected successfully with OpenCV!',
            'encoding': encoding_json,
            'confidence': round(confidence, 2)
        }
        
    except Exception as e:
        return {
            'success': False,
            'face_count': 0,
            'message': f'OpenCV error: {str(e)}',
            'encoding': None,
            'confidence': 0.0
        }


def compare_faces(encoding1_json, encoding2_json, threshold=0.5):
    """
    Compare two face encodings to check if they match.
    
    Args:
        encoding1_json: JSON string of first face encoding
        encoding2_json: JSON string of second face encoding
        threshold: Similarity threshold (default 0.5 for 50% accuracy)
    
    Returns:
        dict: {'match': bool, 'similarity': float, 'distance': float}
    """
    try:
        # Load encodings
        encoding1 = np.array(json.loads(encoding1_json))
        encoding2 = np.array(json.loads(encoding2_json))
        
        # Determine encoding type by dimension
        if len(encoding1) == 128 and len(encoding2) == 128:
            # face_recognition encodings (128 dimensions)
            return _compare_face_recognition_encodings(encoding1, encoding2, threshold=0.5)
        elif len(encoding1) == 512 and len(encoding2) == 512:
            # DeepFace Facenet512 embeddings (512 dimensions)
            return _compare_deepface_embeddings(encoding1, encoding2, threshold=0.5)
        else:
            # OpenCV basic features (16384 dimensions)
            return _compare_opencv_features(encoding1, encoding2, threshold=0.5)
        
    except Exception as e:
        return {
            'match': False,
            'similarity': 0.0,
            'distance': float('inf'),
            'error': str(e)
        }


def _compare_face_recognition_encodings(enc1, enc2, threshold=0.5):
    """Compare face_recognition encodings using Euclidean distance"""
    try:
        if FACE_RECOGNITION_AVAILABLE:
            # Use face_recognition's built-in comparison
            distance = face_recognition.face_distance([enc1], enc2)[0]
            
            # Convert to similarity (0-1, higher is more similar)
            similarity = 1 - distance
            
            # Match if distance < threshold (default 0.5 for 50% accuracy)
            match = distance < threshold
            
            return {
                'match': match,
                'similarity': round(float(similarity), 4),
                'distance': round(float(distance), 4),
                'method': 'face_recognition-128D'
            }
        else:
            # Fallback to Euclidean distance
            distance = np.linalg.norm(enc1 - enc2)
            similarity = 1.0 / (1.0 + distance)
            match = distance < threshold
            
            return {
                'match': match,
                'similarity': round(float(similarity), 4),
                'distance': round(float(distance), 4),
                'method': 'face_recognition-fallback'
            }
    except Exception as e:
        return {
            'match': False,
            'similarity': 0.0,
            'distance': float('inf'),
            'error': str(e)
        }


def _compare_deepface_embeddings(emb1, emb2, threshold=0.5):
    """Compare DeepFace embeddings using cosine distance"""
    try:
        # Cosine distance
        from numpy.linalg import norm
        cosine_distance = 1 - np.dot(emb1, emb2) / (norm(emb1) * norm(emb2))
        
        # Convert to similarity (0-1, higher is more similar)
        similarity = 1 - cosine_distance
        
        # Match if distance < threshold (0.5 for 50% accuracy)
        match = cosine_distance < threshold
        
        return {
            'match': match,
            'similarity': round(float(similarity), 4),
            'distance': round(float(cosine_distance), 4),
            'method': 'DeepFace-Facenet512'
        }
    except Exception as e:
        return {
            'match': False,
            'similarity': 0.0,
            'distance': float('inf'),
            'error': str(e)
        }


def _compare_opencv_features(feat1, feat2, threshold=0.5):
    """Compare OpenCV features using Euclidean distance"""
    try:
        # Calculate Euclidean distance
        distance = np.linalg.norm(feat1 - feat2)
        
        # Normalize distance to similarity score (0-1)
        similarity = 1.0 / (1.0 + distance)
        
        # Check if faces match (threshold 0.5 for 50% accuracy)
        match = distance < threshold
        
        return {
            'match': match,
            'similarity': round(float(similarity), 4),
            'distance': round(float(distance), 4),
            'method': 'OpenCV-Basic'
        }
    except Exception as e:
        return {
            'match': False,
            'similarity': 0.0,
            'distance': float('inf'),
            'error': str(e)
        }


def verify_faces_with_deepface(img1_path, img2_path):
    """
    Direct DeepFace verification (alternative method)
    Use this for highest accuracy when both images are file paths
    """
    if not DEEPFACE_AVAILABLE:
        return {
            'verified': False,
            'distance': 1.0,
            'message': 'DeepFace not available'
        }
    
    try:
        result = DeepFace.verify(
            img1_path=img1_path,
            img2_path=img2_path,
            model_name='Facenet512',
            detector_backend='opencv',
            distance_metric='cosine',
            enforce_detection=False
        )
        
        return {
            'verified': result['verified'],
            'distance': result['distance'],
            'threshold': result['threshold'],
            'similarity': (1 - result['distance']) * 100,
            'message': 'Verified with DeepFace' if result['verified'] else 'Not verified'
        }
    except Exception as e:
        return {
            'verified': False,
            'distance': 1.0,
            'message': f'Error: {str(e)}'
        }
