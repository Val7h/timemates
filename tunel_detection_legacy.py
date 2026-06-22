"""Face detection for Túnel do Tempo. Uses OpenCV Haar Cascades (no dlib needed).

Decisão: opencv-python-headless ao invés de face_recognition.
Motivo: face_recognition exige dlib, que compila com cmake/boost no Render
(build ~1.5GB, frequentemente estoura free tier). Haar Cascades vêm pré-treinados
no pacote cv2, zero compilação, deploy instantâneo.

Trade-off: Haar não dá embedding facial verdadeiro nem confidence real. Mitigamos
com histogram-based embedding (128-dim) — suficiente pra clustering inicial e
match heurístico. Em produção, trocar por FaceNet/ArcFace via ONNX runtime.
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple
import os
import logging

logger = logging.getLogger(__name__)

# Cascade carregado on-demand (evita custo no import)
_cascade = None


def get_face_cascade():
    """Lazy load do Haar Cascade pré-treinado que vem no cv2."""
    global _cascade
    if _cascade is None:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        _cascade = cv2.CascadeClassifier(cascade_path)
        if _cascade.empty():
            logger.error(f"Falha ao carregar cascade de {cascade_path}")
    return _cascade


def detect_faces(image_path: str) -> List[Dict]:
    """Detecta faces, retorna lista de {face_index, bbox_x, bbox_y, bbox_w, bbox_h, confidence}."""
    if not os.path.exists(image_path):
        logger.warning(f"Arquivo não existe: {image_path}")
        return []

    img = cv2.imread(image_path)
    if img is None:
        logger.warning(f"cv2.imread retornou None pra: {image_path}")
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = get_face_cascade()
    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40),
    )

    results = []
    for i, (x, y, w, h) in enumerate(faces):
        results.append({
            'face_index': i,
            'bbox_x': int(x),
            'bbox_y': int(y),
            'bbox_w': int(w),
            'bbox_h': int(h),
            'confidence': 0.85,  # Haar não expõe confidence real; valor heurístico
        })
    return results


def compute_simple_embedding(image_path: str, bbox: Tuple[int, int, int, int]) -> List[float]:
    """
    Embedding leve baseado em histograma de intensidade do recorte facial.

    Para produção real, trocar por modelo deep learning (FaceNet/ArcFace via ONNX).
    Por enquanto: 128-dim histogram-based embedding, normalizado pra soma=1.
    Suficiente pra clustering inicial de "fotos parecidas do mesmo evento".
    """
    img = cv2.imread(image_path)
    if img is None:
        return []
    x, y, w, h = bbox
    face = img[y:y + h, x:x + w]
    if face.size == 0:
        return []
    face_resized = cv2.resize(face, (64, 64))
    face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
    # Histograma de 128 bins, normalizado
    hist = cv2.calcHist([face_gray], [0], None, [128], [0, 256])
    hist = hist.flatten()
    if hist.sum() > 0:
        hist = hist / hist.sum()
    return hist.tolist()


def process_upload(image_path: str) -> Dict:
    """Pipeline completo: detect + embed pra cada face encontrada."""
    faces = detect_faces(image_path)
    for f in faces:
        bbox = (f['bbox_x'], f['bbox_y'], f['bbox_w'], f['bbox_h'])
        f['embedding'] = compute_simple_embedding(image_path, bbox)
        f['embedding_model'] = 'opencv_hist_v1'
    return {
        'faces_detected': len(faces),
        'faces': faces,
    }
