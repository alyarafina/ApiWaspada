from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import uuid
from PIL import Image
from ..config import settings
from ..services.ai_service import detector
router=APIRouter(prefix='/api/detect',tags=['AI Detection'])
@router.get('/status')
def status(): return detector.status()
@router.post('')
def detect(image:UploadFile=File(...)):
    if image.content_type not in ('image/jpeg','image/png'): raise HTTPException(415,'Gunakan gambar JPG atau PNG.')
    name=f'{uuid.uuid4()}.jpg'; path=Path(settings.upload_dir)/name; path.parent.mkdir(parents=True,exist_ok=True)
    data=image.file.read(settings.max_upload_mb*1024*1024+1)
    if len(data)>settings.max_upload_mb*1024*1024: raise HTTPException(413,'Ukuran file terlalu besar.')
    path.write_bytes(data)
    try:
        with Image.open(path) as im: im.verify()
        out=Path(settings.result_dir)/(path.stem+'_detected.jpg'); result=detector.predict(str(path),str(out))
        return result
    except Exception as exc: raise HTTPException(400,f'Gambar tidak dapat diproses: {exc}')
    finally: path.unlink(missing_ok=True)
