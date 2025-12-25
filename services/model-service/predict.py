"""
预测API端点 - 支持直接预测
"""
from fastapi import APIRouter, File, UploadFile, Form
from typing import Optional
import logging

logger = logging.getLogger(__name__)

predict_router = APIRouter()


@predict_router.post("/")
async def predict(
    file: UploadFile = File(...),
    model_name: str = Form("default"),
    confidence_threshold: float = Form(0.5)
):
    """直接预测接口"""
    # 这个接口已经在main.py中实现
    pass

