# Danh sách thư viện để PyInstaller gói vào exe (code app\ nằm ngoài exe nên phải liệt kê ở đây).
# Không bao giờ được gọi — chỉ để PyInstaller "nhìn thấy" các import.
def _never_called():
    import asyncio, threading, time, ctypes, importlib.util, json, os, sys, hashlib, urllib.request, urllib.error
    import tempfile, shutil, socket, queue, io, colorsys, random, re, math, subprocess, wave, traceback
    import numpy, pygame, pygame.freetype
    import tkinter, tkinter.ttk, tkinter.messagebox, tkinter.filedialog
    from PIL import Image, ImageDraw
    import soundfile, soxr
    import pyvirtualcam
    import TikTokLive
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import ConnectEvent, DisconnectEvent, CommentEvent, GiftEvent, LikeEvent, JoinEvent, FollowEvent, ShareEvent
    from TikTokLive.client.web.web_settings import WebDefaults
    import vieneu, vieneu.factory, vieneu.v3turbo, vieneu.v3nano, vieneu.base, vieneu.utils
    import vieneu._v3_turbo_engine.onnx_runtime_lite, vieneu._v3_turbo_engine.onnx_denoiser
    import vieneu_utils, sea_g2p, onnxruntime, tokenizers, kaldi_native_fbank, huggingface_hub, yaml
