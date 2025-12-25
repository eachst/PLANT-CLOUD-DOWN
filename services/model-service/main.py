"""
模型服务主应用
"""
import os
import sys
import logging
import json
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

# 加载环境变量
load_dotenv()

# 配置日志（在导入模型加载器之前）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 尝试导入YAML模块
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError as e:
    logger.warning(f"YAML模块导入失败: {e}，YAML配置文件可能无法使用")
    YAML_AVAILABLE = False
    yaml = None

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import numpy as np
import time

# 添加共享模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from shared.utils.helpers import (
    log_execution_time, redis_set, redis_get, redis_exists,
    upload_file_to_cos, download_file_from_cos, get_file_hash,
    get_current_time, safe_json_dumps, safe_json_loads
)

# 导入模型加载器
sys.path.insert(0, os.path.dirname(__file__))
try:
    from model_loader import (
        load_model_from_file, load_image_from_url, load_image_from_bytes,
        ModelLoader, PyTorchModelLoader, ONNXModelLoader,
        EnsembleModelLoader, DistillationModelLoader, predict_disease
    )
except ImportError as e:
    logger.warning(f"模型加载器导入失败: {e}，某些功能可能不可用")
    # 定义占位符函数
    def load_model_from_file(*args, **kwargs):
        return None
    def load_image_from_url(*args, **kwargs):
        return None
    def load_image_from_bytes(*args, **kwargs):
        return None
    def predict_disease(*args, **kwargs):
        return {"top_prediction": {"plant": "未知", "disease": "未知", "confidence": 0.0}}
    PyTorchModelLoader = None
    ONNXModelLoader = None
    EnsembleModelLoader = None
    DistillationModelLoader = None

# 导入智能路由和图像分割
try:
    from smart_router import SmartRouter
    from image_segmenter import segment_image
    SMART_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"智能路由或图像分割导入失败: {e}，某些功能可能不可用")
    SMART_ROUTER_AVAILABLE = False
    SmartRouter = None
    def segment_image(*args, **kwargs):
        return args[0], None

from shared.schemas.schemas import (
    PredictionRequest, PredictionResult, Model, ModelCreate, ModelUpdate,
    HealthCheck, SuccessResponse, ErrorResponse
)

# 全局变量
app_state: Dict[str, Any] = {
    "models": {},
    "model_configs": {},
    "redis_client": None,
    "smart_router": None,
    "student_model": None,
    "ensemble_model": None,
    "class_names": []
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("模型服务启动中...")
    
    # 初始化Redis连接
    # app_state["redis_client"] = await get_redis_client()
    
    # 加载模型
    await load_models()
    
    logger.info("模型服务启动完成")
    
    yield
    
    # 关闭时执行
    logger.info("模型服务关闭中...")
    
    # 清理资源
    # if app_state["redis_client"]:
    #     await app_state["redis_client"].close()
    
    logger.info("模型服务已关闭")


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="植物病害检测模型服务",
        description="提供植物病害检测模型加载和预测服务",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # 添加中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 添加异常处理器
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                message=exc.detail,
                error_code=f"HTTP_{exc.status_code}"
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                message="服务器内部错误",
                error_code="INTERNAL_SERVER_ERROR"
            ).dict()
        )
    
    # 添加路由
    app.include_router(health_router, prefix="/health", tags=["健康检查"])
    app.include_router(model_router, prefix="/models", tags=["模型管理"])
    app.include_router(prediction_router, prefix="/predictions", tags=["预测服务"])
    app.include_router(prediction_router, prefix="/predict", tags=["预测服务"])
    
    return app



def _get_model_type(loader) -> str:
    """获取模型类型字符串"""
    if loader is None:
        return "unknown"
    if isinstance(loader, PyTorchModelLoader):
        return "pytorch"
    elif isinstance(loader, ONNXModelLoader):
        return "onnx"
    elif isinstance(loader, EnsembleModelLoader):
        return "ensemble"
    elif isinstance(loader, DistillationModelLoader):
        return "distillation"
    else:
        return "unknown"


