# Multimodal Intelligent Educational Companion Robot Based on RDK X5

## Project Overview

This project is a multimodal intelligent educational companion robot built on the `RDK X5` platform. It is designed for two core scenarios, school teaching and home education, and integrates large language models, voice interaction, visual perception, and edge computing to provide functions such as patrol inspection, learning assistance, behavior detection, remote companionship, and daily reminders.

The overall system uses a dual `RDK X5` collaborative architecture:

- `Upper RDK X5`: responsible for `Qwen3 + ASR + TTS`, used for natural language understanding, speech recognition, speech synthesis, and intelligent Q&A interaction.
- `Lower RDK X5`: responsible for edge computing, video stream reading, and vision-related tasks, supporting patrol, recognition, detection, and analysis capabilities.

The project emphasizes practicality and companionship in educational scenarios. It can serve campus safety and teaching management, and also provide learning assistance, health reminders, and intelligent interaction in home environments.

## Key Features

- Dual `RDK X5` collaboration, balancing LLM interaction and local vision computing
- Supports school patrols, student state perception, and teaching Q&A assistance
- Supports weather reports, reminders, posture detection, and fitness scoring in home scenarios
- Supports natural voice interaction and educational content assistance
- Supports multimodal capability fusion, covering speech, vision, and task scheduling scenarios

## Application Scenarios

### School Scenarios

1. Supports regular teaching-building patrols through `SLAM + path planning`, checking classroom lighting status and whether students are present to help ensure campus and student safety.
2. Supports student attendance and emotion recognition. Parent-side and teacher-side apps can view attendance and emotion status to help teachers and parents understand student conditions in time.
3. Supports remote teacher question publishing. Students can answer through the educational robot; when they encounter questions they cannot solve, they can ask `Qwen3` for help, and teachers can view student answers to improve learning efficiency.

### Home Education Scenarios

1. The arts-and-literacy home page includes a weather page and supports voice weather reports, helping students understand weather information more conveniently.
2. Supports setting reminder tasks through voice assistance and triggering voice prompts at the specified time.
3. Supports student posture detection, helping students maintain good posture and triggering reminders when poor posture is detected.
4. Includes a self-developed fitness scoring system that supports detection and scoring of 4 actions to help improve students' physical fitness.
5. After pairing with the companion app, supports remote video voice calls between students and parents to improve companionship and safety.
6. Includes learning question generation based on a large language model for notification-style learning, and supports asking `Qwen3` for answers to improve comprehensive learning ability.
7. Supports calling an image-generation model for drawing and creation, enhancing students' creativity and expression.
8. Supports focus mode, summarizing the distribution of focus time throughout the day to help build good study habits.

## System Architecture

The system uses a layered dual `RDK X5` collaborative architecture, with responsibilities divided as follows:

### Upper RDK X5: Qwen3 + ASR + TTS

The upper `RDK X5` is mainly responsible for the intelligent interaction pipeline, focusing on the following capabilities:

- Deploys `Qwen3` for learning Q&A, knowledge assistance, and conversational interaction
- Deploys `ASR` to convert speech input into text instructions
- Deploys `TTS` to convert system responses into natural spoken output
- Serves as the human-machine interaction hub, passing interaction results or task requests to the lower board

### Lower RDK X5: Edge Computing and Vision Side

The lower `RDK X5` is mainly responsible for local vision and edge task handling, focusing on the following capabilities:

- Video stream reading and processing
- Environmental perception and state recognition during school patrols
- Student attendance, emotion recognition, posture detection, and action detection
- Vision analysis and focus-related statistics in home scenarios
- Receiving tasks from the upper board and completing local perception and analysis execution

The overall collaboration sequence is: the upper board first completes language and speech interaction capabilities, the lower board then completes vision and edge-computing deployment, and finally the two boards are linked together.

## Deployment Guide

### Upper RDK X5: Qwen3 + ASR + TTS Deployment

The upper `RDK X5` mainly completes deployment of the large-model and speech-interaction pipeline. The flow below is organized as `large-model environment -> Qwen3 -> ASR -> TTS -> integration`, and is suitable as the core deployment section in the README.

#### 1. Basic Environment Setup

