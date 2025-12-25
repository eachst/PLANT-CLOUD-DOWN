# 集成模型和蒸馏模型使用指南

## 概述

本系统支持三种模型类型：
1. **单模型** - 单个独立的模型
2. **集成模型** - 多个模型的组合，通过不同策略融合结果
3. **蒸馏模型** - 学生模型（可选使用教师模型辅助）

## 配置文件格式支持

系统同时支持 **JSON** 和 **YAML** 格式的配置文件：
- JSON: `.json` 扩展名
- YAML: `.yaml` 或 `.yml` 扩展名

推荐使用 YAML 格式，更易读易写。

## 模型配置文件格式

### 1. 单模型配置

**JSON格式：**
```json
{
  "input_size": [224, 224],
  "mean": [0.485, 0.456, 0.406],
  "std": [0.229, 0.224, 0.225],
  "class_names": ["healthy", "disease1", "disease2", "disease3"]
}
```

**YAML格式（推荐）：**
```yaml
input_size: [224, 224]
mean: [0.485, 0.456, 0.406]
std: [0.229, 0.224, 0.225]
class_names:
  - healthy
  - disease1
  - disease2
  - disease3
```

文件名：`{model_name}_config.json` 或 `{model_name}_config.yaml`

### 2. 集成模型配置

**JSON格式：**
```json
{
  "model_type": "ensemble",
  "model_paths": [
    "/app/models/model1.pt",
    "/app/models/model2.pt",
    "/app/models/model3.pt"
  ],
  "ensemble_strategy": "average",
  "weights": [0.4, 0.3, 0.3],
  "input_size": [224, 224],
  "mean": [0.485, 0.456, 0.406],
  "std": [0.229, 0.224, 0.225],
  "class_names": ["healthy", "disease1", "disease2", "disease3"]
}
```

**YAML格式（推荐）：**
```yaml
model_type: ensemble
model_paths:
  - model1.pt
  - model2.pt
  - model3.pt
ensemble_strategy: average  # average, weighted, voting
weights: [0.4, 0.3, 0.3]  # 仅当strategy为weighted时使用
input_size: [224, 224]
mean: [0.485, 0.456, 0.406]
std: [0.229, 0.224, 0.225]
class_names:
  - healthy
  - disease1
  - disease2
  - disease3
```

**参数说明：**
- `model_type`: 必须为 `"ensemble"`
- `model_paths`: 模型文件路径列表（绝对路径或相对于配置文件的路径）
- `ensemble_strategy`: 集成策略
  - `"average"`: 平均策略（默认）
  - `"weighted"`: 加权平均
  - `"voting"`: 投票策略
- `weights`: 加权平均的权重（仅当strategy为weighted时使用）

文件名：`ensemble_config.yaml`、`ensemble_config.yml` 或 `ensemble_config.json`

### 3. 蒸馏模型配置

**JSON格式：**
```json
{
  "model_type": "distillation",
  "student_model_path": "student_model.pt",
  "teacher_model_paths": [
    "teacher_model1.pt",
    "teacher_model2.pt"
  ],
  "use_teacher": false,
  "temperature": 4.0,
  "input_size": [224, 224],
  "mean": [0.485, 0.456, 0.406],
  "std": [0.229, 0.224, 0.225],
  "class_names": ["healthy", "disease1", "disease2", "disease3"]
}
```

**YAML格式（推荐）：**
```yaml
model_type: distillation
student_model_path: student_model.pt
teacher_model_paths:
  - teacher_model1.pt
  - teacher_model2.pt
use_teacher: false  # 是否使用教师模型辅助
temperature: 4.0  # 蒸馏温度参数
input_size: [224, 224]
mean: [0.485, 0.456, 0.406]
std: [0.229, 0.224, 0.225]
class_names:
  - healthy
  - disease1
  - disease2
  - disease3
```

**参数说明：**
- `model_type`: 必须为 `"distillation"`
- `student_model_path`: 学生模型路径（相对或绝对路径）
- `teacher_model_paths`: 教师模型路径列表（可选）
- `use_teacher`: 是否使用教师模型辅助（默认false）
- `temperature`: 蒸馏温度参数

文件名：`distillation_config.yaml`、`distillation_config.yml` 或 `distillation_config.json`

## 部署步骤

### 1. 准备模型文件

将所有模型文件上传到 `/opt/plant-disease/models/` 目录：

```bash
# 单模型
model1.pt
model1_config.json

# 集成模型
model1.pt
model2.pt
model3.pt
ensemble_config.json

# 蒸馏模型
student_model.pt
teacher_model1.pt
teacher_model2.pt
distillation_config.json
```

### 2. 配置集成模型

创建 `ensemble_config.json`：

```json
{
  "model_type": "ensemble",
  "model_paths": [
    "model1.pt",
    "model2.pt",
    "model3.pt"
  ],
  "ensemble_strategy": "average",
  "input_size": [224, 224],
  "mean": [0.485, 0.456, 0.406],
  "std": [0.229, 0.224, 0.225],
  "class_names": ["healthy", "leaf_spot", "rust", "powdery_mildew"]
}
```

### 3. 配置蒸馏模型

