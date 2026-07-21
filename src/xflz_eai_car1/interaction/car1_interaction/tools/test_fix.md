# 语音交互流程修复说明

## 问题诊断

**原问题**：唤醒后还没说话，就进入识别、LLM交互和TTS合成。

**根本原因**：
1. 用户说完唤醒词后，VAD 仍处于 `is_speech_detected()=True` 状态（唤醒词尾音/环境噪音）
2. 转换到 LISTENING 状态时，`_vad_in_speech` 被重置为 `False`
3. 提示音被禁用，没有给 VAD 足够时间稳定
4. VAD 阈值过低（0.35），对噪音敏感
5. 预热期结束后，因为 `_vad_in_speech=False` 且 `vad.is_speech_detected()=True`，立即触发 `_vad_speech_started()`，创建 ASR stream

## 修复方案

### 1. 重新启用提示音 (`voice_interaction.py:1049-1068`)
- 播放 `kws.wav` 给用户明确反馈
- 提示音播放期间，系统忽略音频（除了 KWS 打断检测）
- 给 VAD 足够时间让语音状态稳定

### 2. 增加"等待静音"逻辑 (`voice_interaction.py:825-878`)
- 新增 `_vad_waiting_silence` 标志位
- 提示音播放完成后，**必须先检测到静音**，才能开始检测新的语音
- 流程：唤醒 → 播放提示音 → 等待静音 → 检测到用户开始说话 → ASR 识别

### 3. 调整 VAD 参数 (`config.yaml:15-22`)
- `threshold: 0.35 → 0.5`：提高阈值，降低对环境噪音的敏感度
- `min_speech_duration: 0.15 → 0.25`：需要更长的连续语音才触发，避免短暂噪音

### 4. 初始化标志位 (`voice_interaction.py:219-223`)
- 在 `__init__` 中初始化 `_vad_waiting_silence = False`

## 修复后的流程

```
用户说"小飞同学"
    ↓
检测到唤醒词 → _transition_to_listening()
    ↓
播放提示音 kws.wav (设置 _vad_waiting_silence=True)
    ↓
提示音播放期间：忽略音频，只检测KWS打断
    ↓
提示音播放完成
    ↓
等待 VAD 检测到静音 (_vad_waiting_silence=True)
    ↓
检测到静音 → _vad_waiting_silence=False (准备接收用户语音)
    ↓
**用户开始说话**
    ↓
VAD 检测到语音开始 (_vad_speech_started() = True)
    ↓
创建 ASR stream，实时转写
    ↓
检测到后端点（用户说话结束）
    ↓
提交最终识别结果给 LLM
    ↓
LLM 实时输出 → 分段 → TTS 合成 → 实时播放
```

## 验证步骤

1. 运行交互系统：
```bash
cd /home/iflytek/ros2_ws/src/xflz_eai_car1/interaction/car1_interaction/tools
python3 voice_interaction.py --debug
```

2. 说"小飞同学"唤醒

3. 观察日志输出：
   - 应该看到 "提示音播放完成，等待用户说话..."
   - 然后看到 "已检测到静音，准备接收用户语音"（如果开启 debug.show_vad_status）
   - **只有在你真正开始说话后**，才会看到 "检测到用户开始说话 → ASR 激活"

4. 验证没有误触发：
   - 唤醒后，保持安静几秒
   - 系统不应该自动进入 ASR 识别
   - 只有当你开始说话时，才会出现 `[ASR]` 实时转写

## 相关文件

- `voice_interaction.py`: 主程序逻辑
- `config.yaml`: VAD 参数配置
- `resource/kws.wav`: 唤醒提示音
- `resource/idle.wav`: 超时提示音
