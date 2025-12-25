"""
智能路由系统 - 根据设备能力和预测置信度动态选择模型
"""
import time
from typing import Dict, Any, Optional
import numpy as np
from PIL import Image
import torch

class SmartRouter:
    """智能路由系统"""
    
    def __init__(self, student_model: Optional[Any] = None, ensemble_model: Optional[Any] = None, 
                 class_names: Optional[list] = None, device: Optional[torch.device] = None):
        """初始化智能路由系统"""
        self.student_model = student_model
        self.ensemble_model = ensemble_model
        self.class_names = class_names or []
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 统计信息
        self.stats = {
            "student_predictions": 0,
            "ensemble_predictions": 0,
            "total_predictions": 0,
            "student_avg_time": 0.0,
            "ensemble_avg_time": 0.0,
            "total_time": 0.0
        }
        
        # 路由策略
        self.confidence_thresholds = {
            "high": 0.95,
            "medium": 0.90,
            "low": 0.85
        }
    
    def analyze_device(self, device_info: str) -> str:
        """分析设备信息，返回设备能力等级"""
        # 简单的设备能力分析，可根据实际情况扩展
        if not device_info:
            return "medium"
        
        device_info_lower = device_info.lower()
        
        # 高端设备特征
        high_end = ["high", "gpu", "cuda", "rtx", "v100", "a100", "h100", "apple m2", "apple m3"]
        
        # 低端设备特征
        low_end = ["low", "mobile", "phone", "android", "iphone", "ipad"]
        
        if any(feature in device_info_lower for feature in high_end):
            return "high"
        elif any(feature in device_info_lower for feature in low_end):
            return "low"
        else:
            return "medium"
    
    def predict_disease(self, model: Any, image: Image.Image, class_names: list, device: torch.device) -> Dict[str, Any]:
        """使用指定模型进行预测"""
        from model_loader import predict_disease as ml_predict_disease
        return ml_predict_disease(model, image, class_names, device)
    
    def smart_predict(self, image: Image.Image, device_info: str = "") -> Dict[str, Any]:
        """智能选择模型进行预测"""
        start_time = time.time()
        device_level = self.analyze_device(device_info)
        confidence_threshold = self.confidence_thresholds[device_level]
        
        # 高能力设备直接使用集成模型
        if device_level == "high" and self.ensemble_model is not None:
            ensemble_pred = self.predict_disease(self.ensemble_model, image, self.class_names, self.device)
            self.stats["ensemble_predictions"] += 1
            self.stats["total_predictions"] += 1
            
            end_time = time.time()
            inference_time = end_time - start_time
            self.stats["ensemble_avg_time"] = (
                (self.stats["ensemble_avg_time"] * (self.stats["ensemble_predictions"] - 1) + inference_time) / self.stats["ensemble_predictions"]
            )
            self.stats["total_time"] += inference_time
            
            return {
                "result": ensemble_pred,
                "model_used": "ensemble",
                "device_level": device_level,
                "confidence_threshold": confidence_threshold,
                "inference_time": inference_time
            }
        
        # 中低能力设备先使用学生模型
        if self.student_model is None:
            # 学生模型未加载，使用集成模型
            if self.ensemble_model is None:
                raise ValueError("没有可用的模型")
            ensemble_pred = self.predict_disease(self.ensemble_model, image, self.class_names, self.device)
            self.stats["ensemble_predictions"] += 1
            self.stats["total_predictions"] += 1
            
            end_time = time.time()
            inference_time = end_time - start_time
            self.stats["ensemble_avg_time"] = (
                (self.stats["ensemble_avg_time"] * (self.stats["ensemble_predictions"] - 1) + inference_time) / self.stats["ensemble_predictions"]
            )
            self.stats["total_time"] += inference_time
            
            return {
                "result": ensemble_pred,
                "model_used": "ensemble",
                "device_level": device_level,
                "confidence_threshold": confidence_threshold,
                "inference_time": inference_time
            }
        
        # 使用学生模型进行初步预测
        student_pred = self.predict_disease(self.student_model, image, self.class_names, self.device)
        student_time = time.time() - start_time
        
        # 检查置信度
        student_confidence = student_pred.get("top_prediction", {}).get("confidence", 0.0)
        
        # 学生模型置信度足够高，直接返回结果
        if student_confidence >= confidence_threshold:
            self.stats["student_predictions"] += 1
            self.stats["total_predictions"] += 1
            
            self.stats["student_avg_time"] = (
                (self.stats["student_avg_time"] * (self.stats["student_predictions"] - 1) + student_time) / self.stats["student_predictions"]
            )
            self.stats["total_time"] += student_time
            
            return {
                "result": student_pred,
                "model_used": "student",
                "device_level": device_level,
                "confidence_threshold": confidence_threshold,
                "inference_time": student_time,
                "confidence_analysis": {
                    "student_confidence": student_confidence,
                    "threshold": confidence_threshold,
                    "decision": "student_model_sufficient"
                }
            }
        
        # 学生模型置信度不够，使用集成模型
        if self.ensemble_model is not None:
            ensemble_pred = self.predict_disease(self.ensemble_model, image, self.class_names, self.device)
            end_time = time.time()
            
            total_time = end_time - start_time
            
            # 专家系统验证（简单示例）
            final_pred = self.validate_with_expert_system(student_pred, ensemble_pred)
            
            self.stats["ensemble_predictions"] += 1
            self.stats["total_predictions"] += 1
            
            self.stats["ensemble_avg_time"] = (
                (self.stats["ensemble_avg_time"] * (self.stats["ensemble_predictions"] - 1) + total_time) / self.stats["ensemble_predictions"]
            )
            self.stats["total_time"] += total_time
            
            return {
                "result": final_pred,
                "model_used": "ensemble",
                "device_level": device_level,
                "confidence_threshold": confidence_threshold,
                "inference_time": total_time,
                "confidence_analysis": {
                    "student_confidence": student_confidence,
                    "threshold": confidence_threshold,
                    "decision": "switched_to_ensemble"
                }
            }
        
        # 只有学生模型，返回结果
        self.stats["student_predictions"] += 1
        self.stats["total_predictions"] += 1
        
        self.stats["student_avg_time"] = (
            (self.stats["student_avg_time"] * (self.stats["student_predictions"] - 1) + student_time) / self.stats["student_predictions"]
        )
        self.stats["total_time"] += student_time
        
        return {
            "result": student_pred,
            "model_used": "student",
            "device_level": device_level,
            "confidence_threshold": confidence_threshold,
            "inference_time": student_time,
            "confidence_analysis": {
                "student_confidence": student_confidence,
                "threshold": confidence_threshold,
                "decision": "only_student_available"
            }
        }
    
    def validate_with_expert_system(self, student_pred: Dict[str, Any], ensemble_pred: Dict[str, Any]) -> Dict[str, Any]:
        """使用专家系统验证预测结果"""
        # 简单的专家系统验证，可根据实际情况扩展
        student_top = student_pred.get("top_prediction", {})
        ensemble_top = ensemble_pred.get("top_prediction", {})
        
        # 如果预测结果一致，直接返回
        if student_top.get("plant") == ensemble_top.get("plant") and student_top.get("disease") == ensemble_top.get("disease"):
            # 合并置信度，取平均值
            combined_confidence = (student_top.get("confidence", 0.0) + ensemble_top.get("confidence", 0.0)) / 2
            
            final_pred = ensemble_pred.copy()
            final_pred["final_prediction"] = {
                "plant": student_top.get("plant"),
                "disease": student_top.get("disease"),
                "confidence": combined_confidence
            }
            final_pred["expert_verification"] = "predictions_match"
            return final_pred
        
        # 预测结果不一致，使用集成模型结果，因为置信度更高
        final_pred = ensemble_pred.copy()
        final_pred["final_prediction"] = ensemble_top
        final_pred["expert_verification"] = "ensemble_preferred"
        return final_pred
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            "student_predictions": 0,
            "ensemble_predictions": 0,
            "total_predictions": 0,
            "student_avg_time": 0.0,
            "ensemble_avg_time": 0.0,
            "total_time": 0.0
        }
    
    def update_thresholds(self, thresholds: Dict[str, float]) -> None:
        """更新置信度阈值"""
        self.confidence_thresholds.update(thresholds)
