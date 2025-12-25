/**
 * ESP32植物病害检测边缘设备
 * 使用OV2640摄像头采集图像并上传到云端进行检测
 * 
 * 硬件要求:
 * - ESP32开发板
 * - OV2640摄像头模块
 * - WiFi连接
 * 
 * 功能:
 * - 定时采集图像
 * - 上传图像到云端API
 * - 接收检测结果
 * - 通过串口输出结果
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <esp_camera.h>
#include "camera_pins.h"

// WiFi配置
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// 云端API配置
const char* api_base_url = "http://your-server-ip:8000/api";
const char* api_key = "YOUR_API_KEY";  // 可选

// 采集间隔（毫秒）
const unsigned long capture_interval = 30000;  // 30秒
unsigned long last_capture_time = 0;

// 图像质量（0-63，数值越小质量越高）
const int jpeg_quality = 12;

// 初始化摄像头
void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  // 根据可用内存选择分辨率
  if(psramFound()){
    config.frame_size = FRAMESIZE_UXGA;  // 1600x1200
    config.jpeg_quality = jpeg_quality;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;  // 800x600
    config.jpeg_quality = jpeg_quality;
    config.fb_count = 1;
  }

  // 初始化摄像头
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("摄像头初始化失败，错误代码: 0x%x\n", err);
    return;
  }
  
  Serial.println("摄像头初始化成功");
}

// 连接WiFi
void connectWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("正在连接WiFi");
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("WiFi连接成功，IP地址: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println();
    Serial.println("WiFi连接失败");
  }
}

// 采集图像
camera_fb_t* captureImage() {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("图像采集失败");
    return NULL;
  }
  
  Serial.printf("图像采集成功，大小: %d 字节\n", fb->len);
  return fb;
}

// 上传图像并获取预测结果
void uploadAndPredict(camera_fb_t* fb) {
  if (!fb) {
    return;
  }
  
  HTTPClient http;
  String url = String(api_base_url) + "/predictions/direct";
  
  http.begin(url);
  http.addHeader("Content-Type", "multipart/form-data");
  if (strlen(api_key) > 0) {
    http.addHeader("X-API-Key", api_key);
  }
  
  // 创建multipart/form-data请求体
  String boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW";
  String contentType = "multipart/form-data; boundary=" + boundary;
  
  String body = "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"file\"; filename=\"image.jpg\"\r\n";
  body += "Content-Type: image/jpeg\r\n\r\n";
  
  // 发送请求
  http.addHeader("Content-Type", contentType);
  
  // 先发送头部
  http.POST(body);
  
  // 发送图像数据
  http.write((uint8_t*)fb->buf, fb->len);
  
  // 发送结束边界
  String endBoundary = "\r\n--" + boundary + "--\r\n";
  http.write((uint8_t*)endBoundary.c_str(), endBoundary.length());
  
  int httpResponseCode = http.POST("");
  
  if (httpResponseCode > 0) {
    Serial.printf("HTTP响应代码: %d\n", httpResponseCode);
    
    if (httpResponseCode == 200) {
      String response = http.getString();
      Serial.println("预测结果:");
      Serial.println(response);
      
      // 解析JSON响应
      DynamicJsonDocument doc(2048);
      deserializeJson(doc, response);
      
      if (doc["success"]) {
        JsonObject topPrediction = doc["top_prediction"];
        if (topPrediction) {
          Serial.printf("检测结果: %s (置信度: %.2f%%)\n", 
                        topPrediction["class"].as<const char*>(), 
                        topPrediction["confidence"].as<float>() * 100);
        }
      }
    } else {
      Serial.printf("请求失败，错误代码: %d\n", httpResponseCode);
      Serial.println(http.getString());
    }
  } else {
    Serial.printf("HTTP请求失败: %s\n", http.errorToString(httpResponseCode).c_str());
  }
  
  http.end();
  
  // 释放图像缓冲区
  esp_camera_fb_return(fb);
}

// 健康检查
void healthCheck() {
  HTTPClient http;
  String url = String(api_base_url) + "/health/";
  
  http.begin(url);
  int httpResponseCode = http.GET();
  
  if (httpResponseCode > 0) {
    if (httpResponseCode == 200) {
      Serial.println("API服务健康检查: 正常");
    } else {
      Serial.printf("API服务健康检查: 异常 (代码: %d)\n", httpResponseCode);
    }
  } else {
    Serial.println("API服务健康检查: 无法连接");
  }
  
  http.end();
}

void setup() {
  Serial.begin(115200);
  Serial.println("\nESP32植物病害检测设备启动中...");
  
  // 初始化摄像头
  initCamera();
  
  // 连接WiFi
  connectWiFi();
  
  // 健康检查
  if (WiFi.status() == WL_CONNECTED) {
    delay(1000);
    healthCheck();
  }
  
  Serial.println("系统初始化完成");
}

void loop() {
  // 检查WiFi连接
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi连接断开，正在重新连接...");
    connectWiFi();
    delay(5000);
    return;
  }
  
  // 定时采集和上传
  unsigned long current_time = millis();
  if (current_time - last_capture_time >= capture_interval) {
    last_capture_time = current_time;
    
    Serial.println("\n开始采集图像...");
    camera_fb_t* fb = captureImage();
    
    if (fb) {
      uploadAndPredict(fb);
    }
  }
  
  delay(1000);
}

