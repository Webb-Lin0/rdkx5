# 基于RDK X5的多模态智能教育陪伴机器人

## 项目简介

本项目是一款基于 `RDK X5` 平台打造的多模态智能教育陪伴机器人，面向学校教学与家庭教育两类核心场景，融合大语言模型、语音交互、视觉感知与边缘计算能力，提供巡检、学习辅助、行为检测、远程陪伴与日常提醒等功能。

整体系统采用双 `RDK X5` 协同架构：

- `上位 RDK X5`：负责 `Qwen3 + ASR + TTS`，用于自然语言理解、语音识别、语音合成与智能问答交互。
- `下位 RDK X5`：负责边缘计算、视频流读取与视觉相关任务，并通过内部边缘业务接口与上位板协同，承担巡检、识别、检测与分析类能力。

该项目强调教育场景下的实用性与陪伴性，既可服务校园安全与教学管理，也可在家庭环境中提供学习辅助、健康提醒与智能交互体验。

## 核心特性

- 双 `RDK X5` 分工协作，兼顾大模型交互与本地视觉计算
- 支持学校巡检、学生状态感知与教学问答辅助
- 支持家庭场景下的天气播报、提醒、坐姿检测与健身评分
- 支持基于语音的自然交互与教育内容辅助
- 支持多模态能力融合，覆盖语音、视觉与任务调度场景

## 应用场景

### 学校应用场景

1. 支持通过 `SLAM + 路径规划` 定时巡检教学楼，通过检查各个教室内灯光状况、是否存在学生，保障学校用电安全与学生安全。
2. 支持学生打卡与情绪识别，家长端与教师端能够通过配套应用查看学生打卡状态与情绪状态，帮助教师与家长及时了解学生情况。
3. 支持教师远程布置题目，学生可以通过教育机器人进行作答；遇到不会的问题时，可向 `Qwen3` 寻求帮助，教师能够查看学生答题情况，从而提升学习效率。

### 家庭教育场景

1. 艺术素养首页搭载天气页面，并支持语音播报，帮助学生更便捷地了解天气信息。
2. 支持通过语音助手设置提醒任务，在指定时间触发语音提醒。
3. 支持学生坐姿检测，帮助学生保持良好坐姿，在检测到不良坐姿时触发提醒。
4. 具备自主研发的健身评分系统，支持 4 种动作的检测与评分，帮助提升学生身体素质。
5. 搭配配套应用后，支持学生与家长进行远程视频语音通话，提升陪伴与安全保障能力。
6. 搭载大语言模型生成学习问题，用于通识学习，并支持向 `Qwen3` 提问获取解答，提升综合学习能力。
7. 支持调用生图模型进行绘画创作，增强学生的创造力与表达能力。
8. 支持开启专注模式，对一天内的专注时间分布进行汇总，帮助培养良好的学习习惯。

## 系统架构

系统采用上下分层的双 `RDK X5` 协同架构，按照功能职责拆分如下：

### 上位 RDK X5：Qwen3 + ASR + TTS

上位 `RDK X5` 主要负责智能交互链路，聚焦以下能力：

- 部署 `Qwen3`，用于学习问答、知识辅助与对话交互
- 部署 `ASR`，将语音输入转换为文本指令
- 部署 `TTS`，将系统响应转换为自然语音输出
- 作为机器人的人机交互中枢，向下位板提供交互结果或任务请求

### 下位 RDK X5：边缘计算与视觉侧

下位 `RDK X5` 主要负责本地视觉与边缘任务处理，并通过内部边缘业务接口与上位板联动，聚焦以下能力：

- 视频流读取与处理
- 学校巡检过程中的环境感知与状态识别
- 学生打卡、情绪识别、坐姿检测与动作检测
- 家庭场景下的视觉分析与专注状态相关统计
- 接收上位板任务并完成本地侧感知与分析执行

整体协同顺序为：上位板先完成语言与语音交互能力构建，下位板再完成视觉与边缘计算能力部署，最终进行双板联调。

## 部署说明

### 上位 RDK X5：Qwen3 + ASR + TTS 部署

上位 `RDK X5` 主要完成大模型与语音交互链路部署。下面的流程按 `大模型环境 -> Qwen3 -> ASR -> TTS -> 联调` 的顺序整理，适合作为开源 README 中的核心部署主线。

#### 1. 基础环境准备

建议系统为 `Ubuntu 22.04`，先完成基础依赖安装：

```bash
sudo apt update
sudo apt install -y \
  curl git wget vim \
  python3 python3-pip python3-venv \
  docker.io ffmpeg sox alsa-utils i2c-tools

sudo systemctl enable docker --now
mkdir -p ~/edu_robot/upper_rdkx5
cd ~/edu_robot/upper_rdkx5
```

如需检查板端基础状态，可先执行：

