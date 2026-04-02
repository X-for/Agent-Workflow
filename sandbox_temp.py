# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "numpy",
#     "opencv-python",
#     "scikit-learn",
# ]
# ///

import numpy as np
import cv2
import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("加油站加油事件识别 - 视频语义模型方案")
print("=" * 80)
print("\n[INFO] 初始化视频语义模型系统...")

# ==================== 1. 系统配置和定义 ====================
@dataclass
class SystemConfig:
    """系统配置参数"""
    # 视频处理参数
    frame_width: int = 640
    frame_height: int = 480
    fps: int = 30
    clip_duration: float = 5.0  # 视频片段时长（秒）
    
    # 模型参数
    num_classes: int = 10
    feature_dim: int = 512
    temporal_window: int = 16  # 时序窗口大小
    
    # 性能参数
    real_time_threshold: float = 0.1  # 实时处理阈值（秒）
    confidence_threshold: float = 0.7  # 置信度阈值
    
    # 事件定义
    event_names = {
        0: "无事件",
        1: "车辆进入",
        2: "车辆就位", 
        3: "拿起油枪",
        4: "开始加油",
        5: "加油中",
        6: "加油结束",
        7: "归还油枪",
        8: "车辆离开",
        9: "异常事件"
    }

class EventType(Enum):
    """事件类型枚举"""
    NO_EVENT = 0
    VEHICLE_ENTER = 1
    VEHICLE_POSITION = 2
    NOZZLE_PICKUP = 3
    FUELING_START = 4
    FUELING_IN_PROGRESS = 5
    FUELING_END = 6
    NOZZLE_RETURN = 7
    VEHICLE_LEAVE = 8
    ABNORMAL_EVENT = 9

