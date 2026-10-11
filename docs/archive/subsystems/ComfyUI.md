# рџ§  Colab-ComfyUI.ipynb вЂ” РЈРїСЂР°РІР»СЏРµРјРѕРµ РІРёРґРµРѕ РґР»СЏ "РќР°СЃР»РµРґРёРµ РђСЂРєР°РёРјР°"

# 1. РЈСЃС‚Р°РЅРѕРІРєР° Р±Р°Р·РѕРІС‹С… РїР°РєРµС‚РѕРІ
!apt -y update -qq
!apt -y install -qq libgl1-mesa-glx wget git

# 2. РљР»РѕРЅРёСЂСѓРµРј ComfyUI
%cd /content
!git clone https://github.com/comfyanonymous/ComfyUI.git
%cd ComfyUI

# 3. РЈСЃС‚Р°РЅРѕРІРєР° Р·Р°РІРёСЃРёРјРѕСЃС‚РµР№
!pip install -r requirements.txt

# 4. РџРѕРґРєР»СЋС‡Р°РµРј Google Drive
from google.colab import drive
drive.mount('/content/drive')

GDRIVE = '/content/drive/MyDrive/ComfyUI'

# 5. РЎРѕР·РґР°С‘Рј РїР°РїРєРё РІ Google Drive
import os
for folder in ['models/svd', 'input', 'output', 'custom_nodes', 'user']:
    os.makedirs(f"{GDRIVE}/{folder}", exist_ok=True)

# 6. РЎРёРјРІРѕР»РёС‡РµСЃРєРёРµ СЃСЃС‹Р»РєРё (РёСЃРїСЂР°РІР»РµРЅРѕ: РѕРґРёРЅ ComfyUI)
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

print("вњ… РЎРёРјРІРѕР»РёС‡РµСЃРєРёРµ СЃСЃС‹Р»РєРё РЅР° Google Drive СЃРѕР·РґР°РЅС‹.")

# 7. РЈСЃС‚Р°РЅРѕРІРєР° РєР°СЃС‚РѕРјРЅС‹С… РЅРѕРґ
print("рџ”§ РЈСЃС‚Р°РЅРѕРІРєР° РєР°СЃС‚РѕРјРЅС‹С… РЅРѕРґ...")

%cd /content/ComfyUI/custom_nodes

!git clone https://github.com/ltdrdata/ComfyUI-Manager.git ComfyUI-Manager --quiet
!git clone https://github.com/AlekPet/comfyui_custom_nodes_alekpet.git comfyui_custom_nodes_alekpet --quiet
!git clone https://github.com/comfyanonymous/ComfyUI_RH_UNO.git ComfyUI_RH_UNO --quiet

print("вњ… РљР°СЃС‚РѕРјРЅС‹Рµ РЅРѕРґС‹ СѓСЃС‚Р°РЅРѕРІР»РµРЅС‹.")

# 8. РЈСЃС‚Р°РЅРѕРІРєР° SVD (Stable Video Diffusion)
!git clone https://github.com/Aspock/StableVideoDiffusion-ComfyUI StableVideoDiffusion-ComfyUI --quiet

# 9. Р—Р°РіСЂСѓР·РєР° РјРѕРґРµР»Рё SVD
SVDMODEL = f"{GDRIVE}/models/svd/svd_xt.safetensors"
if not os.path.exists(SVDMODEL):
    print("рџ“Ґ Р—Р°РіСЂСѓР·РєР° SVD-РјРѕРґРµР»Рё (1-2 РјРёРЅ)...")
    !wget -O "{SVDMODEL}" https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/resolve/main/svd_xt.safetensors
else:
    print("вњ… SVD-РјРѕРґРµР»СЊ СѓР¶Рµ Р·Р°РіСЂСѓР¶РµРЅР°.")

# 10. РЈСЃС‚Р°РЅРѕРІРєР° ngrok (РґР»СЏ API)
!wget -O ngrok.tgz https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
!tar -xvzf ngrok.tgz
!chmod +x ngrok
!./ngrok authtoken YOUR_TOKEN_HERE  # в†ђ Р—Р°РјРµРЅРё РЅР° СЃРІРѕР№

import subprocess
import threading
import time
import requests

def run_ngrok():
    subprocess.Popen(['./ngrok', 'http', '8188'], stdout=subprocess.DEVNULL).wait()

threading.Thread(target=run_ngrok, daemon=True).start()

# Р–РґС‘Рј С‚СѓРЅРЅРµР»СЊ
time.sleep(3)
try:
    public_url = requests.get('http://localhost:4040/api/tunnels').json()['tunnels'][0]['public_url']
    print(f"вњ… ComfyUI РґРѕСЃС‚СѓРїРµРЅ: {public_url}")
except:
    print("вќЊ Ngrok РЅРµ Р·Р°РїСѓСЃС‚РёР»СЃСЏ. РџСЂРѕРІРµСЂСЊ С‚РѕРєРµРЅ.")

# 11. Р—Р°РїСѓСЃРє ComfyUI
%cd /content/ComfyUI
!python main.py --listen 0.0.0.0 --port 8188 --cuda-device 0
