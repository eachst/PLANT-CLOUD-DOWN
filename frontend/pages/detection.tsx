import { useState, useEffect } from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Typography, 
  Upload, 
  Button, 
  Image, 
  Progress, 
  Alert, 
  Tag, 
  Space,
  Divider,
  Empty,
  Spin,
  message,
  Select,
  Slider,
  InputNumber
} from 'antd';
import { 
  CameraOutlined, 
  UploadOutlined, 
  FileImageOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';
import { useAuth } from '../contexts/AuthContext';
import { useTaskStore, useNotificationStore, useModelStore } from '../store';
import AppLayout from '../components/AppLayout';
import { directPrediction, getModels, type PredictionResult } from '../lib/predictionApi';

const { Title, Text, Paragraph } = Typography;
const { Dragger } = Upload;

const DetectionPage = () => {
  const { user } = useAuth();
  const { createTask, currentTask, isCreating } = useTaskStore();
  const { addNotification } = useNotificationStore();
  const { models, fetchModels, currentModel } = useModelStore();
  
  const [imageFile, setImageFile] = useState<UploadFile | null>(null);
  const [previewImage, setPreviewImage] = useState<string>('');
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectionResult, setDetectionResult] = useState<PredictionResult | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('default');
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.5);

  // 加载模型列表
  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  // 处理文件上传
  const handleUploadChange: UploadProps['onChange'] = ({ fileList }) => {
    const file = fileList[0];
    if (file) {
      setImageFile(file);
      
      // 生成预览
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreviewImage(e.target?.result as string);
      };
      reader.readAsDataURL(file.originFileObj as File);
      
      // 重置检测结果
      setDetectionResult(null);
    }
  };

  // 开始检测
  const handleDetect = async () => {
    if (!imageFile || !imageFile.originFileObj) {
      message.error('请先选择一张图片');
      return;
    }

    try {
      setIsDetecting(true);
      message.loading('正在进行病害检测...', 0);
      
      // 调用后端API进行预测
      const file = imageFile.originFileObj as File;
      const result = await directPrediction(file, selectedModel, confidenceThreshold);
      
      message.destroy();
      
      if (result.success && result.top_prediction) {
        setDetectionResult(result);
        setIsDetecting(false);
        
        addNotification({
          title: '检测完成',
          message: `成功检测出${result.top_prediction.class}，置信度${(result.top_prediction.confidence * 100).toFixed(1)}%`,
          type: 'success',
        });
        
        message.success('检测完成！');
      } else {
        throw new Error('检测结果无效');
      }
    } catch (error: any) {
      setIsDetecting(false);
      message.destroy();
      
      const errorMessage = error?.response?.data?.message || error?.message || '检测失败，请重试';
      message.error(errorMessage);
      
      addNotification({
        title: '检测失败',
        message: errorMessage,
        type: 'error',
      });
    }
  };

  // 重置检测
  const handleReset = () => {
    setImageFile(null);
    setPreviewImage('');
    setDetectionResult(null);
    setIsDetecting(false);
  };

  // 严重程度颜色映射
  const severityColorMap = {
    low: 'green',
    medium: 'orange',
    high: 'red',
  };

  // 严重程度文本映射
  const severityTextMap = {
    low: '低',
    medium: '中',
    high: '高',
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* 页面标题 */}
        <div>
          <Title level={2}>植物病害检测</Title>
          <Text type="secondary">
            上传植物图片，系统将自动识别并诊断可能的病害问题。
          </Text>
        </div>

        <Row gutter={[24, 24]}>
          {/* 左侧：上传和预览区域 */}
          <Col xs={24} lg={12}>
            <Card title="图片上传" className="h-full">
              {!previewImage ? (
                <Dragger
                  name="image"
                  multiple={false}
                  accept="image/*"
                  showUploadList={false}
                  onChange={handleUploadChange}
                  beforeUpload={() => false} // 阻止自动上传
                  className="p-8"
                >
                  <p className="ant-upload-drag-icon">
                    <CameraOutlined className="text-4xl text-primary-500" />
                  </p>
                  <p className="ant-upload-text">点击或拖拽图片到此区域上传</p>
                  <p className="ant-upload-hint">
                    支持 JPG、PNG、GIF 等常见图片格式，文件大小不超过 10MB
                  </p>
                </Dragger>
              ) : (
                <div className="space-y-4">
                  <div className="relative">
                    <Image
                      src={previewImage}
                      alt="预览图片"
                      className="w-full rounded-lg"
                      style={{ maxHeight: '300px', objectFit: 'contain' }}
                    />
                    {isDetecting && (
                      <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center rounded-lg">
                        <Spin size="large" indicator={<LoadingOutlined spin />} />
                      </div>
                    )}
                  </div>
                  
                  <div className="flex justify-between">
                    <Space>
                      <FileImageOutlined />
                      <Text>{imageFile?.name}</Text>
                      <Text type="secondary">
                        ({(imageFile?.size! / 1024 / 1024).toFixed(2)} MB)
                      </Text>
                    </Space>
                    <Button size="small" onClick={handleReset}>
                      重新选择
                    </Button>
                  </div>
                  
                  <Divider />
                  
                  {/* 模型选择 */}
                  <div className="space-y-2">
                    <Text strong>选择模型：</Text>
                    <Select
                      value={selectedModel}
                      onChange={setSelectedModel}
                      style={{ width: '100%' }}
                      placeholder="选择检测模型"
                    >
                      <Select.Option value="default">默认模型</Select.Option>
                      <Select.Option value="ensemble">集成模型</Select.Option>
                      <Select.Option value="distillation">蒸馏模型</Select.Option>
                      {models.map((model) => (
                        <Select.Option key={model.id} value={model.name}>
                          {model.name} ({model.version})
                        </Select.Option>
                      ))}
                    </Select>
                  </div>
                  
                  {/* 置信度阈值 */}
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <Text strong>置信度阈值：</Text>
                      <InputNumber
                        min={0}
                        max={1}
                        step={0.1}
                        value={confidenceThreshold}
                        onChange={(value) => setConfidenceThreshold(value || 0.5)}
                        style={{ width: 80 }}
                      />
                    </div>
                    <Slider
                      min={0}
                      max={1}
                      step={0.1}
                      value={confidenceThreshold}
                      onChange={setConfidenceThreshold}
                      marks={{
                        0: '0',
                        0.5: '0.5',
                        1: '1',
                      }}
                    />
                  </div>
                  
                  <Divider />
                  
                  <Button
                    type="primary"
                    size="large"
                    block
                    icon={<CameraOutlined />}
                    onClick={handleDetect}
                    loading={isDetecting}
                    disabled={isDetecting}
                  >
                    {isDetecting ? '检测中...' : '开始检测'}
                  </Button>
                </div>
              )}
            </Card>
          </Col>

          {/* 右侧：检测结果区域 */}
          <Col xs={24} lg={12}>
            <Card title="检测结果" className="h-full">
              {isDetecting ? (
                <div className="flex flex-col items-center justify-center py-8 space-y-4">
                  <Spin size="large" />
                  <Text>正在分析图片，请稍候...</Text>
                  <Progress percent={66} showInfo={false} />
                </div>
              ) : detectionResult ? (
                <div className="space-y-4">
                  <div className="flex items-center space-x-2">
                    <CheckCircleOutlined className="text-green-500 text-xl" />
                    <Title level={4} className="mb-0">检测完成</Title>
                  </div>
                  
                  {/* 模型信息 */}
                  {detectionResult.ensemble_info && (
                    <Alert
                      message={`集成模型 (${detectionResult.ensemble_info.num_models}个模型, ${detectionResult.ensemble_info.strategy}策略)`}
                      type="info"
                      showIcon
                    />
                  )}
                  
                  {detectionResult.distillation_info && (
                    <Alert
                      message={`蒸馏模型 (学生模型 + ${detectionResult.distillation_info.teacher_models}个教师模型)`}
                      type="info"
                      showIcon
                    />
                  )}
                  
                  <div className="bg-secondary-50 p-4 rounded-lg">
                    <Space direction="vertical" className="w-full" size="middle">
                      {detectionResult.top_prediction && (
                        <>
                          <div>
                            <Text strong>检测结果：</Text>
                            <Text className="text-lg font-semibold text-primary-600 ml-2">
                              {detectionResult.top_prediction.class}
                            </Text>
                          </div>
                          
                          <div>
                            <Text strong>置信度：</Text>
                            <Progress
                              percent={Math.round(detectionResult.top_prediction.confidence * 100)}
                              size="small"
                              format={(percent) => `${percent}%`}
                              strokeColor={{
                                '0%': '#108ee9',
                                '100%': '#87d068',
                              }}
                            />
                          </div>
                        </>
                      )}
                      
                      {detectionResult.predictions && detectionResult.predictions.length > 1 && (
                        <div>
                          <Text strong>所有预测结果：</Text>
                          <div className="mt-2 space-y-1">
                            {detectionResult.predictions.map((pred, index) => (
                              <div key={index} className="flex justify-between items-center">
                                <Tag color={index === 0 ? 'green' : 'default'}>
                                  {pred.class}
                                </Tag>
                                <Text type="secondary">
                                  {(pred.confidence * 100).toFixed(1)}%
                                </Text>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      <div>
                        <Text strong>处理时间：</Text>
                        <Text>{detectionResult.processing_time.toFixed(2)}秒</Text>
                      </div>
                      
                      <div>
                        <Text strong>使用模型：</Text>
                        <Tag>{detectionResult.model_name}</Tag>
                      </div>
                    </Space>
                  </div>
                </div>
              ) : (
                <Empty
                  description="暂无检测结果"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                >
                  <Alert
                    message="请先上传图片并点击开始检测"
                    type="info"
                    showIcon
                    icon={<InfoCircleOutlined />}
                  />
                </Empty>
              )}
            </Card>
          </Col>
        </Row>
      </div>
    </AppLayout>
  );
};

export default DetectionPage;