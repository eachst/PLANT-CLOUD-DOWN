/**
 * 预测API服务
 * 用于调用后端模型服务的预测接口
 */
import apiClient from './api';

export interface PredictionRequest {
  image_url?: string;
  model_name?: string;
  confidence_threshold?: number;
}

export interface PredictionResult {
  success: boolean;
  predictions: Array<{
    class: string;
    confidence: number;
    class_id: number;
  }>;
  top_prediction: {
    class: string;
    confidence: number;
    class_id: number;
  } | null;
  processing_time: number;
  model_name: string;
  ensemble_info?: {
    num_models: number;
    strategy: string;
  };
  distillation_info?: {
    student_model: boolean;
    teacher_models: number;
    temperature: number;
  };
}

export interface AsyncPredictionResponse {
  message: string;
  task_id: string;
  status: string;
}

/**
 * 直接预测（同步）
 * @param file 图像文件
 * @param modelName 模型名称
 * @param confidenceThreshold 置信度阈值
 */
export async function directPrediction(
  file: File,
  modelName: string = 'default',
  confidenceThreshold: number = 0.5
): Promise<PredictionResult> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('model_name', modelName);
  formData.append('confidence_threshold', confidenceThreshold.toString());

  return apiClient.post<PredictionResult>(
    '/predictions/direct',
    formData
  );
}

/**
 * 创建异步预测任务
 * @param imageUrl 图像URL
 * @param modelName 模型名称
 * @param confidenceThreshold 置信度阈值
 */
export async function createPredictionTask(
  imageUrl: string,
  modelName: string = 'default',
  confidenceThreshold: number = 0.5
): Promise<AsyncPredictionResponse> {
  return apiClient.post<AsyncPredictionResponse>('/predictions/', {
    image_url: imageUrl,
    model_name: modelName,
    confidence_threshold: confidenceThreshold,
  });
}

/**
 * 获取预测结果
 * @param taskId 任务ID
 */
export async function getPredictionResult(
  taskId: string
): Promise<PredictionResult & { status: string; task_id: string }> {
  return apiClient.get(`/predictions/${taskId}`);
}

/**
 * 上传图像并获取URL（如果需要）
 * 这里可以集成到腾讯云COS或其他存储服务
 */
export async function uploadImage(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);

  // 如果后端有图像上传接口，使用它
  // 否则返回本地预览URL
  try {
    const response = await apiClient.post<{ url: string }>(
      '/upload',
      formData
    );
    return response.url;
  } catch (error) {
    // 如果上传失败，返回本地预览URL
    return URL.createObjectURL(file);
  }
}

/**
 * 获取模型列表
 */
export async function getModels(): Promise<any[]> {
  const response = await apiClient.get('/models/');
  return response.models || [];
}

/**
 * 获取模型信息
 */
export async function getModelInfo(modelName: string): Promise<any> {
  return apiClient.get(`/models/${modelName}`);
}