def _load_config_file(config_path: str) -> Optional[Dict[str, Any]]:
    """加载配置文件（支持JSON和YAML）"""
    if not os.path.exists(config_path):
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            file_ext = os.path.splitext(config_path)[1].lower()
            
            if file_ext in ['.yaml', '.yml']:
                if not YAML_AVAILABLE:
                    logger.error(f"YAML配置文件需要PyYAML库")
                    return None
                return yaml.safe_load(f)
            elif file_ext == '.json':
                return json.load(f)
            else:
                # 尝试自动检测格式
                content = f.read()
                f.seek(0)
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    if YAML_AVAILABLE:
                        return yaml.safe_load(content)
                    else:
                        logger.error(f"无法解析配置文件: {config_path}")
                        return None
    except Exception as e:
        logger.error(f"加载配置文件失败: {config_path}, 错误: {str(e)}")
        return None


async def load_models():
    """加载模型"""
    model_path = os.getenv("MODEL_PATH", "/app/models")
    
    if not os.path.exists(model_path):
        logger.warning(f"模型路径不存在: {model_path}，将创建目录")
        os.makedirs(model_path, exist_ok=True)
        return
    
    try:
        # 检查模型文件
        model_files = [f for f in os.listdir(model_path) if f.endswith(('.pt', '.pth', '.onnx'))]
        
        # 首先检查是否有集成模型或蒸馏模型配置（支持JSON和YAML）
        ensemble_configs = [
            os.path.join(model_path, "ensemble_config.yaml"),
            os.path.join(model_path, "ensemble_config.yml"),
            os.path.join(model_path, "ensemble_config.json")
        ]
        distillation_configs = [
            os.path.join(model_path, "distillation_config.yaml"),
            os.path.join(model_path, "distillation_config.yml"),
            os.path.join(model_path, "distillation_config.json")
        ]
        
        ensemble_config = None
        for config_path in ensemble_configs:
            if os.path.exists(config_path):
                ensemble_config = config_path
                break
        
        distillation_config = None
        for config_path in distillation_configs:
            if os.path.exists(config_path):
                distillation_config = config_path
                break
        
        # 加载集成模型
        if ensemble_config:
            try:
                logger.info(f"检测到集成模型配置，正在加载: {ensemble_config}")
                loader = load_model_from_file(ensemble_config, ensemble_config)
                if loader:
                    app_state["models"]["ensemble"] = loader
                    app_state["ensemble_model"] = loader
                    # 加载配置数据
                    config_data = _load_config_file(ensemble_config)
                    if config_data is None:
                        config_data = {}
                    app_state["model_configs"]["ensemble"] = {
                        "name": "ensemble",
                        "file_path": ensemble_config,
                        "file_size": os.path.getsize(ensemble_config),
                        "loaded_at": get_current_time().isoformat(),
                        "status": "loaded",
                        "model_type": "ensemble",
                        "num_models": len(config_data.get("model_paths", [])),
                        "strategy": config_data.get("ensemble_strategy", "average")
                    }
                    logger.info("集成模型加载成功")
            except Exception as e:
                logger.error(f"加载集成模型失败: {str(e)}")
        
        # 加载蒸馏模型
        if distillation_config:
            try:
                logger.info(f"检测到蒸馏模型配置，正在加载: {distillation_config}")
                loader = load_model_from_file(distillation_config, distillation_config)
                if loader:
                    app_state["models"]["distillation"] = loader
                    # 加载配置数据
                    config_data = _load_config_file(distillation_config)
                    if config_data is None:
                        config_data = {}
                    app_state["model_configs"]["distillation"] = {
                        "name": "distillation",
                        "file_path": distillation_config,
                        "file_size": os.path.getsize(distillation_config),
                        "loaded_at": get_current_time().isoformat(),
                        "status": "loaded",
                        "model_type": "distillation",
                        "student_model": config_data.get("student_model_path", ""),
                        "teacher_models": len(config_data.get("teacher_model_paths", []))
                    }
                    logger.info("蒸馏模型加载成功")
            except Exception as e:
                logger.error(f"加载蒸馏模型失败: {str(e)}")
        
        # 加载单模型
        for model_file in model_files:
            model_name = os.path.splitext(model_file)[0]
            
            # 跳过已经在集成或蒸馏模型中使用的模型
            if model_name in ["ensemble", "distillation"]:
                continue
            
            model_file_path = os.path.join(model_path, model_file)
            
            # 查找配置文件（支持JSON和YAML）
            config_files = [
                os.path.join(model_path, f"{model_name}_config.yaml"),
                os.path.join(model_path, f"{model_name}_config.yml"),
                os.path.join(model_path, f"{model_name}_config.json")
            ]
            config_file = None
            for cf in config_files:
                if os.path.exists(cf):
                    config_file = cf
                    break
            
            # 加载模型
            loader = load_model_from_file(model_file_path, config_file if os.path.exists(config_file) else None)
            
            if loader:
                app_state["models"][model_name] = loader
                
                # 检查是否为学生模型
                if "student" in model_name.lower():
                    app_state["student_model"] = loader
                
                app_state["model_configs"][model_name] = {
                    "name": model_name,
                    "file_path": model_file_path,
                    "file_size": os.path.getsize(model_file_path),
                    "loaded_at": get_current_time().isoformat(),
                    "status": "loaded",
                    "model_type": _get_model_type(loader),
                    "device": str(loader.device) if hasattr(loader, 'device') else "cpu"
                }
                logger.info(f"模型已加载: {model_name} ({app_state['model_configs'][model_name]['model_type']})")
            else:
                app_state["model_configs"][model_name] = {
                    "name": model_name,
                    "file_path": model_file_path,
                    "file_size": os.path.getsize(model_file_path),
                    "loaded_at": get_current_time().isoformat(),
                    "status": "error"
                }
                logger.error(f"模型加载失败: {model_name}")
        
        # 初始化类名（简单示例，实际应从模型配置或文件中加载）
        app_state["class_names"] = [
            "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust", "Apple___healthy",
            "Blueberry___healthy", "Cherry_(including_sour)___Powdery_mildew", "Cherry_(including_sour)___healthy",
            "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot", "Corn_(maize)___Common_rust_",
            "Corn_(maize)___Northern_Leaf_Blight", "Corn_(maize)___healthy", "Grape___Black_rot", "Grape___Esca_(Black_Measles)",
            "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)", "Grape___healthy", "Orange___Haunglongbing_(Citrus_greening)",
            "Peach___Bacterial_spot", "Peach___healthy", "Pepper,_bell___Bacterial_spot", "Pepper,_bell___healthy",
            "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy", "Raspberry___healthy", "Soybean___healthy",
            "Squash___Powdery_mildew", "Strawberry___Leaf_scorch", "Strawberry___healthy", "Tomato___Bacterial_spot",
            "Tomato___Early_blight", "Tomato___Late_blight", "Tomato___Leaf_Mold", "Tomato___Septoria_leaf_spot",
            "Tomato___Spider_mites Two-spotted_spider_mite", "Tomato___Target_Spot", "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
            "Tomato___Tomato_mosaic_virus", "Tomato___healthy"
        ]
        
        # 初始化智能路由
        if SMART_ROUTER_AVAILABLE:
            try:
                app_state["smart_router"] = SmartRouter(
                    student_model=app_state["student_model"],
                    ensemble_model=app_state["ensemble_model"],
                    class_names=app_state["class_names"]
                )
                logger.info("智能路由初始化成功")
            except Exception as e:
                logger.error(f"智能路由初始化失败: {str(e)}")
        
        logger.info(f"共加载 {len([m for m in app_state['models'].values()])} 个模型")
    except Exception as e:
        logger.error(f"加载模型失败: {str(e)}")


