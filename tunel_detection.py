"""InsightFace ArcFace face detection + 512-dim embeddings.

Sprint 3 / Tier 3 upgrade: substitui Haar Cascades + histogram embedding
pelo stack ArcFace (buffalo_l). Embedding 512-dim normalizado, cos-sim real.

Auto-downloads buffalo_l model on first use (~80MB). Modelo cacheado em
~/.insightface/models/ entre cold-starts (volume persistente no Render se
configurado; senão re-download por boot — aceitavel).

FALLBACK: se insightface/onnxruntime falhar ao importar OU init falhar
(OOM no Render free tier é o risco principal), cai pra tunel_detection_legacy
(Haar + histogram 128-dim). Produção NUNCA quebra; embeddings novos viram
'arcface_buffalo_l_v1', antigos continuam 'opencv_hist_v1'.
"""

import os
import numpy as np
from typing import List, Dict

_face_analyzer = None
_init_attempted = False


def get_face_analyzer():
    """Lazy init do InsightFace. Cacheia o resultado (inclusive None se falhar)."""
    global _face_analyzer, _init_attempted
    if _init_attempted:
        return _face_analyzer
    _init_attempted = True
    try:
        import insightface  # noqa: F401
        from insightface.app import FaceAnalysis
        _face_analyzer = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        _face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
    except Exception as e:
        print(f"[WARN] InsightFace init failed: {e}, falling back to OpenCV")
        _face_analyzer = None
    return _face_analyzer


def detect_faces_v2(image_path: str) -> List[Dict]:
    """Try InsightFace, fall back to OpenCV Haar if unavailable."""
    analyzer = get_face_analyzer()
    if analyzer is None:
        from tunel_detection_legacy import detect_faces, compute_simple_embedding
        faces = detect_faces(image_path)
        for f in faces:
            bbox = (f['bbox_x'], f['bbox_y'], f['bbox_w'], f['bbox_h'])
            f['embedding'] = compute_simple_embedding(image_path, bbox)
            f['embedding_model'] = 'opencv_hist_v1'
        return faces

    import cv2
    img = cv2.imread(image_path)
    if img is None:
        return []
    faces = analyzer.get(img)
    results = []
    for i, f in enumerate(faces):
        bbox = f.bbox.astype(int)
        results.append({
            'face_index': i,
            'bbox_x': int(bbox[0]),
            'bbox_y': int(bbox[1]),
            'bbox_w': int(bbox[2] - bbox[0]),
            'bbox_h': int(bbox[3] - bbox[1]),
            'confidence': float(f.det_score),
            'embedding': f.normed_embedding.tolist(),  # 512-dim ArcFace, L2-normalized
            'embedding_model': 'arcface_buffalo_l_v1',
        })
    return results


def process_upload(image_path: str) -> Dict:
    """Pipeline: detect + embed. Compatível com a assinatura legacy."""
    faces = detect_faces_v2(image_path)
    return {
        'faces_detected': len(faces),
        'faces': faces,
    }


# Backwards-compat shims: alguns callers chamam detect_faces / compute_simple_embedding
# diretamente. Redirecionamos pro caminho v2 (que já faz embedding inline).
def detect_faces(image_path: str) -> List[Dict]:
    """Compat shim — agora delega pro detect_faces_v2 (que já inclui embedding)."""
    return detect_faces_v2(image_path)


def compute_simple_embedding(image_path: str, bbox):
    """Compat shim. ArcFace exige a face inteira processada — recortar manualmente
    perderia o pipeline de alinhamento. Caímos no legacy histogram se chamado."""
    from tunel_detection_legacy import compute_simple_embedding as _legacy
    return _legacy(image_path, bbox)