```bash
uname -a
python3 --version
docker --version
ls /dev/snd
```

#### 2. Qwen3 部署

这里给出本地 `Qwen3` 推理与对话平台的常用部署方式。建议使用 `Ollama + WebUI` 组合，便于后续和语音链路联调。

安装 `Ollama`：

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable ollama --now
```

拉取并测试 `Qwen3` 模型：

```bash
ollama pull qwen3:4b
ollama run qwen3:4b
```

如果你希望提供一个本地可视化对话入口，可启动 `Open WebUI`：

```bash
sudo docker run -d \
  --name open-webui \
  --restart unless-stopped \
  -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:main
```

启动后可通过以下命令确认服务正常：

```bash
curl http://127.0.0.1:11434/api/tags
docker ps
```

#### 3. ASR 部署

语音识别部分建议直接使用 `RDK X5` 的音频能力包完成离线语音链路搭建。先安装音频算法包：

```bash
sudo apt update
sudo apt install -y tros-humble-hobot-audio
source /opt/tros/humble/setup.bash
```

如果使用四麦阵列或音频驱动板，先检查硬件是否被识别：

```bash
i2cdetect -r -y 0
ls /dev/snd
```

随后拷贝默认配置文件，便于按自己的硬件情况修改：

```bash
cd ~/edu_robot/upper_rdkx5
cp -r /opt/tros/${TROS_DISTRO}/lib/hobot_audio/config ./audio_config
```

常用配置项如下，修改 `audio_config/audio_config.json`：

```json
{
  "micphone_enable": 1,
  "micphone_name": "hw:0,0",
  "micphone_rate": 16000,
  "micphone_chn": 8,
  "voip_mode": 0,
  "mic_type": 0,
  "asr_mode": 2,
  "asr_channel": 3,
  "save_audio": 0
}
```

其中：

- `micphone_name`：麦克风设备号，需按 `ls /dev/snd` 的结果调整
- `mic_type`：`0` 表示环形麦克风阵列，`1` 表示线形麦克风阵列
- `asr_mode`：建议设为 `2`，表示持续输出 ASR 识别结果

启动 `ASR`：

```bash
source /opt/tros/humble/setup.bash
export GLOG_minloglevel=3
ros2 launch hobot_audio hobot_audio.launch.py
```

若启动后终端持续打印音频初始化日志，说明采集链路已拉起。联调时建议另开一个终端观察输出日志。

#### 4. TTS 部署

文本转语音部分建议直接使用 `hobot_tts`：

```bash
sudo apt update
sudo apt install -y tros-humble-hobot-tts
source /opt/tros/humble/setup.bash
```

首次运行需要下载并解压模型文件：

```bash
cd ~/edu_robot/upper_rdkx5
wget http://archive.d-robotics.cc/tts-model/tts_model.tar.gz
sudo tar -xf tts_model.tar.gz -C /opt/tros/${TROS_DISTRO}/lib/hobot_tts/
```

检查播放设备：

```bash
ls /dev/snd
```

若能看到类似 `pcmC0D1p` 的播放设备，通常表示音频输出设备已就绪。随后启动 `TTS` 节点：

```bash
source /opt/tros/humble/setup.bash
export GLOG_minloglevel=1
ros2 run hobot_tts hobot_tts
```

如果默认播放设备不对，可以手动指定，例如：

```bash
ros2 run hobot_tts hobot_tts --ros-args -p playback_device:="hw:1,1"
```

新开一个终端，发送一条测试播报：

```bash
source /opt/tros/humble/setup.bash
ros2 topic pub --once /tts_text std_msgs/msg/String "{data: \"你好，我已经完成文本转语音部署。\"}"
```

#### 5. 上位板联调顺序

建议按以下顺序完成上位板联调：

```bash
# 终端 1：启动 Qwen3
ollama serve

# 终端 2：启动 ASR
source /opt/tros/humble/setup.bash
export GLOG_minloglevel=3
ros2 launch hobot_audio hobot_audio.launch.py

# 终端 3：启动 TTS
source /opt/tros/humble/setup.bash
export GLOG_minloglevel=1
ros2 run hobot_tts hobot_tts
```

完成以上三个服务后，再接入你自己的业务程序，将 `ASR` 输出文本送入 `Qwen3`，再把 `Qwen3` 返回结果发布到 `/tts_text`，即可形成完整的语音交互闭环。

### 下位 RDK X5：边缘计算与视觉侧部署

下位 `RDK X5` 真实工程是一个基于 `PyQt5` 的功能中枢应用，入口为 `app.main`，用于承载天气、提醒、学习、作业、学生打卡、坐姿检测、健身评分、视频通话、安全巡检等页面能力。其部署重点不是启动一个独立的大仓库后端，而是：

1. 安装 Python GUI 与视觉依赖  
2. 配置内部边缘业务接口地址  
3. 准备摄像头、音频和姿态模型文件  
4. 启动功能中枢界面

#### 1. 同步当前项目到下位 RDK X5

目录结构应包含： 

```text
rdk_share/
├── requirements.txt
├── scripts/
│   └── start_function_hub.sh
└── app/
    ├── main.py
    ├── function_hub.py
    ├── config.py
    ├── workers.py
    ├── interfaces/
    └── pages/