# 路由定义
from fastapi import APIRouter

health_router = APIRouter()
model_router = APIRouter()
prediction_router = APIRouter()


@health_router.get("/", response_model=HealthCheck)
@log_execution_time
async def health_check():
    """健康检查"""
    return HealthCheck(
        status="healthy",
        timestamp=get_current_time(),
        service="model-service",
        version="1.0.0",
        dependencies={
            "models": f"{len(app_state['models'])} loaded",
            "redis": "connected" if app_state["redis_client"] else "disconnected"
        }
    )


@model_router.get("/", response_model=Dict[str, Any])
@log_execution_time
async def list_models():
    """列出所有模型"""
    return {
        "models": list(app_state["model_configs"].values()),
        "total": len(app_state["model_configs"])
    }


@model_router.get("/{model_name}", response_model=Dict[str, Any])
@log_execution_time
async def get_model(model_name: str):
    """获取特定模型信息"""
    if model_name not in app_state["model_configs"]:
        raise HTTPException(status_code=404, detail=f"模型 {model_name} 不存在")
    
    return app_state["model_configs"][model_name]


@model_router.post("/", response_model=Dict[str, Any])
@log_execution_time
async def create_model(model: ModelCreate):
    """创建模型记录"""
    # 这里应该实现模型创建逻辑
    # 示例代码
    model_id = len(app_state["model_configs"]) + 1
    model_info = {
        "id": model_id,
        "name": model.name,
        "version": model.version,
        "model_type": model.model_type,
        "description": model.description,
        "file_path": model.file_path,
        "config": model.config,
        "metadata": model.metadata,
        "is_active": model.is_active,
        "created_at": get_current_time().isoformat()
    }
    
    app_state["model_configs"][model.name] = model_info
    
    return {"message": "模型创建成功", "model": model_info}


