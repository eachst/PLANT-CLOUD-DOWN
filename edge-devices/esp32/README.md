# ESP32植物病害检测边缘设备

## 硬件要求

- ESP32开发板（推荐ESP32-CAM或ESP32-WROVER-KIT）
- OV2640摄像头模块
- Micro USB数据线
- WiFi网络

## 软件要求

- Arduino IDE 1.8.13或更高版本
- ESP32开发板支持包

## 安装步骤

### 1. 安装Arduino IDE和ESP32支持

1. 下载并安装 [Arduino IDE](https://www.arduino.cc/en/software)
2. 打开Arduino IDE，进入 `文件` -> `首选项`
3. 在"附加开发板管理器网址"中添加：
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. 进入 `工具` -> `开发板` -> `开发板管理器`
5. 搜索"esp32"并安装"esp32 by Espressif Systems"

### 2. 安装必要的库

在Arduino IDE中，进入 `工具` -> `管理库`，安装以下库：

- **ArduinoJson** (版本 6.x)
- **ESP32 Camera** (通常已包含在ESP32支持包中)

### 3. 配置代码

1. 打开 `plant_disease_detector.ino`
2. 修改以下配置：

```cpp
// WiFi配置
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// 云端API配置
const char* api_base_url = "http://your-server-ip:8000/api";
const char* api_key = "YOUR_API_KEY";  // 可选
```

3. 根据您的硬件调整 `camera_pins.h` 中的引脚定义

### 4. 上传代码

1. 选择开发板：`工具` -> `开发板` -> `ESP32 Arduino` -> 选择您的ESP32型号
2. 选择端口：`工具` -> `端口` -> 选择您的COM端口
3. 点击上传按钮

## 功能说明

- **定时采集**：每30秒自动采集一张图像
- **云端检测**：将图像上传到云端API进行病害检测
- **结果输出**：通过串口监视器显示检测结果

## 串口监视器设置

- 波特率：115200
- 换行符：Both NL & CR

## 故障排除

1. **摄像头初始化失败**
   - 检查摄像头模块连接
   - 确认引脚定义正确
   - 检查电源供应是否充足

2. **WiFi连接失败**
   - 检查SSID和密码是否正确
   - 确认WiFi信号强度
   - 检查路由器是否支持2.4GHz频段（ESP32不支持5GHz）

3. **API请求失败**
   - 检查服务器IP地址和端口
   - 确认服务器正在运行
   - 检查防火墙设置

## 自定义配置

### 修改采集间隔

```cpp
const unsigned long capture_interval = 60000;  // 改为60秒
```

### 修改图像质量

```cpp
const int jpeg_quality = 10;  // 数值越小质量越高（0-63）
```

### 修改分辨率

在 `initCamera()` 函数中修改：

```cpp
config.frame_size = FRAMESIZE_SVGA;  // 800x600
// 或
config.frame_size = FRAMESIZE_HD;    // 1280x720
```

## 支持的摄像头模块

- OV2640（推荐）
- OV3660
- OV5640

## 许可证

MIT License