```

进入工程根目录：

```bash
cd ~/rdk_share
```

#### 2. 安装系统依赖

由于该项目使用 `PyQt5 + PyQtWebEngine + OpenCV`，建议先安装系统层依赖：

```bash
sudo apt update
sudo apt install -y \
  python3 python3-pip python3-venv \
  python3-pyqt5 python3-pyqt5.qtwebengine \
  ffmpeg libgl1 libglib2.0-0 \
  v4l-utils alsa-utils
```

如果板端已经准备好了完整桌面环境，也建议先确认显示环境和摄像头是否正常：

```bash
python3 --version
v4l2-ctl --list-devices
ls /dev/video*
ls /dev/snd
```

#### 3. 安装 Python 依赖

项目中的 Python 依赖由 `requirements.txt` 管理，建议使用虚拟环境：

```bash
cd ~/rdk_share
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

当前依赖主要包括：

- `PyQt5`
- `PyQtWebEngine`
- `requests`
- `PyJWT`
- `websockets`
- `opencv-python`
- `numpy`
- `onnxruntime`

#### 4. 确认下位板接口能力

根据当前工程实现，下位板界面会通过内部边缘业务接口调用以下能力：

```text
/api/ui/page-command
/api/voice/dispatch
/api/weather/query
/api/learning/generate
/api/learning/explain
/api/homework/latest
/api/homework/submit
/api/homework/explain
/api/security/inspection/request
/api/security/inspection/upload
/api/image/generate
/api/attendance/clockin
/api/posture/analyze
/api/fitness/analyze
```

因此，在启动功能中枢前，需确保你的边缘服务已经在本机 `8090` 端口运行，并能够返回 `JSON`。

如果你已经实现了接口服务，可先做简单联通测试：

```bash
curl http://127.0.0.1:8090
```

#### 5. 准备本地视觉与多媒体资源

当前工程中，部分页面依赖本地摄像头、音频和模型文件：

- `StudentClockinPage`：使用本地摄像头进行学生打卡
- `SittingPosturePage`：默认读取 `/home/sunrise/rdk_yolov8_pose/yolov8n_pose_bayese_416x416_nv12.bin`
- `FitnessPage`：默认依赖姿态模型文件 `yolov8n_pose_bayese_416x416_nv12.bin`
- `SecurityInspectionPage`：通过内部边缘业务接口发起巡检请求

你至少需要确认以下内容：

```bash
ls /dev/video*
test -f /home/sunrise/rdk_yolov8_pose/yolov8n_pose_bayese_416x416_nv12.bin && echo "pose model ok"
```

如果模型文件路径不同，需要同步修改页面中的默认路径，重点包括：

- `app/pages/sitting_posture_page.py`
- `app/pages/fitness_page.py`

#### 6. 启动下位板功能中枢

项目提供了现成启动脚本：

```bash
cd ~/rdk_share
source .venv/bin/activate
bash scripts/start_function_hub.sh
```

该脚本本质上会执行：

```bash
python -m app.main
```

如果你希望直接启动，也可以手动执行：

```bash
cd ~/rdk_share
source .venv/bin/activate
python -m app.main
```

#### 7. 启动后的联动文件

功能中枢启动后，会在输出目录中监听以下文件：

```text
output/live_transcript.txt
output/page_command.json
```

用途如下：

- `live_transcript.txt`：用于展示实时语音转写内容
- `page_command.json`：用于通过内部边缘业务接口切换页面或下发页面指令

## 快速开始

建议按照以下顺序完成整机部署：

1. 先在上位 `RDK X5` 完成 `Qwen3`、`ASR` 与 `TTS` 的服务部署，并分别通过命令完成单项测试。
2. 再在下位 `RDK X5` 完成 Python 环境、系统依赖、内部边缘业务接口地址和输出目录配置。
3. 准备好本地摄像头、音频设备以及姿态模型文件，并按实际情况补齐 `ONNX` 推理适配层。
4. 启动下位板功能中枢，确认天气、学习、作业、巡检、视频、打卡、坐姿和健身等页面可正常打开。
5. 配置双板通信，将上位板语音链路与下位板页面联动接入同一业务流程。
6. 分别在学校巡检场景与家庭教育场景下进行联调测试。
7. 最后逐步启用问答、检测、提醒、绘画与专注统计等完整功能。