It is recommended to use `Ubuntu 22.04`. Install the basic dependencies first:

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

If you need to verify the board environment, run:

```bash
uname -a
python3 --version
docker --version
ls /dev/snd
```

#### 2. Qwen3 Deployment

This section provides a common local deployment method for `Qwen3` inference and chat access. The recommended approach is `Ollama + WebUI`, which is convenient for later integration with the speech pipeline.

Install `Ollama`:

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable ollama --now
```

Pull and test the `Qwen3` model:

```bash
ollama pull qwen3:4b
ollama run qwen3:4b
```

If you want a local visual chat entry point, start `Open WebUI`:

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

After startup, verify the services:

```bash
curl http://127.0.0.1:11434/api/tags
docker ps
```

#### 3. ASR Deployment

For speech recognition, it is recommended to use the audio capabilities of `RDK X5` directly to complete the offline speech pipeline. First install the audio package:

```bash
sudo apt update
sudo apt install -y tros-humble-hobot-audio
source /opt/tros/humble/setup.bash
```

If you use a four-microphone array or audio driver board, first check whether the hardware is recognized:

```bash
i2cdetect -r -y 0
ls /dev/snd
```

Then copy the default configuration file so you can adjust it according to your hardware:

```bash
cd ~/edu_robot/upper_rdkx5
cp -r /opt/tros/${TROS_DISTRO}/lib/hobot_audio/config ./audio_config
```

Common configuration items can be modified in `audio_config/audio_config.json`:

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

Where:

- `micphone_name`: microphone device name, adjust based on the result of `ls /dev/snd`
- `mic_type`: `0` means circular microphone array, `1` means linear microphone array
- `asr_mode`: recommended value is `2`, which means ASR recognition results are continuously output

Start `ASR`:

```bash
source /opt/tros/humble/setup.bash
export GLOG_minloglevel=3
ros2 launch hobot_audio hobot_audio.launch.py
```

If the terminal keeps printing audio initialization logs after startup, it means the capture pipeline has been brought up successfully. During integration, it is recommended to open another terminal to watch the logs.

#### 4. TTS Deployment

For text-to-speech, it is recommended to use `hobot_tts` directly:

```bash
sudo apt update
sudo apt install -y tros-humble-hobot-tts
source /opt/tros/humble/setup.bash
```

The first run requires downloading and extracting the model files:

```bash
cd ~/edu_robot/upper_rdkx5
wget http://archive.d-robotics.cc/tts-model/tts_model.tar.gz
sudo tar -xf tts_model.tar.gz -C /opt/tros/${TROS_DISTRO}/lib/hobot_tts/
```

Check the playback device:

```bash
ls /dev/snd
```

If you can see a playback device similar to `pcmC0D1p`, it usually means the audio output device is ready. Then start the `TTS` node:

```bash
source /opt/tros/humble/setup.bash
export GLOG_minloglevel=1
ros2 run hobot_tts hobot_tts
```

If the default playback device is incorrect, you can specify it manually, for example:

```bash
ros2 run hobot_tts hobot_tts --ros-args -p playback_device:="hw:1,1"
```

Open another terminal and send a test message:

```bash
source /opt/tros/humble/setup.bash
ros2 topic pub --once /tts_text std_msgs/msg/String "{data: \"Hello, I have finished the text-to-speech deployment.\"}"
```

#### 5. Upper Board Integration Order

It is recommended to complete upper-board integration in the following order:

```bash
# Terminal 1: Start Qwen3
ollama serve

# Terminal 2: Start ASR
source /opt/tros/humble/setup.bash
export GLOG_minloglevel=3
ros2 launch hobot_audio hobot_audio.launch.py

