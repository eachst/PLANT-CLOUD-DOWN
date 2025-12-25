"""
深度学习模型加载器
支持PyTorch和ONNX模型
"""
import os
import logging
import torch
import torch.nn as nn
import onnxruntime as ort
import numpy as np
from PIL import Image
import cv2
from typing import Dict, Any, Optional, List, Tuple
import json

# YAML支持
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logging.warning("PyYAML未安装，YAML配置文件将不可用")

logger = logging.getLogger(__name__)


class ModelLoader:
    """模型加载器基类"""
    
    def __init__(self, model_path: str, model_config: Dict[str, Any]):
        self.model_path = model_path
        self.model_config = model_config
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.is_loaded = False
        
    def load(self) -> bool:
        """加载模型"""
        raise NotImplementedError
        
    def predict(self, image: np.ndarray) -> Dict[str, Any]:
        """预测"""
        raise NotImplementedError
        
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """预处理图像"""
        raise NotImplementedError
        
    def postprocess(self, output: np.ndarray) -> Dict[str, Any]:
        """后处理输出"""
        raise NotImplementedError


class PyTorchModelLoader(ModelLoader):
    """PyTorch模型加载器"""
    
    def __init__(self, model_path: str, model_config: Dict[str, Any]):
        super().__init__(model_path, model_config)
        self.input_size = model_config.get("input_size", (224, 224))
        self.mean = model_config.get("mean", [0.485, 0.456, 0.406])
        self.std = model_config.get("std", [0.229, 0.224, 0.225])
        self.class_names = model_config.get("class_names", [])
        
    def load(self) -> bool:
        """加载PyTorch模型"""
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"模型文件不存在: {self.model_path}")
                return False
                
            # 加载模型
            if self.device.type == "cuda":
                self.model = torch.load(self.model_path, map_location=self.device)
            else:
                self.model = torch.load(self.model_path, map_location="cpu")
            
            self.model.eval()
            self.is_loaded = True
            logger.info(f"PyTorch模型加载成功: {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"加载PyTorch模型失败: {str(e)}")
            return False
    
    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        """预处理图像"""
        # 调整大小
        image = cv2.resize(image, self.input_size)
        
        # 转换为RGB
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        else:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 归一化
        image = image.astype(np.float32) / 255.0
        image = (image - np.array(self.mean)) / np.array(self.std)
        
        # 转换为CHW格式
        image = image.transpose(2, 0, 1)
        
        # 添加batch维度
        image = torch.from_numpy(image).unsqueeze(0)
        
        return image.to(self.device)
    
    def postprocess(self, output: torch.Tensor, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """后处理输出"""
        # 应用softmax
        probabilities = torch.nn.functional.softmax(output, dim=1)
        
        # 获取top-k结果
        top_k = min(5, len(self.class_names))
        top_probs, top_indices = torch.topk(probabilities, top_k)
        
        results = []
        for i in range(top_k):
            idx = top_indices[0][i].item()
            prob = top_probs[0][i].item()
            
            if prob >= confidence_threshold:
                class_name = self.class_names[idx] if idx < len(self.class_names) else f"class_{idx}"
                results.append({
                    "class": class_name,
                    "confidence": float(prob),
                    "class_id": int(idx)
                })
        
        return {
            "predictions": results,
            "top_prediction": results[0] if results else None
        }
    
    def predict(self, image: np.ndarray, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """预测"""
        if not self.is_loaded:
            raise RuntimeError("模型未加载")
        
        # 预处理
        input_tensor = self.preprocess(image)
        
        # 推理
        with torch.no_grad():
            output = self.model(input_tensor)
        
        # 后处理
        result = self.postprocess(output, confidence_threshold)
        
        return result


class ONNXModelLoader(ModelLoader):
    """ONNX模型加载器"""
    
    def __init__(self, model_path: str, model_config: Dict[str, Any]):
        super().__init__(model_path, model_config)
        self.input_size = model_config.get("input_size", (224, 224))
        self.mean = model_config.get("mean", [0.485, 0.456, 0.406])
        self.std = model_config.get("std", [0.229, 0.224, 0.225])
        self.class_names = model_config.get("class_names", [])
        self.session = None
        
    def load(self) -> bool:
        """加载ONNX模型"""
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"模型文件不存在: {self.model_path}")
                return False
            
            # 创建ONNX Runtime会话
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if torch.cuda.is_available() else ['CPUExecutionProvider']
            self.session = ort.InferenceSession(
                self.model_path,
                providers=providers
            )
            
            self.is_loaded = True
            logger.info(f"ONNX模型加载成功: {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"加载ONNX模型失败: {str(e)}")
            return False
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """预处理图像"""
        # 调整大小
        image = cv2.resize(image, self.input_size)
        
        # 转换为RGB
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        else:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 归一化
        image = image.astype(np.float32) / 255.0
        image = (image - np.array(self.mean)) / np.array(self.std)
        
        # 转换为CHW格式
        image = image.transpose(2, 0, 1)
        
        # 添加batch维度
        image = np.expand_dims(image, axis=0)
        
        return image
    
    def postprocess(self, output: np.ndarray, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """后处理输出"""
        # 应用softmax
        exp_output = np.exp(output - np.max(output))
        probabilities = exp_output / np.sum(exp_output)
        
        # 获取top-k结果
        top_k = min(5, len(self.class_names))
        top_indices = np.argsort(probabilities[0])[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            prob = float(probabilities[0][idx])
            
            if prob >= confidence_threshold:
                class_name = self.class_names[idx] if idx < len(self.class_names) else f"class_{idx}"
                results.append({
                    "class": class_name,
                    "confidence": prob,
                    "class_id": int(idx)
                })
        
        return {
            "predictions": results,
            "top_prediction": results[0] if results else None
        }
    
    def predict(self, image: np.ndarray, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """预测"""
        if not self.is_loaded:
            raise RuntimeError("模型未加载")
        
        # 预处理
        input_array = self.preprocess(image)
        
        # 获取输入名称
        input_name = self.session.get_inputs()[0].name
        
        # 推理
        outputs = self.session.run(None, {input_name: input_array})
        output = outputs[0]
        
        # 后处理
        result = self.postprocess(output, confidence_threshold)
        
        return result


def load_config_file(config_path: str) -> Optional[Dict[str, Any]]:
    """加载配置文件（支持JSON和YAML）"""
    if not os.path.exists(config_path):
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            file_ext = os.path.splitext(config_path)[1].lower()
            
            if file_ext in ['.yaml', '.yml']:
                if not YAML_AVAILABLE:
                    logger.error(f"YAML配置文件需要PyYAML库，请安装: pip install pyyaml")
                    return None
                config = yaml.safe_load(f)
            elif file_ext == '.json':
                config = json.load(f)
            else:
                # 尝试自动检测格式
                content = f.read()
                f.seek(0)
                try:
                    # 先尝试JSON
                    config = json.loads(content)
                except json.JSONDecodeError:
                    # 再尝试YAML
                    if YAML_AVAILABLE:
                        config = yaml.safe_load(content)
                    else:
                        logger.error(f"无法解析配置文件: {config_path}")
                        return None
            
            return config if config else {}
    except Exception as e:
        logger.error(f"加载配置文件失败: {config_path}, 错误: {str(e)}")
        return None


class EnsembleModelLoader(ModelLoader):
    """集成模型加载器 - 支持多个模型的集成预测"""
    
    def __init__(self, model_paths: List[str], model_config: Dict[str, Any]):
        # 使用第一个模型路径作为主路径
        super().__init__(model_paths[0] if model_paths else "", model_config)
        self.model_paths = model_paths
        self.models = []  # 存储多个模型加载器
        self.ensemble_strategy = model_config.get("ensemble_strategy", "average")  # average, voting, weighted
        self.weights = model_config.get("weights", None)  # 加权平均的权重
        self.input_size = model_config.get("input_size", (224, 224))
        self.mean = model_config.get("mean", [0.485, 0.456, 0.406])
        self.std = model_config.get("std", [0.229, 0.224, 0.225])
        self.class_names = model_config.get("class_names", [])
        
    def load(self) -> bool:
        """加载所有集成模型"""
        try:
            if not self.model_paths:
                logger.error("集成模型路径列表为空")
                return False
            
            # 加载所有模型
            for i, model_path in enumerate(self.model_paths):
                if not os.path.exists(model_path):
                    logger.error(f"集成模型文件不存在: {model_path}")
                    continue
                
                # 根据文件扩展名选择加载器
                file_ext = os.path.splitext(model_path)[1].lower()
                model_config = self.model_config.copy()
                
                if file_ext in ['.pt', '.pth']:
                    loader = PyTorchModelLoader(model_path, model_config)
                elif file_ext == '.onnx':
                    loader = ONNXModelLoader(model_path, model_config)
                else:
                    logger.warning(f"不支持的模型格式: {file_ext}, 跳过: {model_path}")
                    continue
                
                if loader.load():
                    self.models.append(loader)
                    logger.info(f"集成模型 {i+1}/{len(self.model_paths)} 加载成功: {model_path}")
                else:
                    logger.warning(f"集成模型 {i+1}/{len(self.model_paths)} 加载失败: {model_path}")
            
            if not self.models:
                logger.error("没有成功加载任何集成模型")
                return False
            
            # 归一化权重
            if self.weights and len(self.weights) == len(self.models):
                total_weight = sum(self.weights)
                self.weights = [w / total_weight for w in self.weights]
            elif self.ensemble_strategy == "weighted":
                # 如果没有提供权重，使用均匀权重
                self.weights = [1.0 / len(self.models)] * len(self.models)
                logger.warning("加权集成策略但未提供权重，使用均匀权重")
            
            self.is_loaded = True
            logger.info(f"集成模型加载完成，共 {len(self.models)} 个模型，策略: {self.ensemble_strategy}")
            return True
        except Exception as e:
            logger.error(f"加载集成模型失败: {str(e)}")
            return False
    
    def preprocess(self, image: np.ndarray) -> Any:
        """预处理图像（使用第一个模型的预处理方法）"""
        if not self.models:
            raise RuntimeError("没有可用的模型")
        return self.models[0].preprocess(image)
    
    def _ensemble_average(self, outputs: List[Any]) -> np.ndarray:
        """平均策略：对多个模型的输出求平均"""
        if isinstance(outputs[0], torch.Tensor):
            # PyTorch张量
            stacked = torch.stack(outputs)
            averaged = torch.mean(stacked, dim=0)
            return averaged.cpu().numpy()
        else:
            # NumPy数组
            stacked = np.stack(outputs)
            averaged = np.mean(stacked, axis=0)
            return averaged
    
    def _ensemble_weighted_average(self, outputs: List[Any]) -> np.ndarray:
        """加权平均策略"""
        if not self.weights:
            return self._ensemble_average(outputs)
        
        if isinstance(outputs[0], torch.Tensor):
            # PyTorch张量
            weighted_sum = sum(w * out for w, out in zip(self.weights, outputs))
            return weighted_sum.cpu().numpy()
        else:
            # NumPy数组
            weighted_sum = sum(w * out for w, out in zip(self.weights, outputs))
            return weighted_sum
    
    def _ensemble_voting(self, outputs: List[Any]) -> np.ndarray:
        """投票策略：每个模型投票，选择得票最多的类别"""
        # 先转换为概率
        probabilities_list = []
        for output in outputs:
            if isinstance(output, torch.Tensor):
                prob = torch.nn.functional.softmax(output, dim=1).cpu().numpy()[0]
            else:
                exp_output = np.exp(output - np.max(output))
                prob = exp_output / np.sum(exp_output)
                prob = prob[0]
            probabilities_list.append(prob)
        
        # 投票：每个模型选择最高概率的类别
        votes = np.zeros(len(self.class_names) if self.class_names else probabilities_list[0].shape[0])
        for prob in probabilities_list:
            top_class = np.argmax(prob)
            votes[top_class] += 1
        
        # 归一化为概率
        total_votes = len(probabilities_list)
        final_prob = votes / total_votes
        
        # 转换为与原始输出相同的形状
        return np.expand_dims(final_prob, axis=0)
    
    def postprocess(self, ensemble_output: np.ndarray, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """后处理集成输出"""
        # 应用softmax
        if isinstance(ensemble_output, torch.Tensor):
            probabilities = torch.nn.functional.softmax(ensemble_output, dim=1)
            probs_array = probabilities[0].cpu().numpy()
        else:
            exp_output = np.exp(ensemble_output - np.max(ensemble_output))
            probabilities = exp_output / np.sum(exp_output)
            probs_array = probabilities[0]
        
        # 获取top-k结果
        top_k = min(5, len(self.class_names) if self.class_names else len(probs_array))
        top_indices = np.argsort(probs_array)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            prob = float(probs_array[idx])
            
            if prob >= confidence_threshold:
                class_name = self.class_names[idx] if self.class_names and idx < len(self.class_names) else f"class_{idx}"
                results.append({
                    "class": class_name,
                    "confidence": prob,
                    "class_id": int(idx)
                })
        
        return {
            "predictions": results,
            "top_prediction": results[0] if results else None,
            "ensemble_info": {
                "num_models": len(self.models),
                "strategy": self.ensemble_strategy
            }
        }
    
    def predict(self, image: np.ndarray, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """集成预测"""
        if not self.is_loaded:
            raise RuntimeError("集成模型未加载")
        
        if not self.models:
            raise RuntimeError("没有可用的模型")
        
        # 预处理（使用第一个模型）
        preprocessed = self.preprocess(image)
        
        # 所有模型进行预测
        outputs = []
        for i, model in enumerate(self.models):
            try:
                if isinstance(model, PyTorchModelLoader):
                    with torch.no_grad():
                        if isinstance(preprocessed, torch.Tensor):
                            output = model.model(preprocessed)
                        else:
                            # 如果预处理返回numpy，需要转换
                            input_tensor = torch.from_numpy(preprocessed).to(model.device)
                            output = model.model(input_tensor)
                    outputs.append(output)
                elif isinstance(model, ONNXModelLoader):
                    input_array = preprocessed if isinstance(preprocessed, np.ndarray) else preprocessed.cpu().numpy()
                    input_name = model.session.get_inputs()[0].name
                    output = model.session.run(None, {input_name: input_array})[0]
                    outputs.append(output)
                else:
                    # 使用模型的predict方法
                    result = model.predict(image, confidence_threshold)
                    # 提取原始输出（需要根据实际情况调整）
                    outputs.append(result)
            except Exception as e:
                logger.error(f"模型 {i+1} 预测失败: {str(e)}")
                continue
        
        if not outputs:
            raise RuntimeError("所有模型预测都失败")
        
        # 集成策略
        if self.ensemble_strategy == "average":
            ensemble_output = self._ensemble_average(outputs)
        elif self.ensemble_strategy == "weighted":
            ensemble_output = self._ensemble_weighted_average(outputs)
        elif self.ensemble_strategy == "voting":
            ensemble_output = self._ensemble_voting(outputs)
        else:
            logger.warning(f"未知的集成策略: {self.ensemble_strategy}，使用平均策略")
            ensemble_output = self._ensemble_average(outputs)
        
        # 后处理
        result = self.postprocess(ensemble_output, confidence_threshold)
        
        return result


class DistillationModelLoader(ModelLoader):
    """蒸馏模型加载器 - 支持教师模型和学生模型"""
    
    def __init__(self, student_model_path: str, teacher_model_paths: Optional[List[str]], model_config: Dict[str, Any]):
        super().__init__(student_model_path, model_config)
        self.student_model_path = student_model_path
        self.teacher_model_paths = teacher_model_paths or []
        self.student_model = None
        self.teacher_models = []
        self.use_teacher = model_config.get("use_teacher", False)  # 是否使用教师模型辅助
        self.temperature = model_config.get("temperature", 4.0)  # 蒸馏温度
        self.input_size = model_config.get("input_size", (224, 224))
        self.mean = model_config.get("mean", [0.485, 0.456, 0.406])
        self.std = model_config.get("std", [0.229, 0.224, 0.225])
        self.class_names = model_config.get("class_names", [])
        
    def load(self) -> bool:
        """加载学生模型和可选的教师模型"""
        try:
            # 加载学生模型
            if not os.path.exists(self.student_model_path):
                logger.error(f"学生模型文件不存在: {self.student_model_path}")
                return False
            
            file_ext = os.path.splitext(self.student_model_path)[1].lower()
            if file_ext in ['.pt', '.pth']:
                self.student_model = PyTorchModelLoader(self.student_model_path, self.model_config)
            elif file_ext == '.onnx':
                self.student_model = ONNXModelLoader(self.student_model_path, self.model_config)
            else:
                logger.error(f"不支持的学生模型格式: {file_ext}")
                return False
            
            if not self.student_model.load():
                logger.error("学生模型加载失败")
                return False
            
            logger.info(f"学生模型加载成功: {self.student_model_path}")
            
            # 可选：加载教师模型
            if self.use_teacher and self.teacher_model_paths:
                for teacher_path in self.teacher_model_paths:
                    if not os.path.exists(teacher_path):
                        logger.warning(f"教师模型文件不存在: {teacher_path}")
                        continue
                    
                    file_ext = os.path.splitext(teacher_path)[1].lower()
                    if file_ext in ['.pt', '.pth']:
                        teacher_model = PyTorchModelLoader(teacher_path, self.model_config)
                    elif file_ext == '.onnx':
                        teacher_model = ONNXModelLoader(teacher_path, self.model_config)
                    else:
                        logger.warning(f"不支持的教师模型格式: {file_ext}")
                        continue
                    
                    if teacher_model.load():
                        self.teacher_models.append(teacher_model)
                        logger.info(f"教师模型加载成功: {teacher_path}")
            
            self.is_loaded = True
            logger.info(f"蒸馏模型加载完成，学生模型: 1个，教师模型: {len(self.teacher_models)}个")
            return True
        except Exception as e:
            logger.error(f"加载蒸馏模型失败: {str(e)}")
            return False
    
    def predict(self, image: np.ndarray, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """使用学生模型进行预测（可选使用教师模型辅助）"""
        if not self.is_loaded:
            raise RuntimeError("蒸馏模型未加载")
        
        # 使用学生模型进行预测
        result = self.student_model.predict(image, confidence_threshold)
        
        # 如果启用教师模型，可以添加额外的信息
        if self.use_teacher and self.teacher_models:
            # 可以在这里添加教师模型的辅助逻辑
            # 例如：使用教师模型的输出进行校准
            teacher_results = []
            for teacher_model in self.teacher_models:
                try:
                    teacher_result = teacher_model.predict(image, confidence_threshold)
                    teacher_results.append(teacher_result)
                except Exception as e:
                    logger.warning(f"教师模型预测失败: {str(e)}")
            
            # 添加教师模型信息到结果中
            if teacher_results:
                result["teacher_predictions"] = teacher_results
                result["distillation_info"] = {
                    "student_model": True,
                    "teacher_models": len(self.teacher_models),
                    "temperature": self.temperature
                }
        
        return result





def load_image_from_bytes(image_bytes: bytes) -> Optional[np.ndarray]:
    """从字节加载图像"""
    try:
        from io import BytesIO
        image = Image.open(BytesIO(image_bytes))
        return np.array(image)
    except Exception as e:
        logger.error(f"从字节加载图像失败: {str(e)}")
        return None


def predict_disease(model: ModelLoader, image: np.ndarray, class_names: list, device: torch.device, confidence_threshold: float = 0.5) -> Dict[str, Any]:
    """统一的预测函数，适配不同类型的模型加载器"""
    try:
        result = model.predict(image, confidence_threshold)
        
        # 确保结果格式统一
        if "top_prediction" in result:
            # 如果top_prediction是完整的字典（包含plant, disease, confidence）
            if result["top_prediction"] and isinstance(result["top_prediction"], dict):
                return result
        
        # 从预测结果中提取植物和病害信息
        if "predictions" in result and result["predictions"]:
            top_pred = result["predictions"][0]
            class_name = top_pred["class"]
            
            # 拆分class_name为plant和disease（假设格式为"Plant___Disease"）
            if "___" in class_name:
                plant, disease = class_name.split("___", 1)
            else:
                plant = "未知"
                disease = class_name
            
            # 构建统一格式的结果
            unified_result = {
                "top_prediction": {
                    "plant": plant,
                    "disease": disease,
                    "confidence": top_pred["confidence"]
                },
                "predictions": result["predictions"]
            }
            
            return unified_result
        
        # 默认结果
        return {
            "top_prediction": {
                "plant": "未知",
                "disease": "未知",
                "confidence": 0.0
            },
            "predictions": []
        }
    except Exception as e:
        logger.error(f"预测疾病失败: {str(e)}")
        return {
            "top_prediction": {
                "plant": "未知",
                "disease": "未知",
                "confidence": 0.0
            },
            "predictions": []
        }


def load_model_from_file(model_path: str, model_config_path: Optional[str] = None) -> Optional[ModelLoader]:
    """从文件加载模型（支持单模型、集成模型、蒸馏模型）"""
    if not os.path.exists(model_path):
        logger.error(f"模型文件不存在: {model_path}")
        return None
    
    # 加载配置
    model_config = {}
    if model_config_path and os.path.exists(model_config_path):
        model_config = load_config_file(model_config_path)
        if model_config is None:
            logger.warning(f"配置文件加载失败，使用默认配置")
            model_config = {}
    else:
        # 默认配置
        model_config = {
            "input_size": (224, 224),
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
            "class_names": []
        }
    
    # 检查是否为集成模型
    if "model_type" in model_config and model_config["model_type"] == "ensemble":
        model_paths = model_config.get("model_paths", [])
        if not model_paths:
            # 如果配置中没有指定路径，尝试从目录加载
            model_dir = os.path.dirname(model_path)
            model_paths = [os.path.join(model_dir, mp) for mp in model_config.get("model_files", [])]
        
        if model_paths:
            logger.info(f"检测到集成模型配置，包含 {len(model_paths)} 个模型")
            loader = EnsembleModelLoader(model_paths, model_config)
            if loader.load():
                return loader
            else:
                return None
    
    # 检查是否为蒸馏模型
    if "model_type" in model_config and model_config["model_type"] == "distillation":
        student_path = model_config.get("student_model_path", model_path)
        teacher_paths = model_config.get("teacher_model_paths", [])
        
        # 如果路径是相对路径，转换为绝对路径
        model_dir = os.path.dirname(model_path)
        if not os.path.isabs(student_path):
            student_path = os.path.join(model_dir, student_path)
        teacher_paths = [os.path.join(model_dir, tp) if not os.path.isabs(tp) else tp for tp in teacher_paths]
        
        logger.info(f"检测到蒸馏模型配置，学生模型: {student_path}, 教师模型: {len(teacher_paths)}个")
        loader = DistillationModelLoader(student_path, teacher_paths, model_config)
        if loader.load():
            return loader
        else:
            return None
    
    # 单模型加载
    file_ext = os.path.splitext(model_path)[1].lower()
    
    if file_ext in ['.pt', '.pth']:
        loader = PyTorchModelLoader(model_path, model_config)
    elif file_ext == '.onnx':
        loader = ONNXModelLoader(model_path, model_config)
    else:
        logger.error(f"不支持的模型格式: {file_ext}")
        return None
    
    # 加载模型
    if loader.load():
        return loader
    else:
        return None


def load_image_from_url(url: str) -> Optional[np.ndarray]:
    """从URL加载图像"""
    try:
        import requests
        from io import BytesIO
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            return np.array(image)
        else:
            logger.error(f"无法从URL加载图像: {url}, 状态码: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"从URL加载图像失败: {str(e)}")
        return None


def load_image_from_bytes(image_bytes: bytes) -> Optional[np.ndarray]:
    """从字节加载图像"""
    try:
        from io import BytesIO
        image = Image.open(BytesIO(image_bytes))
        return np.array(image)
    except Exception as e:
        logger.error(f"从字节加载图像失败: {str(e)}")
        return None


def predict_disease(model: ModelLoader, image: np.ndarray, class_names: list, device: torch.device, confidence_threshold: float = 0.5) -> Dict[str, Any]:
    """统一的预测函数，适配不同类型的模型加载器"""
    try:
        result = model.predict(image, confidence_threshold)
        
        # 确保结果格式统一
        if "top_prediction" in result:
            # 如果top_prediction是完整的字典（包含plant, disease, confidence）
            if result["top_prediction"] and isinstance(result["top_prediction"], dict):
                return result
        
        # 从预测结果中提取植物和病害信息
        if "predictions" in result and result["predictions"]:
            top_pred = result["predictions"][0]
            class_name = top_pred["class"]
            
            # 拆分class_name为plant和disease（假设格式为"Plant___Disease"）
            if "___" in class_name:
                plant, disease = class_name.split("___", 1)
            else:
                plant = "未知"
                disease = class_name
            
            # 构建统一格式的结果
            unified_result = {
                "top_prediction": {
                    "plant": plant,
                    "disease": disease,
                    "confidence": top_pred["confidence"]
                },
                "predictions": result["predictions"]
            }
            
            return unified_result
        
        # 默认结果
        return {
            "top_prediction": {
                "plant": "未知",
                "disease": "未知",
                "confidence": 0.0
            },
            "predictions": []
        }
    except Exception as e:
        logger.error(f"预测疾病失败: {str(e)}")
        return {
            "top_prediction": {
                "plant": "未知",
                "disease": "未知",
                "confidence": 0.0
            },
            "predictions": []
        }


class EnsembleModelLoader(ModelLoader):
    """集成模型加载器 - 支持多个模型的集成预测"""
    
    def __init__(self, model_paths: List[str], model_config: Dict[str, Any]):
        # 使用第一个模型路径作为主路径
        super().__init__(model_paths[0] if model_paths else "", model_config)
        self.model_paths = model_paths
        self.models = []  # 存储多个模型加载器
        self.ensemble_strategy = model_config.get("ensemble_strategy", "average")  # average, voting, weighted
        self.weights = model_config.get("weights", None)  # 加权平均的权重
        self.input_size = model_config.get("input_size", (224, 224))
        self.mean = model_config.get("mean", [0.485, 0.456, 0.406])
        self.std = model_config.get("std", [0.229, 0.224, 0.225])
        self.class_names = model_config.get("class_names", [])
        
    def load(self) -> bool:
        """加载所有集成模型"""
        try:
            if not self.model_paths:
                logger.error("集成模型路径列表为空")
                return False
            
            # 加载所有模型
            for i, model_path in enumerate(self.model_paths):
                if not os.path.exists(model_path):
                    logger.error(f"集成模型文件不存在: {model_path}")
                    continue
                
                # 根据文件扩展名选择加载器
                file_ext = os.path.splitext(model_path)[1].lower()
                model_config = self.model_config.copy()
                
                if file_ext in ['.pt', '.pth']:
                    loader = PyTorchModelLoader(model_path, model_config)
                elif file_ext == '.onnx':
                    loader = ONNXModelLoader(model_path, model_config)
                else:
                    logger.warning(f"不支持的模型格式: {file_ext}, 跳过: {model_path}")
                    continue
                
                if loader.load():
                    self.models.append(loader)
                    logger.info(f"集成模型 {i+1}/{len(self.model_paths)} 加载成功: {model_path}")
                else:
                    logger.warning(f"集成模型 {i+1}/{len(self.model_paths)} 加载失败: {model_path}")
            
            if not self.models:
                logger.error("没有成功加载任何集成模型")
                return False
            
            # 归一化权重
            if self.weights and len(self.weights) == len(self.models):
                total_weight = sum(self.weights)
                self.weights = [w / total_weight for w in self.weights]
            elif self.ensemble_strategy == "weighted":
                # 如果没有提供权重，使用均匀权重
                self.weights = [1.0 / len(self.models)] * len(self.models)
                logger.warning("加权集成策略但未提供权重，使用均匀权重")
            
            self.is_loaded = True
            logger.info(f"集成模型加载完成，共 {len(self.models)} 个模型，策略: {self.ensemble_strategy}")
            return True
        except Exception as e:
            logger.error(f"加载集成模型失败: {str(e)}")
            return False
    
    def preprocess(self, image: np.ndarray) -> Any:
        """预处理图像（使用第一个模型的预处理方法）"""
        if not self.models:
            raise RuntimeError("没有可用的模型")
        return self.models[0].preprocess(image)
    
    def _ensemble_average(self, outputs: List[Any]) -> np.ndarray:
        """平均策略：对多个模型的输出求平均"""
        if isinstance(outputs[0], torch.Tensor):
            # PyTorch张量
            stacked = torch.stack(outputs)
            averaged = torch.mean(stacked, dim=0)
            return averaged.cpu().numpy()
        else:
            # NumPy数组
            stacked = np.stack(outputs)
            averaged = np.mean(stacked, axis=0)
            return averaged
    
    def _ensemble_weighted_average(self, outputs: List[Any]) -> np.ndarray:
        """加权平均策略"""
        if not self.weights:
            return self._ensemble_average(outputs)
        
        if isinstance(outputs[0], torch.Tensor):
            # PyTorch张量
            weighted_sum = sum(w * out for w, out in zip(self.weights, outputs))
            return weighted_sum.cpu().numpy()
        else:
            # NumPy数组
            weighted_sum = sum(w * out for w, out in zip(self.weights, outputs))
            return weighted_sum
    
    def _ensemble_voting(self, outputs: List[Any]) -> np.ndarray:
        """投票策略：每个模型投票，选择得票最多的类别"""
        # 先转换为概率
        probabilities_list = []
        for output in outputs:
            if isinstance(output, torch.Tensor):
                prob = torch.nn.functional.softmax(output, dim=1).cpu().numpy()[0]
            else:
                exp_output = np.exp(output - np.max(output))
                prob = exp_output / np.sum(exp_output)
                prob = prob[0]
            probabilities_list.append(prob)
        
        # 投票：每个模型选择最高概率的类别
        votes = np.zeros(len(self.class_names) if self.class_names else probabilities_list[0].shape[0])
        for prob in probabilities_list:
            top_class = np.argmax(prob)
            votes[top_class] += 1
        
        # 归一化为概率
        total_votes = len(probabilities_list)
        final_prob = votes / total_votes
        
        # 转换为与原始输出相同的形状
        return np.expand_dims(final_prob, axis=0)
    
    def postprocess(self, ensemble_output: np.ndarray, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """后处理集成输出"""
        # 应用softmax
        if isinstance(ensemble_output, torch.Tensor):
            probabilities = torch.nn.functional.softmax(ensemble_output, dim=1)
            probs_array = probabilities[0].cpu().numpy()
        else:
            exp_output = np.exp(ensemble_output - np.max(ensemble_output))
            probabilities = exp_output / np.sum(exp_output)
            probs_array = probabilities[0]
        
        # 获取top-k结果
        top_k = min(5, len(self.class_names) if self.class_names else len(probs_array))
        top_indices = np.argsort(probs_array)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            prob = float(probs_array[idx])
            
            if prob >= confidence_threshold:
                class_name = self.class_names[idx] if self.class_names and idx < len(self.class_names) else f"class_{idx}"
                results.append({
                    "class": class_name,
                    "confidence": prob,
                    "class_id": int(idx)
                })
        
        return {
            "predictions": results,
            "top_prediction": results[0] if results else None,
            "ensemble_info": {
                "num_models": len(self.models),
                "strategy": self.ensemble_strategy
            }
        }
    
    def predict(self, image: np.ndarray, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """集成预测"""
        if not self.is_loaded:
            raise RuntimeError("集成模型未加载")
        
        if not self.models:
            raise RuntimeError("没有可用的模型")
        
        # 预处理（使用第一个模型）
        preprocessed = self.preprocess(image)
        
        # 所有模型进行预测
        outputs = []
        for i, model in enumerate(self.models):
            try:
                if isinstance(model, PyTorchModelLoader):
                    with torch.no_grad():
                        if isinstance(preprocessed, torch.Tensor):
                            output = model.model(preprocessed)
                        else:
                            # 如果预处理返回numpy，需要转换
                            input_tensor = torch.from_numpy(preprocessed).to(model.device)
                            output = model.model(input_tensor)
                    outputs.append(output)
                elif isinstance(model, ONNXModelLoader):
                    input_array = preprocessed if isinstance(preprocessed, np.ndarray) else preprocessed.cpu().numpy()
                    input_name = model.session.get_inputs()[0].name
                    output = model.session.run(None, {input_name: input_array})[0]
                    outputs.append(output)
                else:
                    # 使用模型的predict方法
                    result = model.predict(image, confidence_threshold)
                    # 提取原始输出（需要根据实际情况调整）
                    outputs.append(result)
            except Exception as e:
                logger.error(f"模型 {i+1} 预测失败: {str(e)}")
                continue
        
        if not outputs:
            raise RuntimeError("所有模型预测都失败")
        
        # 集成策略
        if self.ensemble_strategy == "average":
            ensemble_output = self._ensemble_average(outputs)
        elif self.ensemble_strategy == "weighted":
            ensemble_output = self._ensemble_weighted_average(outputs)
        elif self.ensemble_strategy == "voting":
            ensemble_output = self._ensemble_voting(outputs)
        else:
            logger.warning(f"未知的集成策略: {self.ensemble_strategy}，使用平均策略")
            ensemble_output = self._ensemble_average(outputs)
        
        # 后处理
        result = self.postprocess(ensemble_output, confidence_threshold)
        
        return result


class DistillationModelLoader(ModelLoader):
    """蒸馏模型加载器 - 支持教师模型和学生模型"""
    
    def __init__(self, student_model_path: str, teacher_model_paths: Optional[List[str]], model_config: Dict[str, Any]):
        super().__init__(student_model_path, model_config)
        self.student_model_path = student_model_path
        self.teacher_model_paths = teacher_model_paths or []
        self.student_model = None
        self.teacher_models = []
        self.use_teacher = model_config.get("use_teacher", False)  # 是否使用教师模型辅助
        self.temperature = model_config.get("temperature", 4.0)  # 蒸馏温度
        self.input_size = model_config.get("input_size", (224, 224))
        self.mean = model_config.get("mean", [0.485, 0.456, 0.406])
        self.std = model_config.get("std", [0.229, 0.224, 0.225])
        self.class_names = model_config.get("class_names", [])
        
    def load(self) -> bool:
        """加载学生模型和可选的教师模型"""
        try:
            # 加载学生模型
            if not os.path.exists(self.student_model_path):
                logger.error(f"学生模型文件不存在: {self.student_model_path}")
                return False
            
            file_ext = os.path.splitext(self.student_model_path)[1].lower()
            if file_ext in ['.pt', '.pth']:
                self.student_model = PyTorchModelLoader(self.student_model_path, self.model_config)
            elif file_ext == '.onnx':
                self.student_model = ONNXModelLoader(self.student_model_path, self.model_config)
            else:
                logger.error(f"不支持的学生模型格式: {file_ext}")
                return False
            
            if not self.student_model.load():
                logger.error("学生模型加载失败")
                return False
            
            logger.info(f"学生模型加载成功: {self.student_model_path}")
            
            # 可选：加载教师模型
            if self.use_teacher and self.teacher_model_paths:
                for teacher_path in self.teacher_model_paths:
                    if not os.path.exists(teacher_path):
                        logger.warning(f"教师模型文件不存在: {teacher_path}")
                        continue
                    
                    file_ext = os.path.splitext(teacher_path)[1].lower()
                    if file_ext in ['.pt', '.pth']:
                        teacher_model = PyTorchModelLoader(teacher_path, self.model_config)
                    elif file_ext == '.onnx':
                        teacher_model = ONNXModelLoader(teacher_path, self.model_config)
                    else:
                        logger.warning(f"不支持的教师模型格式: {file_ext}")
                        continue
                    
                    if teacher_model.load():
                        self.teacher_models.append(teacher_model)
                        logger.info(f"教师模型加载成功: {teacher_path}")
            
            self.is_loaded = True
            logger.info(f"蒸馏模型加载完成，学生模型: 1个，教师模型: {len(self.teacher_models)}个")
            return True
        except Exception as e:
            logger.error(f"加载蒸馏模型失败: {str(e)}")
            return False
    
    def predict(self, image: np.ndarray, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """使用学生模型进行预测（可选使用教师模型辅助）"""
        if not self.is_loaded:
            raise RuntimeError("蒸馏模型未加载")
        
        # 使用学生模型进行预测
        result = self.student_model.predict(image, confidence_threshold)
        
        # 如果启用教师模型，可以添加额外的信息
        if self.use_teacher and self.teacher_models:
            # 可以在这里添加教师模型的辅助逻辑
            # 例如：使用教师模型的输出进行校准
            teacher_results = []
            for teacher_model in self.teacher_models:
                try:
                    teacher_result = teacher_model.predict(image, confidence_threshold)
                    teacher_results.append(teacher_result)
                except Exception as e:
                    logger.warning(f"教师模型预测失败: {str(e)}")
            
            # 添加教师模型信息到结果中
            if teacher_results:
                result["teacher_predictions"] = teacher_results
                result["distillation_info"] = {
                    "student_model": True,
                    "teacher_models": len(self.teacher_models),
                    "temperature": self.temperature
                }
        
        return result