# ==================== 2. 视频语义特征提取器 ====================
class VideoFeatureExtractor:
    """视频特征提取器 - 模拟视频语义模型的核心特征提取"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.feature_cache = {}
        
    def extract_spatial_features(self, frame: np.ndarray) -> np.ndarray:
        """提取空间特征（模拟CNN特征提取）"""
        try:
            # 1. 预处理
            resized = cv2.resize(frame, (224, 224))
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            
            # 2. 提取多种特征（模拟深度特征）
            features = []
            
            # HOG特征（方向梯度直方图）
            hog = self._extract_hog_features(gray)
            features.extend(hog)
            
            # 颜色直方图
            color_hist = self._extract_color_histogram(resized)
            features.extend(color_hist)
            
            # 纹理特征（LBP）
            texture = self._extract_texture_features(gray)
            features.extend(texture)
            
            # 运动特征（光流 - 需要多帧）
            if 'prev_frame' in self.feature_cache:
                flow = self._extract_optical_flow(self.feature_cache['prev_frame'], gray)
                features.extend(flow)
            
            self.feature_cache['prev_frame'] = gray
            
            # 转换为固定维度
            features_array = np.array(features, dtype=np.float32)
            
            # 如果特征维度不够，用0填充
            if len(features_array) < self.config.feature_dim:
                padding = np.zeros(self.config.feature_dim - len(features_array))
                features_array = np.concatenate([features_array, padding])
            else:
                features_array = features_array[:self.config.feature_dim]
            
            return features_array
            
        except Exception as e:
            print(f"[WARNING] 特征提取失败: {e}")
            return np.zeros(self.config.feature_dim, dtype=np.float32)
    
    def _extract_hog_features(self, gray_image: np.ndarray) -> List[float]:
        """提取HOG特征"""
        # 简化版HOG特征提取
        gx = cv2.Sobel(gray_image, cv2.CV_32F, 1, 0)
        gy = cv2.Sobel(gray_image, cv2.CV_32F, 0, 1)
        
        mag, angle = cv2.cartToPolar(gx, gy, angleInDegrees=True)
        
        # 计算方向直方图
        hist_bins = 9
        hist_range = (0, 180)
        hist = cv2.calcHist([angle], [0], None, [hist_bins], hist_range)
        hist = cv2.normalize(hist, hist).flatten()
        
        return hist.tolist()
    
    def _extract_color_histogram(self, image: np.ndarray) -> List[float]:
        """提取颜色直方图"""
        # 分别在HSV空间的H、S、V通道计算直方图
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        hist_h = cv2.calcHist([hsv], [0], None, [8], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], None, [4], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], None, [4], [0, 256])
        
        # 归一化并拼接
        hist_h = cv2.normalize(hist_h, hist_h).flatten()
        hist_s = cv2.normalize(hist_s, hist_s).flatten()
        hist_v = cv2.normalize(hist_v, hist_v).flatten()
        
        return np.concatenate([hist_h, hist_s, hist_v]).tolist()
    
    def _extract_texture_features(self, gray_image: np.ndarray) -> List[float]:
        """提取纹理特征（简化LBP）"""
        # 计算局部二值模式
        height, width = gray_image.shape
        features = []
        
        # 分块计算纹理统计
        block_size = 56  # 224/4
        for i in range(0, height, block_size):
            for j in range(0, width, block_size):
                block = gray_image[i:i+block_size, j:j+block_size]
                if block.size > 0:
                    features.append(np.mean(block))
                    features.append(np.std(block))
        
        return features[:16]  # 限制特征数量
    
    def _extract_optical_flow(self, prev_gray: np.ndarray, curr_gray: np.ndarray) -> List[float]:
        """提取光流特征"""
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            0.5, 3, 15, 3, 5, 1.2, 0
        )
        
        # 计算光流统计特征
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        features = [
            np.mean(magnitude),
            np.std(magnitude),
            np.mean(angle),
            np.std(angle)
        ]
        
        return features

# ==================== 3. 时序语义理解模型 ====================
class TemporalSemanticModel:
    """时序语义理解模型 - 模拟LSTM/Transformer的时序建模"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.temporal_buffer = []
        self.max_buffer_size = config.temporal_window * 2
        
        # 模拟训练好的模型权重（实际应用中需要真实训练）
        self.weights = self._initialize_weights()
        
    def _initialize_weights(self) -> Dict:
        """初始化模型权重（模拟预训练模型）"""
        # 这里模拟一个简单的时序分类器
        input_dim = self.config.feature_dim
        hidden_dim = 256
        output_dim = self.config.num_classes
        
        # 模拟LSTM-like权重
        weights = {
            'W_input': np.random.randn(input_dim, hidden_dim) * 0.01,
            'W_hidden': np.random.randn(hidden_dim, hidden_dim) * 0.01,
            'W_output': np.random.randn(hidden_dim, output_dim) * 0.01,
            'b_hidden': np.zeros(hidden_dim),
            'b_output': np.zeros(output_dim),
            'attention_weights': np.random.randn(self.config.temporal_window, hidden_dim) * 0.01
        }
        
        return weights
    
    def process_temporal_sequence(self, features: List[np.ndarray]) -> Dict:
        """处理时序特征序列"""
        try:
            # 1. 更新时序缓冲区
            self.temporal_buffer.extend(features)
            if len(self.temporal_buffer) > self.max_buffer_size:
                self.temporal_buffer = self.temporal_buffer[-self.max_buffer_size:]
            
            # 2. 提取时序窗口
            if len(self.temporal_buffer) < self.config.temporal_window:
                # 缓冲区不足，用0填充
                padding = [np.zeros(self.config.feature_dim)] * (self.config.temporal_window - len(self.temporal_buffer))
                window_features = padding + self.temporal_buffer
            else:
                window_features = self.temporal_buffer[-self.config.temporal_window:]
            
            # 3. 时序建模（模拟LSTM/Transformer）
            temporal_features = self._temporal_modeling(window_features)
            
            # 4. 事件分类
            event_probs, event_id = self._classify_event(temporal_features)
            
            # 5. 时序一致性检查
            consistency_score = self._check_temporal_consistency(event_id)
            
            return {
                'event_id': event_id,
                'event_name': self.config.event_names[event_id],
                'confidence': float(event_probs[event_id]),
                'all_probabilities': event_probs.tolist(),
                'temporal_consistency': consistency_score,
                'timestamp': time.time()
            }
            
        except Exception as e:
            print(f"[ERROR] 时序处理失败: {e}")
            return {
                'event_id': 0,
                'event_name': "无事件",
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _temporal_modeling(self, features: List[np.ndarray]) -> np.ndarray:
        """时序建模（模拟LSTM/Transformer）"""
        # 将特征序列转换为矩阵
        feature_matrix = np.stack(features)  # [T, D]
        
        # 模拟LSTM-like处理
        hidden_state = np.zeros(self.weights['W_hidden'].shape[1])
        
        for t in range(feature_matrix.shape[0]):
            # 输入门
            input_gate = np.tanh(
                np.dot(feature_matrix[t], self.weights['W_input']) + 
                np.dot(hidden_state, self.weights['W_hidden']) + 
                self.weights['b_hidden']
            )
            
            # 更新隐藏状态
            hidden_state = 0.7 * hidden_state + 0.3 * input_gate
        
        # 注意力机制（模拟）
        attention_scores = np.dot(feature_matrix, self.weights['attention_weights'].T)
        attention_weights = np.softmax(attention_scores.mean(axis=1))
        
        # 加权聚合
        weighted_features = np.dot(attention_weights, feature_matrix)
        
        return weighted_features
    
    def _classify_event(self, temporal_features: np.ndarray) -> Tuple[np.ndarray, int]:
        """事件分类"""
        # 线性分类
        logits = np.dot(temporal_features, self.weights['W_output']) + self.weights['b_output']
        
        # Softmax得到概率
        exp_logits = np.exp(logits - np.max(logits))
        probabilities = exp_logits / np.sum(exp_logits)
        
        # 获取最可能的事件
        event_id = np.argmax(probabilities)
        
        return probabilities, int(event_id)
    
    def _check_temporal_consistency(self, current_event: int) -> float:
        """检查时序一致性"""
        if len(self.temporal_buffer) < 2:
            return 1.0  # 数据不足，默认一致
        
        # 简单的一致性检查：事件应该符合一定的转移规律
        valid_transitions = {
            0: [0, 1, 9],  # 无事件 -> 无事件/车辆进入/异常
            1: [2, 9],     # 车辆进入 -> 车辆就位/异常
            2: [3, 9],     # 车辆就位 -> 拿起油枪/异常
            3: [4, 9],     # 拿起油枪 -> 开始加油/异常
            4: [5, 9],     # 开始加油 -> 加油中/异常
            5: [5, 6, 9],  # 加油中 -> 加油中/加油结束/异常
            6: [7, 9],     # 加油结束 -> 归还油枪/异常
            7: [8, 9],     # 归还油枪 -> 车辆离开/异常
            8: [0, 1, 9],  # 车辆离开 -> 无事件/车辆进入/异常
            9: [0, 1, 9]   # 异常 -> 无事件/车辆进入/异常
        }
        
        # 检查最近几个事件是否符合转移规律
        recent_events = []
        for _ in range(min(3, len(self.temporal_buffer) // 10)):
            # 模拟从特征中提取事件（实际中应该有历史记录）
            recent_events.append(np.random.choice(list(valid_transitions.keys())))
        
        if recent_events:
            last_event = recent_events[-1]
            if current_event in valid_transitions.get(last_event, []):
                return 0.9  # 符合转移规律
            else:
                return 0.3  # 不符合转移规律
        
        return 0.7  # 默认中等一致性

# ==================== 4. 完整的视频语义识别系统 ====================
class GasStationVideoSemanticSystem:
    """加油站视频语义识别系统"""
    
    def __init__(self, config: SystemConfig = None):
        self.config = config or SystemConfig()
        self.feature_extractor = VideoFeatureExtractor(self.config)
        self.temporal_model = TemporalSemanticModel(self.config)
        self.processing_stats = {
            'total_frames': 0,
            'processing_time': 0.0,
            'events_detected': 0
        }
        
        print("[INFO] 视频语义识别系统初始化完成")
        print(f"       - 特征维度: {self.config.feature_dim}")
        print(f"       - 时序窗口: {self.config.temporal_window}")
        print(f"       - 事件类别: {self.config.num_classes}")
    
    def process_video_clip(self, video_frames: List[np.ndarray]) -> Dict:
        """处理视频片段"""
        start_time = time.time()
        
        try:
            # 1. 提取每帧的特征
            frame_features = []
            for frame in video_frames:
                features = self.feature_extractor.extract_spatial_features(frame)
                frame_features.append(features)
            
            # 2. 时序语义理解
            result = self.temporal_model.process_temporal_sequence(frame_features)
            
            # 3. 更新统计信息
            processing_time = time.time() - start_time
            self.processing_stats['total_frames'] += len(video_frames)
            self.processing_stats['processing_time'] += processing_time
            self.processing_stats['events_detected'] += 1 if result['event_id'] > 0 else 0
            
            # 4. 添加性能指标
            result['processing_time_ms'] = processing_time * 1000
            result['frames_processed'] = len(video_frames)
            result['fps'] = len(video_frames) / processing_time if processing_time > 0 else 0
            
            # 5. 实时性检查
            if processing_time > self.config.real_time_threshold * len(video_frames):
                result['warning'] = "处理速度低于实时要求"
            
            return result
            
        except Exception as e:
            print(f"[ERROR] 视频处理失败: {e}")
            return {
                'error': str(e),
                'event_id': 0,
                'event_name': "处理失败"
            }
    
    def simulate_processing(self, num_clips: int = 10) -> List[Dict]:
        """模拟处理多个视频片段"""
        print(f"\n[INFO] 开始模拟处理 {num_clips} 个视频片段...")
        
        results = []
        for i in range(num_clips):
            print(f"\n处理片段 {i+1}/{num_clips}:")
            
            # 生成模拟视频帧
            clip_frames = self._generate_simulated_frames()
            
            # 处理视频片段
            result = self.process_video_clip(clip_frames)
            results.append(result)
            
            # 显示结果
            print(f"  检测事件: {result['event_name']}")
            print(f"  置信度: {result.get('confidence', 0):.3f}")
            print(f"  处理时间: {result.get('processing_time_ms', 0):.1f}ms")
            print(f"  实时FPS: {result.get('fps', 0):.1f}")
            
            if 'warning' in result:
                print(f"  ⚠️ 警告: {result['