# 前端修复总结

## 已修复的问题

### 1. API调用问题 ✅

**问题：**
- `detection.tsx` 使用模拟数据，没有真正调用后端API
- API路径不统一（有些用 `/auth/login`，有些用 `/api/auth/login`）
- 缺少专门的预测API服务函数

**修复：**
- 创建了 `lib/predictionApi.ts` - 专门的预测API服务
- 更新了 `detection.tsx` - 使用真实的API调用
- 统一了API路径为 `/api/...`
- 更新了 `lib/api.ts` - 修正了API基础URL

### 2. 检测页面功能增强 ✅

**新增功能：**
- 模型选择下拉框（支持选择不同模型）
- 置信度阈值滑块调整
- 真实API调用（不再使用模拟数据）
- 显示集成模型和蒸馏模型信息
- 显示所有预测结果（不仅仅是top-1）
- 显示处理时间

### 3. API配置统一 ✅

**修复：**
- 统一使用 `NEXT_PUBLIC_API_BASE_URL` 环境变量
- 默认值设置为 `http://localhost:8000/api`
- 更新了所有API调用路径

## 新增文件

### `lib/predictionApi.ts`

提供以下API函数：
- `directPrediction()` - 直接预测（同步）
- `createPredictionTask()` - 创建异步预测任务
- `getPredictionResult()` - 获取预测结果
- `uploadImage()` - 上传图像
- `getModels()` - 获取模型列表
- `getModelInfo()` - 获取模型信息

## 更新的文件

1. **`pages/detection.tsx`**
   - 移除模拟数据
   - 添加真实API调用
   - 添加模型选择功能
   - 添加置信度阈值调整
   - 改进结果显示

2. **`lib/api.ts`**
   - 修正API基础URL
   - 增加超时时间到60秒（预测需要更长时间）

3. **`store/index.ts`**
   - 统一API路径
   - 添加API基础URL的fallback

4. **`next.config.js`**
   - 添加 `NEXT_PUBLIC_API_BASE_URL` 环境变量

## 环境变量配置

在 `.env.local` 或部署时设置：

```bash
NEXT_PUBLIC_API_BASE_URL=http://your-server-ip:8000/api
# 或
NEXT_PUBLIC_API_URL=http://your-server-ip:8000/api
```

## 使用说明

### 1. 检测页面使用

1. 上传图像
2. 选择模型（默认/集成/蒸馏/其他模型）
3. 调整置信度阈值（0-1）
4. 点击"开始检测"
5. 查看结果

### 2. API调用示例

```typescript
import { directPrediction } from '../lib/predictionApi';

// 直接预测
const result = await directPrediction(file, 'ensemble', 0.5);
console.log(result.top_prediction);
```

## 待完善功能

1. **异步预测支持** - 目前只实现了同步预测
2. **历史记录页面** - 需要实现历史记录查看
3. **模型管理页面** - 需要实现模型列表和管理
4. **错误处理优化** - 更详细的错误提示
5. **图像预览优化** - 支持图像裁剪和编辑

## 注意事项

1. **CORS配置** - 确保后端API允许前端域名访问
2. **文件大小限制** - 前端和后端都需要设置文件大小限制
3. **超时设置** - 预测可能需要较长时间，已设置为60秒
4. **环境变量** - 确保正确配置API地址

## 测试建议

1. 测试不同模型的预测
2. 测试不同置信度阈值
3. 测试错误处理（网络错误、API错误等）
4. 测试大文件上传
5. 测试并发请求

