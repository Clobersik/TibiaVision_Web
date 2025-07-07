# app/analysis.py
# Zaktualizowany moduł analizy, przystosowany do pracy z RQ i bazą danych.

import os
import cv2
import json
import time
import requests
import yt_dlp
import numpy as np
import easyocr
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# --- Konfiguracja Aplikacji dla Workera ---
# Worker potrzebuje kontekstu aplikacji, aby połączyć się z bazą danych.
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join('app', 'database', 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Import modeli po inicjalizacji db
from app.main import Job, FrameData

class TibiaFrameAnalyzer:
    """Klasa analizująca klatki wideo z gry Tibia."""
    def __init__(self, world_map_path, lang='en'):
        self.world_map = cv2.imread(world_map_path)
        if self.world_map is None: raise FileNotFoundError(f"Nie można wczytać mapy: {world_map_path}")
        self.world_map_gray = cv2.cvtColor(self.world_map, cv2.COLOR_BGR2GRAY)
        self.ocr_reader = easyocr.Reader([lang])
        self.last_frame_gray = None
        self.last_known_position = None
        self.tracking_points = None
        self.feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)
        self.lk_params = dict(winSize=(15, 15), maxLevel=2, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        self.ui_positions_cache = {}

    # ... (metody _find_ui_element, _extract_minimap, _detect_position, _analyze_battle_list
    #      pozostają takie same jak w poprzedniej wersji - dla zwięzłości pominięto) ...
    def _find_ui_element(self, frame_gray, template_path, cache_key):
        if cache_key in self.ui_positions_cache: return self.ui_positions_cache[cache_key]
        template = cv2.imread(template_path, 0)
        if template is None:
            if cache_key == 'minimap': return (frame_gray.shape[1] - 160, 10, 150, 150)
            if cache_key == 'battle_list': return (frame_gray.shape[1] - 160, 170, 150, 300)
            return None
        res = cv2.matchTemplate(frame_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val > 0.8:
            w, h = template.shape[::-1]
            if cache_key == 'minimap': pos = (max_loc[0], max_loc[1], 150, 150)
            elif cache_key == 'battle_list': pos = (max_loc[0], max_loc[1], 150, 300)
            else: pos = (max_loc[0], max_loc[1], w, h)
            self.ui_positions_cache[cache_key] = pos
            return pos
        return None

    def _extract_minimap(self, frame, frame_gray):
        pos = self._find_ui_element(frame_gray, 'app/templates/assets/minimap_corner.png', 'minimap')
        if pos: x, y, w, h = pos; return frame[y:y+h, x:x+w]
        return None

    def _detect_position(self, minimap_gray):
        if minimap_gray is None or minimap_gray.size == 0: return None
        result = cv2.matchTemplate(self.world_map_gray, minimap_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val >= 0.7:
            w, h = minimap_gray.shape[::-1]
            self.last_known_position = (max_loc[0], max_loc[1], w, h)
            return self.last_known_position
        return None
        
    def _analyze_battle_list(self, frame, frame_gray):
        pos = self._find_ui_element(frame_gray, 'app/templates/assets/battle_list_header.png', 'battle_list')
        if not pos: return []
        x, y, w, h = pos
        battle_list_roi = frame[y:y+h, x:x+w]
        entities, entry_height = [], 22
        for i in range(h // entry_height):
            entry_roi = battle_list_roi[i * entry_height:(i + 1) * entry_height, :]
            if np.mean(entry_roi) < 25: continue
            ocr_result = self.ocr_reader.readtext(entry_roi[:, 5:], detail=0, paragraph=False)
            if ocr_result:
                name = " ".join(ocr_result)
                hp_bar_roi = entry_roi[12:15, 5:w-5]
                hsv_hp = cv2.cvtColor(hp_bar_roi, cv2.COLOR_BGR2HSV)
                mask_health = cv2.inRange(hsv_hp, np.array([30, 100, 100]), np.array([90, 255, 255]))
                hp_percent = (cv2.countNonZero(mask_health) / (hp_bar_roi.shape[1] * hp_bar_roi.shape[0])) * 100
                is_target = np.mean(entry_roi[:, 0:3]) > 100
                entities.append({"name": name, "hp_percent": round(hp_percent, 2), "is_target": is_target})
        return entities

    def analyze_frame(self, frame):
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        minimap_frame = self._extract_minimap(frame, frame_gray)
        current_position = None
        if minimap_frame is not None:
            minimap_gray = cv2.cvtColor(minimap_frame, cv2.COLOR_BGR2GRAY)
            if self.last_frame_gray is None or self.last_known_position is None:
                current_position = self._detect_position(minimap_gray)
                if current_position: self.tracking_points = cv2.goodFeaturesToTrack(minimap_gray, mask=None, **self.feature_params)
            else:
                if self.tracking_points is not None and len(self.tracking_points) > 0:
                    new_points, status, _ = cv2.calcOpticalFlowPyrLK(self.last_frame_gray, minimap_gray, self.tracking_points, None, **self.lk_params)
                    good_new = new_points[status == 1]
                    if len(good_new) > 5:
                        dx = np.mean(new_points[status==1,0] - self.tracking_points[status==1,0])
                        dy = np.mean(new_points[status==1,1] - self.tracking_points[status==1,1])
                        x, y, w, h = self.last_known_position
                        current_position = (x + dx, y + dy, w, h)
                        self.last_known_position = current_position
                        self.tracking_points = good_new.reshape(-1, 1, 2)
                    else: self.last_known_position = None
                else: self.last_known_position = None
            self.last_frame_gray = minimap_gray.copy()
        
        battle_list_entities = self._analyze_battle_list(frame, frame_gray)
        h, w, _ = frame.shape
        hp_bar_roi, mana_bar_roi = frame[h-30:h-20, 10:110], frame[h-20:h-10, 10:110]
        mask_hp = cv2.inRange(cv2.cvtColor(hp_bar_roi, cv2.COLOR_BGR2HSV), np.array([0, 120, 70]), np.array([10, 255, 255]))
        mask_mana = cv2.inRange(cv2.cvtColor(mana_bar_roi, cv2.COLOR_BGR2HSV), np.array([100, 150, 0]), np.array([140, 255, 255]))
        hp_percent = (cv2.countNonZero(mask_hp) / (hp_bar_roi.size / 3)) * 100
        mana_percent = (cv2.countNonZero(mask_mana) / (mana_bar_roi.size / 3)) * 100
        
        results = {"player_coords": None, "stats": {"hp": round(hp_percent, 2), "mana": round(mana_percent, 2)}, "battle_list": battle_list_entities}
        if current_position: x, y, w, h = current_position; results["player_coords"] = {"x": round(x + w/2), "y": round(y + h/2), "z": 7}
        return results

def download_video(source_type, source_data, target_path):
    # ... (bez zmian) ...
    if source_type == 'url':
        with requests.get(source_data, stream=True) as r: r.raise_for_status(); open(target_path, 'wb').writelines(r.iter_content(8192))
    elif source_type == 'youtube':
        with yt_dlp.YoutubeDL({'format': 'best/best', 'outtmpl': target_path}) as ydl: ydl.download([source_data])

def run_analysis(job_id, source_type, source_data, frame_skip, upload_path=None):
    """Główna funkcja analityczna, uruchamiana przez workera RQ."""
    with app.app_context():
        job = Job.query.get(job_id)
        if not job: return

        job.status = 'processing'
        db.session.commit()
        
        try:
            video_path = upload_path
            if source_type != 'upload':
                video_filename = f"{job_id}.mp4"
                video_path = os.path.join('app', 'uploads', video_filename)
                download_video(source_type, source_data, video_path)

            analyzer = TibiaFrameAnalyzer('map.png')
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_number = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break

                if frame_number % (frame_skip + 1) == 0:
                    analysis_result = analyzer.analyze_frame(frame)
                    
                    # Zapis wyników do bazy danych
                    frame_data = FrameData(
                        job_id=job_id,
                        frame_number=frame_number,
                        timestamp=cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0,
                        player_coords_json=json.dumps(analysis_result['player_coords']),
                        stats_json=json.dumps(analysis_result['stats']),
                        battle_list_json=json.dumps(analysis_result['battle_list'])
                    )
                    db.session.add(frame_data)
                
                if frame_number % 50 == 0: # Zapisuj postęp co 50 klatek
                    job.progress = int((frame_number / total_frames) * 100)
                    db.session.commit()

                frame_number += 1
            
            job.progress = 100
            job.status = 'completed'
            db.session.commit()

        except Exception as e:
            job.status = f'failed: {str(e)}'
            db.session.commit()
            print(f"Błąd w zadaniu {job_id}: {e}")
        finally:
            if source_type != 'upload' and video_path and os.path.exists(video_path):
                os.remove(video_path)
