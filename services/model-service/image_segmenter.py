import cv2
import numpy as np
from PIL import Image

class ImageSegmenter:
    """
    图像分割器，用于从图像中提取植物区域
    
    使用颜色阈值和形态学操作来分离植物区域
    """
    
    def __init__(self):
        pass
    
    def segment_plant(self, image, threshold_low=None, threshold_high=None):
        """
        从图像中分割出植物区域
        
        参数:
            image: PIL.Image 对象或 numpy.ndarray (BGR 或 RGB)
            threshold_low: HSV颜色空间中的下界阈值，默认为 (25, 40, 40)
            threshold_high: HSV颜色空间中的上界阈值，默认为 (90, 255, 255)
            
        返回:
            segmented_image: 分割后的图像，只包含植物区域 (与输入格式相同)
            mask: 二值掩码图像 (numpy.ndarray)
        """
        # 默认阈值设置（适合绿色植物）
        if threshold_low is None:
            threshold_low = (25, 40, 40)  # HSV下限
        if threshold_high is None:
            threshold_high = (90, 255, 255)  # HSV上限
        
        is_pil_image = isinstance(image, Image.Image)
        is_numpy_array = isinstance(image, np.ndarray)
        
        # 处理输入图像，转换为numpy数组
        if is_pil_image:
            img_array = np.array(image)
            # 如果是RGBA格式，转换为RGB
            if img_array.shape[-1] == 4:
                img_array = img_array[..., :3]
            # PIL.Image是RGB格式，转换为BGR用于OpenCV
            img_array_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        elif is_numpy_array:
            img_array = image.copy()
            # 如果是RGBA格式，转换为RGB
            if img_array.shape[-1] == 4:
                img_array = img_array[..., :3]
            # 检查是否需要转换颜色空间
            # 假设输入是BGR格式（OpenCV默认）
            img_array_bgr = img_array
            # 转换为RGB用于后续处理
            img_array = cv2.cvtColor(img_array_bgr, cv2.COLOR_BGR2RGB)
        else:
            raise TypeError("输入必须是PIL.Image对象或numpy.ndarray")
        
        # 转换到HSV颜色空间
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        
        # 创建颜色掩码
        mask = cv2.inRange(hsv, threshold_low, threshold_high)
        
        # 应用形态学操作来清理掩码
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 寻找轮廓并保留最大的轮廓（假设是植物主体）
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # 找到最大的轮廓
            largest_contour = max(contours, key=cv2.contourArea)
            
            # 创建新的掩码，只保留最大的轮廓
            full_mask = np.zeros_like(mask)
            cv2.drawContours(full_mask, [largest_contour], -1, 255, -1)
            
            # 使用掩码提取植物区域
            segmented_array = cv2.bitwise_and(img_array, img_array, mask=full_mask)
            
            # 找到植物区域的边界框
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # 如果边界框太小，可能是误检测，返回原图
            if w * h < 1000:  # 最小面积阈值
                if is_pil_image:
                    return image, np.ones_like(mask, dtype=np.uint8) * 255
                else:
                    return img_array_bgr, np.ones_like(mask, dtype=np.uint8) * 255
            
            # 不裁剪，返回完整尺寸的图像和掩码
            if is_pil_image:
                # 转换回PIL图像
                segmented_image = Image.fromarray(segmented_array)
                return segmented_image, full_mask
            else:
                # 转换为BGR格式返回
                segmented_bgr = cv2.cvtColor(segmented_array, cv2.COLOR_RGB2BGR)
                return segmented_bgr, full_mask
        else:
            # 如果没有找到轮廓，返回原图和全白掩码
            if is_pil_image:
                return image, np.ones_like(mask, dtype=np.uint8) * 255
            else:
                return img_array_bgr, np.ones_like(mask, dtype=np.uint8) * 255
    
    def segment_plant_lab(self, image):
        """
        使用Lab颜色空间分割植物区域
        
        参数:
            image: PIL.Image 对象或 numpy.ndarray
            
        返回:
            segmented_image: 分割后的图像 (与输入格式相同)
            mask: 二值掩码图像 (numpy.ndarray)
        """
        is_pil_image = isinstance(image, Image.Image)
        is_numpy_array = isinstance(image, np.ndarray)
        
        # 处理输入图像，转换为numpy数组
        if is_pil_image:
            img_array = np.array(image)
            # 如果是RGBA格式，转换为RGB
            if img_array.shape[-1] == 4:
                img_array = img_array[..., :3]
            # PIL.Image是RGB格式，转换为BGR用于OpenCV
            img_array_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        elif is_numpy_array:
            img_array = image.copy()
            # 如果是RGBA格式，转换为RGB
            if img_array.shape[-1] == 4:
                img_array = img_array[..., :3]
            # 假设输入是BGR格式（OpenCV默认）
            img_array_bgr = img_array
            # 转换为RGB用于后续处理
            img_array = cv2.cvtColor(img_array_bgr, cv2.COLOR_BGR2RGB)
        else:
            raise TypeError("输入必须是PIL.Image对象或numpy.ndarray")
        
        # 转换到Lab颜色空间
        lab = cv2.cvtColor(img_array_bgr, cv2.COLOR_BGR2LAB)
        
        # 使用a通道（绿色植物在a通道中为负值）
        a_channel = lab[:, :, 1]
        
        # 直方图均衡化增强对比度
        a_eq = cv2.equalizeHist(a_channel)
        
        # 应用Otsu阈值分割
        _, mask = cv2.threshold(a_eq, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 应用形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 寻找轮廓并保留最大的轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # 找到最大的轮廓
            largest_contour = max(contours, key=cv2.contourArea)
            
            # 创建新的掩码，只保留最大的轮廓
            full_mask = np.zeros_like(mask)
            cv2.drawContours(full_mask, [largest_contour], -1, 255, -1)
            
            # 使用掩码提取植物区域
            segmented_array = cv2.bitwise_and(img_array, img_array, mask=full_mask)
            
            # 找到植物区域的边界框
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # 如果边界框太小，可能是误检测，返回原图
            if w * h < 1000:  # 最小面积阈值
                if is_pil_image:
                    return image, np.ones_like(mask, dtype=np.uint8) * 255
                else:
                    return img_array_bgr, np.ones_like(mask, dtype=np.uint8) * 255
            
            # 不裁剪，返回完整尺寸的图像和掩码
            if is_pil_image:
                # 转换回PIL图像
                segmented_image = Image.fromarray(segmented_array)
                return segmented_image, full_mask
            else:
                # 转换为BGR格式返回
                segmented_bgr = cv2.cvtColor(segmented_array, cv2.COLOR_RGB2BGR)
                return segmented_bgr, full_mask
        else:
            # 如果没有找到轮廓，返回原图和全白掩码
            if is_pil_image:
                return image, np.ones_like(mask, dtype=np.uint8) * 255
            else:
                return img_array_bgr, np.ones_like(mask, dtype=np.uint8) * 255
                
    def segment_plant_rgb_auto(self, image):
        """
        使用RGB颜色空间的自动阈值分割植物区域
        
        参数:
            image: PIL.Image 对象或 numpy.ndarray
            
        返回:
            segmented_image: 分割后的图像 (与输入格式相同)
            mask: 二值掩码图像 (numpy.ndarray)
        """
        is_pil_image = isinstance(image, Image.Image)
        is_numpy_array = isinstance(image, np.ndarray)
        
        # 处理输入图像，转换为numpy数组
        if is_pil_image:
            img_array = np.array(image)
            # 如果是RGBA格式，转换为RGB
            if img_array.shape[-1] == 4:
                img_array = img_array[..., :3]
            # PIL.Image是RGB格式
            img_array_rgb = img_array
        elif is_numpy_array:
            img_array = image.copy()
            # 如果是RGBA格式，转换为RGB
            if img_array.shape[-1] == 4:
                img_array = img_array[..., :3]
            # 假设输入是BGR格式（OpenCV默认），转换为RGB
            img_array_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        else:
            raise TypeError("输入必须是PIL.Image对象或numpy.ndarray")
        
        # 计算RGB比率特征
        # 对绿色敏感的比率: (G - R) / (G + R + B)
        r, g, b = img_array_rgb[:, :, 0], img_array_rgb[:, :, 1], img_array_rgb[:, :, 2]
        denominator = r + g + b
        denominator[denominator == 0] = 1  # 避免除以零
        ratio = (g - r) / denominator
        
        # 归一化到0-255范围
        ratio_norm = cv2.normalize(ratio, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        
        # 应用Otsu阈值分割
        _, mask = cv2.threshold(ratio_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 应用形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 寻找轮廓并保留最大的轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # 找到最大的轮廓
            largest_contour = max(contours, key=cv2.contourArea)
            
            # 创建新的掩码，只保留最大的轮廓
            full_mask = np.zeros_like(mask)
            cv2.drawContours(full_mask, [largest_contour], -1, 255, -1)
            
            # 使用掩码提取植物区域
            segmented_array = cv2.bitwise_and(img_array_rgb, img_array_rgb, mask=full_mask)
            
            # 找到植物区域的边界框
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # 如果边界框太小，可能是误检测，返回原图
            if w * h < 1000:  # 最小面积阈值
                if is_pil_image:
                    return image, np.ones_like(mask, dtype=np.uint8) * 255
                else:
                    return img_array, np.ones_like(mask, dtype=np.uint8) * 255
            
            # 转换为原始格式
            if is_pil_image:
                # 转换回PIL图像
                segmented_image = Image.fromarray(segmented_array)
                return segmented_image, full_mask
            else:
                # 转换回BGR格式
                segmented_bgr = cv2.cvtColor(segmented_array, cv2.COLOR_RGB2BGR)
                return segmented_bgr, full_mask
        else:
            # 如果没有找到轮廓，返回原图和全白掩码
            if is_pil_image:
                return image, np.ones_like(mask, dtype=np.uint8) * 255
            else:
                return img_array, np.ones_like(mask, dtype=np.uint8) * 255
    
    def segment_with_fallback(self, image):
        """
        使用多种阈值组合尝试分割，如果失败则返回原图
        
        参数:
            image: PIL.Image 对象或 numpy.ndarray
            
        返回:
            segmented_image: 分割后的图像 (与输入格式相同)
            mask: 二值掩码图像 (numpy.ndarray)
        """
        # 尝试多种分割方法
        segmentation_methods = [
            # HSV颜色空间分割 - 标准绿色植物
            lambda img: self.segment_plant(img, (25, 40, 40), (90, 255, 255)),
            # HSV颜色空间分割 - 浅绿色植物
            lambda img: self.segment_plant(img, (35, 30, 70), (85, 255, 255)),
            # HSV颜色空间分割 - 深绿色植物
            lambda img: self.segment_plant(img, (20, 50, 30), (70, 255, 200)),
            # Lab颜色空间分割
            self.segment_plant_lab,
            # RGB自动阈值分割
            self.segment_plant_rgb_auto
        ]
        
        is_pil_image = isinstance(image, Image.Image)
        is_numpy_array = isinstance(image, np.ndarray)
        
        # 获取原始图像尺寸
        if is_pil_image:
            original_size = image.width * image.height
        elif is_numpy_array:
            original_size = image.shape[0] * image.shape[1]
        else:
            raise TypeError("输入必须是PIL.Image对象或numpy.ndarray")
        
        best_segmented = image
        best_mask = None
        min_size_ratio = 0.1  # 分割区域至少为原图的10%
        
        for method in segmentation_methods:
            try:
                segmented, mask = method(image)
                
                # 获取分割后图像的尺寸
                if is_pil_image:
                    segmented_size = segmented.width * segmented.height
                else:
                    segmented_size = segmented.shape[0] * segmented.shape[1]
                
                # 如果分割后的区域大小合理，且不是太小
                if segmented_size > min_size_ratio * original_size:
                    best_segmented = segmented
                    best_mask = mask
                    # 找到合适的分割就返回
                    return best_segmented, best_mask
            except Exception:
                continue
        
        # 如果所有尝试都不成功，返回原图
        if best_mask is None:
            # 创建全白掩码
            if is_pil_image:
                best_mask = np.ones((image.height, image.width), dtype=np.uint8) * 255
            else:
                best_mask = np.ones((image.shape[0], image.shape[1]), dtype=np.uint8) * 255
        
        return best_segmented, best_mask

# 创建全局图像分割器实例
segmenter = ImageSegmenter()

def segment_image(image, method="fallback", low=None, high=None):
    """
    便捷函数：使用默认的ImageSegmenter进行图像分割
    
    参数:
        image: PIL.Image 对象或 numpy.ndarray
        method: 分割方法选择 (可选, 默认: "fallback"):
            - "hsv": 使用HSV颜色空间的默认阈值分割
            - "lab": 使用Lab颜色空间分割
            - "rgb_auto": 使用RGB自动阈值分割
            - "fallback": 使用多种方法的回退策略
        low: HSV阈值下限 (仅当method="hsv"时使用)
        high: HSV阈值上限 (仅当method="hsv"时使用)
        
    返回:
        segmented_image: 分割后的图像 (与输入格式相同)
        mask: 二值掩码图像 (numpy.ndarray)
    """
    if method == "hsv":
        if low is None or high is None:
            # 使用默认HSV阈值
            return segmenter.segment_plant(image, (35, 30, 30), (85, 255, 255))
        else:
            return segmenter.segment_plant(image, low, high)
    elif method == "lab":
        return segmenter.segment_plant_lab(image)
    elif method == "rgb_auto":
        return segmenter.segment_plant_rgb_auto(image)
    elif method == "fallback":
        return segmenter.segment_with_fallback(image)
    else:
        raise ValueError(f"不支持的分割方法: {method}。可用方法: 'hsv', 'lab', 'rgb_auto', 'fallback'")