@model_router.put("/{model_name}", response_model=Dict[str, Any])
@log_execution_time
async def update_model(model_name: str, model_update: ModelUpdate):
    """更新模型信息"""
    if model_name not in app_state["model_configs"]:
        raise HTTPException(status_code=404, detail=f"模型 {model_name} 不存在")
    
    # 更新模型信息
    model_info = app_state["model_configs"][model_name]
    
    if model_update.name is not None:
        model_info["name"] = model_update.name
    if model_update.version is not None:
        model_info["version"] = model_update.version
    if model_update.description is not None:
        model_info["description"] = model_update.description
    if model_update.config is not None:
        model_info["config"] = model_update.config
    if model_update.metadata is not None:
        model_info["metadata"] = model_update.metadata
    if model_update.is_active is not None:
        model_info["is_active"] = model_update.is_active
    
    model_info["updated_at"] = get_current_time().isoformat()
    
    return {"message": "模型更新成功", "model": model_info}


@model_router.delete("/{model_name}", response_model=Dict[str, Any])
@log_execution_time
async def delete_model(model_name: str):
    """删除模型"""
    if model_name not in app_state["model_configs"]:
        raise HTTPException(status_code=404, detail=f"模型 {model_name} 不存在")
    
    # 从内存中卸载模型
    if model_name in app_state["models"]:
        del app_state["models"][model_name]
    
    # 删除模型配置
    del app_state["model_configs"][model_name]
    
    return {"message": f"模型 {model_name} 已删除"}


@prediction_router.post("/", response_model=Dict[str, Any])
@log_execution_time
async def create_prediction(request: PredictionRequest, background_tasks: BackgroundTasks):
    """创建预测任务（异步）"""
    # 验证模型是否存在
    model_name = request.model_name or "default"
    if model_name not in app_state["model_configs"]:
        raise HTTPException(status_code=404, detail=f"模型 {model_name} 不存在")
    
    if model_name not in app_state["models"]:
        raise HTTPException(status_code=500, detail=f"模型 {model_name} 未正确加载")
    
    task_id = f"pred_{get_current_time().strftime('%Y%m%d%H%M%S')}_{os.getpid()}"
    
    # 缓存预测请求
    prediction_data = {
        "task_id": task_id,
        "image_url": request.image_url,
        "model_name": model_name,
        "model_id": request.model_id,
        "confidence_threshold": request.confidence_threshold or 0.5,
        "status": "pending",
        "created_at": get_current_time().isoformat()
    }
    
    try:
        await redis_set(f"prediction:{task_id}", prediction_data, expire=3600)
    except Exception as e:
        logger.warning(f"缓存预测请求失败: {str(e)}")
    
    # 添加后台任务执行预测
    background_tasks.add_task(execute_prediction, task_id, prediction_data)
    
    return {
        "message": "预测任务已创建",
        "task_id": task_id,
        "status": "pending"
    }