创建 `distillation_config.json`：

```json
{
  "model_type": "distillation",
  "student_model_path": "student_model.pt",
  "teacher_model_paths": ["teacher_model1.pt", "teacher_model2.pt"],
  "use_teacher": false,
  "input_size": [224, 224],
  "mean": [0.485, 0.456, 0.406],
  "std": [0.229, 0.224, 0.225],
  "class_names": ["healthy", "disease1", "disease2"]
}
```

### 4. 加载模型

系统启动时会自动扫描 `models/` 目录并加载所有模型。

对于集成模型和蒸馏模型，需要指定配置文件：

- 集成模型：创建 `ensemble_config.json`，系统会自动识别
- 蒸馏模型：创建 `distillation_config.json`，系统会自动识别

或者，可以通过API手动加载：

```bash
# 加载集成模型
curl -X POST "http://localhost:8003/api/models/load" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "ensemble",
    "config_path": "/app/models/ensemble_config.json"
  }'
```

## API使用

### 使用集成模型预测

```bash
curl -X POST "http://localhost:8000/api/predictions/direct" \
  -F "file=@test_image.jpg" \
  -F "model_name=ensemble" \
  -F "confidence_threshold=0.5"
```

响应示例：

```json
{
  "success": true,
  "predictions": [
    {"class": "leaf_spot", "confidence": 0.92, "class_id": 1},
    {"class": "healthy", "confidence": 0.08, "class_id": 0}
  ],
  "top_prediction": {
    "class": "leaf_spot",
    "confidence": 0.92,
    "class_id": 1
  },
  "processing_time": 0.45,
  "model_name": "ensemble",
  "ensemble_info": {
    "num_models": 3,
    "strategy": "average"
  }
}
```

### 使用蒸馏模型预测

```bash
curl -X POST "http://localhost:8000/api/predictions/direct" \
  -F "file=@test_image.jpg" \
  -F "model_name=distillation" \
  -F "confidence_threshold=0.5"
```

## 集成策略说明

### 1. Average（平均策略）

对所有模型的输出概率求平均：

```python
final_prob = mean([model1_prob, model2_prob, model3_prob])
```

**优点：** 简单稳定，适合大多数情况
**缺点：** 所有模型权重相同

### 2. Weighted（加权平均）

根据权重对模型输出进行加权平均：

```python
final_prob = sum(weight[i] * model[i]_prob for i in range(num_models))
```

**优点：** 可以为不同模型设置不同权重
**缺点：** 需要手动调整权重

### 3. Voting（投票策略）

每个模型投票选择最高概率的类别，最终选择得票最多的类别：

```python
votes = [argmax(model1_prob), argmax(model2_prob), argmax(model3_prob)]
final_class = mode(votes)  # 众数
```

**优点：** 对异常值鲁棒
**缺点：** 可能忽略概率信息

## 最佳实践

1. **集成模型**
   - 使用3-5个不同架构的模型效果最好
   - 平均策略通常效果最好
   - 如果模型性能差异大，使用加权平均

2. **蒸馏模型**
   - 学生模型通常比教师模型小且快
   - 如果学生模型性能足够，可以设置 `use_teacher: false`
   - 教师模型主要用于训练时的知识蒸馏

3. **性能优化**
   - 集成模型会增加推理时间（N倍，N为模型数量）
   - 考虑使用ONNX格式加速
   - 使用GPU可以并行推理多个模型

## 故障排除

### 模型加载失败

1. 检查模型文件路径是否正确
2. 检查配置文件格式是否正确
3. 查看日志：`docker-compose logs model-service`

### 集成预测结果异常

1. 检查所有模型是否都成功加载
2. 确认模型输出维度一致
3. 检查集成策略配置

### 性能问题

1. 减少集成模型数量
2. 使用ONNX格式
3. 启用GPU加速

## 示例配置

### 完整集成模型配置示例

```json
{
  "model_type": "ensemble",
  "model_paths": [
    "resnet50_ensemble_model1.pt",
    "efficientnet_ensemble_model2.pt",
    "densenet_ensemble_model3.pt"
  ],
  "ensemble_strategy": "weighted",
  "weights": [0.4, 0.35, 0.25],
  "input_size": [224, 224],
  "mean": [0.485, 0.456, 0.406],
  "std": [0.229, 0.224, 0.225],
  "class_names": [
    "healthy",
    "bacterial_spot",
    "early_blight",
    "late_blight",
    "leaf_mold",
    "septoria_leaf_spot",
    "spider_mites",
    "target_spot",
    "yellow_leaf_curl_virus",
    "mosaic_virus"
  ]
}
```

### 完整蒸馏模型配置示例

```json
{
  "model_type": "distillation",
  "student_model_path": "student_model_distilled.pt",
  "teacher_model_paths": [
    "teacher_resnet50.pt",
    "teacher_efficientnet.pt"
  ],
  "use_teacher": false,
  "temperature": 4.0,
  "input_size": [224, 224],
  "mean": [0.485, 0.456, 0.406],
  "std": [0.229, 0.224, 0.225],
  "class_names": [
    "healthy",
    "disease1",
    "disease2"
  ]
}
```

