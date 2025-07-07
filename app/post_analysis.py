# app/post_analysis.py
# Moduł do analizy i wizualizacji wyników po zakończeniu przetwarzania.

import cv2
import numpy as np
from sklearn.cluster import DBSCAN

def visualize_path_and_hunt_area(coords, world_map_path, output_path):
    """
    Rysuje ścieżkę gracza na mapie świata, identyfikuje i zaznacza 
    główny obszar polowania (hunt).
    """
    world_map = cv2.imread(world_map_path)
    if world_map is None:
        raise FileNotFoundError("Nie można wczytać mapy świata do wizualizacji.")

    # Rysowanie ścieżki
    points = np.array(coords, np.int32)
    cv2.polylines(world_map, [points], isClosed=False, color=(75, 0, 130), thickness=2)

    # Identyfikacja obszaru polowania za pomocą DBSCAN
    if len(coords) > 50: # Wymagaj minimalnej liczby punktów do analizy
        # eps: maksymalna odległość między próbkami, aby uznać je za sąsiadów
        # min_samples: liczba próbek w sąsiedztwie, aby uznać punkt za rdzeń
        db = DBSCAN(eps=50, min_samples=20).fit(coords)
        labels = db.labels_
        
        # Znajdź największy klaster (ignorując szum oznaczony jako -1)
        unique_labels = set(labels)
        if len(unique_labels) > 1:
            core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
            core_samples_mask[db.core_sample_indices_] = True
            
            largest_cluster_label = -1
            max_size = 0
            for k in unique_labels:
                if k == -1: continue # Pomiń szum
                
                class_member_mask = (labels == k)
                size = np.sum(class_member_mask & core_samples_mask)
                if size > max_size:
                    max_size = size
                    largest_cluster_label = k
            
            # Jeśli znaleziono znaczący klaster, zaznacz go
            if largest_cluster_label != -1:
                cluster_points = points[labels == largest_cluster_label]
                # Oblicz prostokąt otaczający klaster
                x, y, w, h = cv2.boundingRect(cluster_points)
                # Narysuj półprzezroczysty prostokąt
                sub_img = world_map[y:y+h, x:x+w]
                white_rect = np.ones(sub_img.shape, dtype=np.uint8) * 255
                res = cv2.addWeighted(sub_img, 0.7, white_rect, 0.3, 1.0)
                world_map[y:y+h, x:x+w] = res
                # Dodaj etykietę
                cv2.putText(world_map, "Hunt Area", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)


    # Zapisz wynikowy obraz
    cv2.imwrite(output_path, world_map)
    print(f"Wizualizacja ścieżki zapisana w: {output_path}")