@prediction_router.post("/smart", response_model=Dict[str, Any])
@log_execution_time
async def smart_prediction(
    file: UploadFile = File(...),
    device_info: str = Form(""),
    use_segmentation: bool = Form(True)
):
    """使用智能路由进行预测"""
    if SMART_ROUTER_AVAILABLE and app_state.get("smart_router"):
        try:
            # 读取图像
            image_bytes = await file.read()
            image = load_image_from_bytes(image_bytes)
            
            if image is None:
                raise HTTPException(status_code=400, detail="无法解析图像文件")
            
            # 图像预处理
            if use_segmentation:
                image, _ = segment_image(image)
            
            # 使用智能路由预测
            result = app_state["smart_router"].smart_predict(image, device_info)
            
            return {
                "success": True,
                "result": result,
                "message": "智能预测成功"
            }
        except Exception as e:
            logger.error(f"智能预测失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"智能预测失败: {str(e)}")
    else:
        raise HTTPException(status_code=503, detail="智能路由不可用")


@prediction_router.post("/student", response_model=Dict[str, Any])
@log_execution_time
async def student_prediction(
    file: UploadFile = File(...),
    use_segmentation: bool = Form(True),
    confidence_threshold: float = Form(0.5)
):
    """使用学生模型进行预测"""
    student_model = app_state.get("student_model")
    if not student_model:
        raise HTTPException(status_code=503, detail="学生模型未加载")
    
    try:
        # 读取图像
        image_bytes = await file.read()
        image = load_image_from_bytes(image_bytes)
        
        if image is None:
            raise HTTPException(status_code=400, detail="无法解析图像文件")
        
        # 图像预处理
        if use_segmentation:
            image, _ = segment_image(image)
        
        # 使用学生模型预测
        result = predict_disease(student_model, image, app_state["class_names"], student_model.device)
        result["model_type"] = "student"
        
        return {
            "success": True,
            "result": result,
            "message": "学生模型预测成功"
        }
    except Exception as e:
        logger.error(f"学生模型预测失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"学生模型预测失败: {str(e)}")


@prediction_router.post("/ensemble", response_model=Dict[str, Any])
@log_execution_time
async def ensemble_prediction(
    file: UploadFile = File(...),
    use_segmentation: bool = Form(True),
    confidence_threshold: float = Form(0.5)
):
    """使用集成模型进行预测"""
    ensemble_model = app_state.get("ensemble_model")
    if not ensemble_model:
        raise HTTPException(status_code=503, detail="集成模型未加载")
    
    try:
        # 读取图像
        image_bytes = await file.read()
        image = load_image_from_bytes(image_bytes)
        
        if image is None:
            raise HTTPException(status_code=400, detail="无法解析图像文件")
        
        # 图像预处理
        if use_segmentation:
            image, _ = segment_image(image)
        
        # 使用集成模型预测
        result = predict_disease(ensemble_model, image, app_state["class_names"], ensemble_model.device)
        result["model_type"] = "ensemble"
        
        return {
            "success": True,
            "result": result,
            "message": "集成模型预测成功"
        }
    except Exception as e:
        logger.error(f"集成模型预测失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"集成模型预测失败: {str(e)}")


@prediction_router.get("/router_stats", response_model=Dict[str, Any])
@log_execution_time
async def get_router_stats():
    """获取智能路由统计信息"""
    if SMART_ROUTER_AVAILABLE and app_state.get("smart_router"):
        return app_state["smart_router"].get_stats()
    else:
        raise HTTPException(status_code=503, detail="智能路由不可用")


@prediction_router.post("/direct", response_model=Dict[str, Any])
@log_execution_time
async def direct_prediction(
    file: UploadFile = File(...),
    model_name: str = Form("default"),
    confidence_threshold: float = Form(0.5)
):
    """直接预测（同步）"""
    # 验证模型
    if model_name not in app_state["models"]:
        raise HTTPException(status_code=404, detail=f"模型 {model_name} 不存在或未加载")
    
    try:
        # 读取图像
        image_bytes = await file.read()
        image = load_image_from_bytes(image_bytes)
        
        if image is None:
            raise HTTPException(status_code=400, detail="无法解析图像文件")
        
        # 获取模型
        model_loader = app_state["models"][model_name]
        
        # 执行预测
        start_time = time.time()
        result = model_loader.predict(image, confidence_threshold)
        processing_time = time.time() - start_time
        
        return {
            "success": True,
            "predictions": result["predictions"],
            "top_prediction": result["top_prediction"],
            "processing_time": processing_time,
            "model_name": model_name
        }
    except Exception as e:
        logger.error(f"直接预测失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


async def execute_prediction(task_id: str, prediction_data: Dict[str, Any]):
    """执行预测任务"""
    try:
        # 更新任务状态为处理中
        prediction_data["status"] = "processing"
        prediction_data["started_at"] = get_current_time().isoformat()
        try:
            await redis_set(f"prediction:{task_id}", prediction_data, expire=3600)
        except Exception as e:
            logger.warning(f"更新任务状态失败: {str(e)}")
        
        # 下载图像
        image = load_image_from_url(prediction_data["image_url"])
        if image is None:
            raise Exception("图像下载失败")
        
        # 执行预测
        model_name = prediction_data["model_name"]
        model_loader = app_state["models"].get(model_name)
        if not model_loader:
            raise Exception(f"模型 {model_name} 未加载")
        
        # 执行预测
        start_time = time.time()
        result = model_loader.predict(image, prediction_data.get("confidence_threshold", 0.5))
        processing_time = time.time() - start_time
        
        # 更新任务状态为完成
        prediction_data["status"] = "completed"
        prediction_data["completed_at"] = get_current_time().isoformat()
        prediction_data["predictions"] = result["predictions"]
        prediction_data["top_prediction"] = result["top_prediction"]
        prediction_data["processing_time"] = processing_time
        
        try:
            await redis_set(f"prediction:{task_id}", prediction_data, expire=3600)
        except Exception as e:
            logger.warning(f"保存预测结果失败: {str(e)}")
        
        logger.info(f"预测任务 {task_id} 完成，耗时: {processing_time:.2f}秒")
    except Exception as e:
        # 更新任务状态为失败
        prediction_data["status"] = "failed"
        prediction_data["error_message"] = str(e)
        prediction_data["completed_at"] = get_current_time().isoformat()
        
        try:
            await redis_set(f"prediction:{task_id}", prediction_data, expire=3600)
        except Exception as redis_error:
            logger.warning(f"保存错误信息失败: {str(redis_error)}")
        
        logger.error(f"预测任务 {task_id} 失败: {str(e)}")


@prediction_router.get("/{task_id}", response_model=Dict[str, Any])
@log_execution_time
async def get_prediction(task_id: str):
    """获取预测结果"""
    try:
        prediction_data = await redis_get(f"prediction:{task_id}")
        if not prediction_data:
            raise HTTPException(status_code=404, detail=f"预测任务 {task_id} 不存在")
        
        return prediction_data
    except Exception as e:
        logger.error(f"获取预测结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取预测结果失败: {str(e)}")


@prediction_router.delete("/{task_id}", response_model=Dict[str, Any])
@log_execution_time
async def delete_prediction(task_id: str):
    """删除预测结果"""
    # 检查预测任务是否存在
    # exists = await redis_exists(f"prediction:{task_id}")
    # if not exists:
    #     raise HTTPException(status_code=404, detail=f"预测任务 {task_id} 不存在")
    
    # 删除预测结果
    # await redis_delete(f"prediction:{task_id}")
    
    return {"message": f"预测任务 {task_id} 已删除"}


# 创建应用实例（必须在所有路由定义之后）
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )