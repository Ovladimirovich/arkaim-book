# 🧠 Colab-ComfyUI.ipynb — Управляемое видео для "Наследие Аркаима"

# 1. Установка базовых пакетов
!apt -y update -qq
!apt -y install -qq libgl1-mesa-glx wget git

# 2. Клонируем ComfyUI
%cd /content
!git clone https://github.com/comfyanonymous/ComfyUI.git
%cd ComfyUI

# 3. Установка зависимостей
!pip install -r requirements.txt

# 4. Подключаем Google Drive
from google.colab import drive
drive.mount('/content/drive')

GDRIVE = '/content/drive/MyDrive/ComfyUI'

# 5. Создаём папки в Google Drive
import os
for folder in ['models/svd', 'input', 'output', 'custom_nodes', 'user']:
    os.makedirs(f"{GDRIVE}/{folder}", exist_ok=True)

# 6. Символические ссылки (исправлено: один ComfyUI)
LINKS = {
    'models': f'{GDRIVE}/models',
    'custom_nodes': f'{GDRIVE}/custom_nodes',
    'input': f'{GDRIVE}/input',
    'output': f'{GDRIVE}/output',
    'user': f'{GDRIVE}/user'
}

for name, target in LINKS.items():
    source = f'/content/ComfyUI/{name}'
    if os.path.islink(source) or os.path.isdir(source):
        !rm -rf "{source}"
    os.symlink(target, source)

print("✅ Символические ссылки на Google Drive созданы.")

# 7. Установка кастомных нод
print("🔧 Установка кастомных нод...")

%cd /content/ComfyUI/custom_nodes

!git clone https://github.com/ltdrdata/ComfyUI-Manager.git ComfyUI-Manager --quiet
!git clone https://github.com/AlekPet/comfyui_custom_nodes_alekpet.git comfyui_custom_nodes_alekpet --quiet
!git clone https://github.com/comfyanonymous/ComfyUI_RH_UNO.git ComfyUI_RH_UNO --quiet

print("✅ Кастомные ноды установлены.")

# 8. Установка SVD (Stable Video Diffusion)
!git clone https://github.com/Aspock/StableVideoDiffusion-ComfyUI StableVideoDiffusion-ComfyUI --quiet

# 9. Загрузка модели SVD
SVDMODEL = f"{GDRIVE}/models/svd/svd_xt.safetensors"
if not os.path.exists(SVDMODEL):
    print("📥 Загрузка SVD-модели (1-2 мин)...")
    !wget -O "{SVDMODEL}" https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/resolve/main/svd_xt.safetensors
else:
    print("✅ SVD-модель уже загружена.")

# 10. Установка ngrok (для API)
!wget -O ngrok.tgz https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
!tar -xvzf ngrok.tgz
!chmod +x ngrok
!./ngrok authtoken YOUR_TOKEN_HERE  # ← Замени на свой

import subprocess
import threading
import time
import requests

def run_ngrok():
    subprocess.Popen(['./ngrok', 'http', '8188'], stdout=subprocess.DEVNULL).wait()

threading.Thread(target=run_ngrok, daemon=True).start()

# Ждём туннель
time.sleep(3)
try:
    public_url = requests.get('http://localhost:4040/api/tunnels').json()['tunnels'][0]['public_url']
    print(f"✅ ComfyUI доступен: {public_url}")
except:
    print("❌ Ngrok не запустился. Проверь токен.")

# 11. Запуск ComfyUI
%cd /content/ComfyUI
!python main.py --listen 0.0.0.0 --port 8188 --cuda-device 0