# Terminal 3: Start TTS
source /opt/tros/humble/setup.bash
export GLOG_minloglevel=1
ros2 run hobot_tts hobot_tts
```

After the three services above are running, connect your own business logic. Send the text output from `ASR` into `Qwen3`, then publish the `Qwen3` result to `/tts_text` to complete the full speech interaction loop.

### Lower RDK X5: Edge Computing and Vision Side Deployment

The actual lower-board project is a `PyQt5`-based functional hub application. It is used to support weather, reminders, learning, homework, student attendance, posture detection, fitness scoring, video calls, and security patrol pages, and it coordinates with the upper `RDK X5` through internal edge business interfaces. The deployment focus is not on starting a standalone backend, but on:

1. Installing Python GUI and vision dependencies
2. Configuring internal edge business interface addresses
3. Preparing camera, audio, and posture model files
4. Launching the functional hub interface

#### 1. Sync the Current Project to the Lower RDK X5

The directory structure should include:

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

Enter the project root:

```bash
cd ~/rdk_share
```

#### 2. Install System Dependencies

Because the project uses `PyQt5 + PyQtWebEngine + OpenCV`, it is recommended to install the system dependencies first:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-pip python3-venv \
  python3-pyqt5 python3-pyqt5.qtwebengine \
  ffmpeg libgl1 libglib2.0-0 \
  v4l-utils alsa-utils
```

If the board already has a complete desktop environment, it is also a good idea to verify that the display environment and camera are working properly:

```bash
python3 --version
v4l2-ctl --list-devices
ls /dev/video*
ls /dev/snd
```

#### 3. Install Python Dependencies

Python dependencies are managed through `requirements.txt`. It is recommended to use a virtual environment:

```bash
cd ~/rdk_share
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

The current dependencies mainly include:

- `PyQt5`
- `PyQtWebEngine`
- `requests`
- `PyJWT`
- `websockets`
- `opencv-python`
- `numpy`
- `onnxruntime`

#### 4. Verify Lower-Board API Capabilities

According to the current implementation, the lower-board UI will call the following local edge APIs:

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

Therefore, before starting the functional hub, make sure your edge service is already running on local port `8090` and can return `JSON`.

If you have already implemented the API service, you can first do a simple connectivity test:

```bash
curl http://127.0.0.1:8090
```

#### 5. Prepare Local Vision and Multimedia Resources

In the current project, some pages depend on local camera, audio, and model files:

- `StudentClockinPage`: uses the local camera for student attendance
- `SittingPosturePage`: reads `/home/sunrise/rdk_yolov8_pose/yolov8n_pose_bayese_416x416_nv12.bin` by default
- `FitnessPage`: also relies on the posture model file `yolov8n_pose_bayese_416x416_nv12.bin`
- `SecurityInspectionPage`: triggers patrol requests through the edge API

You need to confirm at least the following:

```bash
ls /dev/video*
test -f /home/sunrise/rdk_yolov8_pose/yolov8n_pose_bayese_416x416_nv12.bin && echo "pose model ok"
```

If the model file path is different, update the default path in the UI accordingly, especially in:

- `app/pages/sitting_posture_page.py`
- `app/pages/fitness_page.py`

#### 6. Start the Lower-Board Functional Hub

The project provides a ready-to-use startup script:

```bash
cd ~/rdk_share
source .venv/bin/activate
bash scripts/start_function_hub.sh
```

This script essentially runs:

```bash
python -m app.main
```

If you prefer to start it directly, you can also run:

```bash
cd ~/rdk_share
source .venv/bin/activate
python -m app.main
```

#### 7. Linked Files After Startup

After the functional hub starts, it will watch the following files in the output directory:

```text
output/live_transcript.txt
output/page_command.json
```

Usage:

- `live_transcript.txt`: used to display real-time speech-to-text content
- `page_command.json`: used to switch pages or send page instructions through an internal edge business interface

## Quick Start

It is recommended to complete the whole system deployment in the following order:

1. First, complete the `Qwen3`, `ASR`, and `TTS` service deployment on the upper `RDK X5`, and verify each service individually through the corresponding commands.
2. Then, complete the Python environment, system dependencies, edge API address, and output directory configuration on the lower `RDK X5`.
3. Prepare the local camera, audio devices, and posture model files, and supplement the `ONNX` inference adaptation layer according to the actual situation.
4. Start the lower-board functional hub and confirm that the weather, learning, homework, patrol, video, attendance, posture, and fitness pages can open normally.
5. Configure dual-board communication so that the speech pipeline on the upper board and the pages on the lower board are integrated into the same business flow.
6. Perform integration testing separately in the school patrol scenario and the home education scenario.
7. Finally, enable the complete functions such as Q&A, detection, reminders, drawing, and focus statistics step by step.
