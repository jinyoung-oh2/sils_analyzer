import math
import os
import json
import matplotlib
matplotlib.use("Agg")  # GUI 백엔드 설정 (파일로 저장)
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches
from route_extracter import RouteExtractor
from file_input_manager import FileInputManager 



class RoutePlotter(RouteExtractor):
    """
    RouteExtractor를 상속받아 각 event별로 ISILS, SILS Safe Path, Base Route,
    Own Ship, 그리고 Target Ships를 플롯하는 클래스.
    이벤트별로 별도의 플롯 파일을 생성함.
    """
    def __init__(self, sils_json_data, isils_json_data):
        super().__init__(sils_json_data, isils_json_data)

    def get_safe_path(self, safe_paths, idx):
        """
        주어진 safe_paths 리스트에서, 인덱스 idx에 해당하는 safe path가 없으면
        이전 이벤트들의 safe path를 순차적으로 확인하여 처음 만나는 값을 반환합니다.
        만약 모두 없다면 None을 반환합니다.
        """
        while idx >= 0:
            if idx < len(safe_paths) and safe_paths[idx]:
                return safe_paths[idx]
            idx -= 1
        return None

    def get_route_coordinates(self, route):
        """주어진 route의 각 point에서 위도와 경도 리스트를 추출."""
        latitudes = [point["position"]["latitude"] for point in route]
        longitudes = [point["position"]["longitude"] for point in route]
        return latitudes, longitudes

    def set_axis_limits_based_on_base_route(self, ax):
        """
        base route의 좌표를 기준으로 플롯의 x, y 범위를 정사각형으로 고정.
        base route가 없으면 아무 작업도 하지 않음.
        """
        if not self.base_route:
            return

        try:
            lat_base, lon_base = self.get_route_coordinates(self.base_route)
            lat_min, lat_max = min(lat_base), max(lat_base)
            lon_min, lon_max = min(lon_base), max(lon_base)
            lat_range = lat_max - lat_min
            lon_range = lon_max - lon_min
            max_range = max(lat_range, lon_range)

            # 중앙 좌표 계산
            lat_mid = (lat_min + lat_max) / 2
            lon_mid = (lon_min + lon_max) / 2

            # 약간의 여백(margin)을 추가할 수 있음 (예: 10%)
            margin = max_range * 0.1
            half_range = max_range / 2 + margin

            ax.set_xlim(lon_mid - half_range, lon_mid + half_range)
            ax.set_ylim(lat_mid - half_range, lat_mid + half_range)
            ax.set_aspect('equal', adjustable='datalim')
        except Exception as e:
            print(f"Base Route를 기반으로 축 설정 실패: {e}")

    def draw_ship(self, ax, lon, lat, heading, color, ship_length=230, ship_width=30, scale=10.0, shape='star'):
        """
        실제 ship_length (m), ship_width (m)를 사용하여, 위도/경도 단위로 변환한 배 모양(삼각형 또는 별)을 그린다.
        
        :param scale: 배 크기 조정을 위한 스케일링 팩터.
        :param shape: "ship"이면 기존 삼각형 모양, "star"이면 별 모양으로 그림.
        """
        if shape == 'star':
                # m -> degree 변환 (위도 기준)
                deg_per_meter = (1 / 111320) * scale
                # 별의 outer_radius를 ship_length의 절반으로 잡고, inner_radius는 outer_radius의 0.5배로 설정 (필요시 조정)
                outer_radius = (ship_length / 2) * deg_per_meter  
                inner_radius = outer_radius * 0.5  
                
                # 5각 별은 10개의 점(외부, 내부가 번갈아 나옴)으로 구성됨.
                vertices = []
                for i in range(10):
                    angle_deg = i * 36  # 360/10 = 36도 간격
                    r = outer_radius if i % 2 == 0 else inner_radius
                    x = r * np.sin(np.radians(angle_deg))
                    y = r * np.cos(np.radians(angle_deg))
                    vertices.append([x, y])
                vertices = np.array(vertices)
                
                # heading (도 단위)를 라디안으로 변환 후 회전 행렬 구성 (선박에서 0°가 정북, 시계방향 증가)
                angle = np.radians(-heading)
                rotation_matrix = np.array([
                    [np.cos(angle), -np.sin(angle)],
                    [np.sin(angle),  np.cos(angle)]
                ])
                rotated_vertices = vertices.dot(rotation_matrix.T)
                # 실제 좌표 (lon, lat)로 평행이동
                rotated_vertices[:, 0] += lon
                rotated_vertices[:, 1] += lat
                
                star_polygon = patches.Polygon(
                    rotated_vertices, closed=True,
                    facecolor=color, edgecolor=color, lw=2, alpha=0.9, zorder=5
                )
                ax.add_patch(star_polygon)
        else:
            # 기존 ship(삼각형) 모양 그리기
            deg_per_meter = (1 / 111320) * scale  
            L_deg = ship_length * deg_per_meter  # 배 길이 (위도 단위)
            W_deg = ship_width * deg_per_meter   # 배 폭 (위도 단위)

            vertices = np.array([
                [0, L_deg/2 + L_deg/6],         # Bow: (0, 2/3 * L_deg)
                [-W_deg/2, -L_deg/2 + L_deg/6],   # Stern left: (-W_deg/2, -L_deg/3)
                [W_deg/2, -L_deg/2 + L_deg/6]     # Stern right: (W_deg/2, -L_deg/3)
            ])
            
            angle = np.radians(-heading)
            rotation_matrix = np.array([
                [np.cos(angle), -np.sin(angle)],
                [np.sin(angle),  np.cos(angle)]
            ])
            rotated_vertices = vertices.dot(rotation_matrix.T)
            rotated_vertices[:, 0] += lon
            rotated_vertices[:, 1] += lat

            ship_polygon = patches.Polygon(
                rotated_vertices, closed=True,
                facecolor=color, edgecolor='red', lw=2, alpha=0.9, zorder=5
            )
            ax.add_patch(ship_polygon)

    def plot_all(self, output_path_pattern, option="both"):
        """
        이벤트별로 플롯을 생성하여 저장.
        
        :param output_path_pattern: 예) "result/scen_301_event{}.png"
                                    {}에 이벤트 인덱스가 들어감.
        :param option: "both", "sils", "isils" 중 하나.
                       "both": SILS와 ISILS 모두 플롯
                       "sils": SILS 데이터만 플롯
                       "isils": ISILS 데이터만 플롯
        """
        sils_event_count = len(self.sils_event_data) if hasattr(self, 'sils_event_data') and self.sils_event_data is not None else 0
        isils_event_count = len(self.isils_event_data) if hasattr(self, 'isils_event_data') and self.isils_event_data is not None else 0
        num_events = max(sils_event_count, isils_event_count)
        for idx in range(num_events):
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # ISILS Safe Path (option이 "both" 또는 "isils"인 경우)
            if option in ("both", "isils") and idx < len(self.isils_safe_paths):
                route_isils = self.get_safe_path(self.isils_safe_paths, idx)
                if route_isils:
                    lat_isils, lon_isils = self.get_route_coordinates(route_isils)
                    ax.plot(lon_isils, lat_isils, marker='o', linestyle=':', 
                            color='dodgerblue', label='ISILS Safe Path')
            
            # SILS Safe Path (option이 "both" 또는 "sils"인 경우)
            if option in ("both", "sils"):
                route_sils = self.get_safe_path(self.sils_safe_paths, idx)
                if route_sils:
                    lat_sils, lon_sils = self.get_route_coordinates(route_sils)
                    ax.plot(lon_sils, lat_sils, marker='o', linestyle=':',
                            color='darkorange', label='SILS Safe Path')
            
            # Base Route (공통)
            if self.base_route:
                lat_base, lon_base = self.get_route_coordinates(self.base_route)
                ax.plot(lon_base, lat_base, marker='o', linestyle='-', 
                        color='black', label='Base Route')
            
            # Own Ship 표시 (배 모양으로 그리기)
            # SILS Own Ship
            if option in ("both", "sils") and idx < len(self.sils_own_ship_event_info) and self.sils_own_ship_event_info[idx]:
                try:
                    ship_length = self.sils_own_ship_info["length"]
                    ship_width = self.sils_own_ship_info["width"]

                    ship_data = self.sils_own_ship_event_info[idx]
                    lat = ship_data["position"]["latitude"]
                    lon = ship_data["position"]["longitude"]
                    heading = ship_data.get("heading", 0)
                    # ship_length와 ship_width는 실제 m 단위 값 (필요시 static 정보에서 가져올 수 있음)
                    self.draw_ship(ax, lon, lat, heading, color='crimson',
                                   ship_length=ship_length, ship_width=ship_width)
                except Exception as e:
                    print(f"Warning: SILS own ship position error: {e}")
            # ISILS Own Ship
            if option in ("both", "isils") and idx < len(self.isils_own_ship_event_info) and self.isils_own_ship_event_info[idx]:
                try:
                    ship_length = self.isils_own_ship_info["length"]
                    ship_width = self.isils_own_ship_info["width"]
                    ship_data = self.isils_own_ship_event_info[idx]
                    lat = ship_data["position"]["latitude"]
                    lon = ship_data["position"]["longitude"]
                    heading = ship_data.get("heading", 0)
                    self.draw_ship(ax, lon, lat, heading, color='limegreen',
                                   ship_length=ship_length, ship_width=ship_width)
                except Exception as e:
                    print(f"Warning: ISILS own ship position error: {e}")
            
            # SILS Target Ships
            if option in ("both", "sils") and idx < len(self.sils_target_ships_event_info):
                for tidx, target in enumerate(self.flatten(self.sils_target_ships_event_info[idx])):
                    if not isinstance(target, dict):
                        print(f"Warning: SILS target이 dict가 아님: {target}")
                        continue
                    try:
                        t_lat = target["position"]["latitude"]
                        t_lon = target["position"]["longitude"]
                    except Exception as e:
                        print(f"Warning: SILS target position error: {e}, 대상: {target}")
                        continue
                    label = "SILS Target Ship" if tidx == 0 else None
                    ax.scatter(t_lon, t_lat, color='firebrick', marker='x', s=80, label=label)
                    # 방향 벡터 그리기
                    if "cog" in target and "sog" in target:
                        try:
                            cog = float(target["cog"])
                            sog = float(target["sog"])
                            max_sog = 20.0
                            arrow_length = (min(max(sog, 0), max_sog) / max_sog) * 0.05
                            angle_rad = math.radians(cog)
                            dx = arrow_length * math.sin(angle_rad)
                            dy = arrow_length * math.cos(angle_rad)
                            ax.annotate('', xy=(t_lon + dx, t_lat + dy), xytext=(t_lon, t_lat),
                                        arrowprops=dict(arrowstyle='->', linestyle='dashed',
                                                        color='firebrick', linewidth=1,
                                                        shrinkA=0, shrinkB=0, fill=False))
                        except Exception as e:
                            print(f"Warning: SILS target cog/sog error: {e}, 대상: {target}")
            
            # ISILS Target Ships
            if option in ("both", "isils") and idx < len(self.isils_target_ships_event_info):
                for tidx, target in enumerate(self.flatten(self.isils_target_ships_event_info[idx])):
                    if not isinstance(target, dict):
                        print(f"Warning: ISILS target이 dict가 아님: {target}")
                        continue
                    try:
                        t_lat = target["position"]["latitude"]
                        t_lon = target["position"]["longitude"]
                    except Exception as e:
                        print(f"Warning: ISILS target position error: {e}, 대상: {target}")
                        continue
                    label = "ISILS Target Ship" if tidx == 0 else None
                    ax.scatter(t_lon, t_lat, color='purple', marker='x', s=80, label=label)
                    if "cog" in target and "sog" in target:
                        try:
                            cog = float(target["cog"])
                            sog = float(target["sog"])
                            max_sog = 20.0
                            arrow_length = (min(max(sog, 0), max_sog) / max_sog) * 0.05
                            angle_rad = math.radians(cog)
                            dx = arrow_length * math.sin(angle_rad)
                            dy = arrow_length * math.cos(angle_rad)
                            ax.annotate('', xy=(t_lon + dx, t_lat + dy), xytext=(t_lon, t_lat),
                                        arrowprops=dict(arrowstyle='->', linestyle='dashed',
                                                        color='purple', linewidth=1,
                                                        shrinkA=0, shrinkB=0, fill=False))
                        except Exception as e:
                            print(f"Warning: ISILS target cog/sog error: {e}, 대상: {target}")

            # 이벤트마다 SILS 관련 텍스트 추가 (좌측 상단/우측 상단)
            if hasattr(self, 'sils_event_data') and self.sils_event_data:
                # 인덱스 범위 내에서 해당 이벤트의 플래그 값을 가져와 조건 검사
                if hasattr(self, 'is_path_gen_fail_sils') and idx < len(self.is_path_gen_fail_sils) and self.is_path_gen_fail_sils[idx]:
                    ax.text(0.05, 0.95, "SILS safe_path_gen fail", transform=ax.transAxes,
                            fontsize=12, color='red', verticalalignment='top',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                if hasattr(self, 'is_near_target_sils') and idx < len(self.is_near_target_sils) and self.is_near_target_sils[idx]:
                    ax.text(0.95, 0.95, "SILS Near target", transform=ax.transAxes,
                            fontsize=12, color='blue', verticalalignment='top',
                            horizontalalignment='right',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

            # ISILS 관련 텍스트 추가 (약간 아래쪽, y=0.90)
            if hasattr(self, 'isils_event_data') and self.isils_event_data:
                if hasattr(self, 'is_path_gen_fail_isils') and idx < len(self.is_path_gen_fail_isils) and self.is_path_gen_fail_isils[idx]:
                    ax.text(0.05, 0.90, "ISILS safe_path_gen fail", transform=ax.transAxes,
                            fontsize=12, color='red', verticalalignment='top',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                if hasattr(self, 'is_near_target_isils') and idx < len(self.is_near_target_isils) and self.is_near_target_isils[idx]:
                    ax.text(0.95, 0.90, "ISILS Near target", transform=ax.transAxes,
                            fontsize=12, color='blue', verticalalignment='top',
                            horizontalalignment='right',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                            
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.set_title(f"Event {idx} - Safe Paths, Target Ships & Own Ship Positions")
            
            # base route를 기준으로 축을 정사각형으로 설정 (있을 경우)
            self.set_axis_limits_based_on_base_route(ax)
            
            ax.legend()
            ax.grid(True)
            fig.savefig(output_path_pattern.format(idx))
            plt.close(fig)
            print(f"플롯이 {output_path_pattern.format(idx)}에 저장되었습니다.")



if __name__ == "__main__":
    # 폴더 경로 설정 (직접 입력)
    sils_folder = "sils_results/ver013_20250213_6_20250213T104604/output"      # SILS 파일들이 위치한 폴더 (marzip 또는 json)
    isils_folder = "output/2025-02-10 04:56:56.934941"                   # ISILS 파일들이 위치한 폴더 (보통 json)
    
    parent_dir = os.path.dirname(sils_folder)
    folder_name = os.path.basename(parent_dir)
    result_dir = os.path.join("plot_result", folder_name)    
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    # 옵션 딕셔너리 설정
    # "plot": 플롯 대상 ("both", "sils", "isils")
    # "sils_mode": SILS 데이터 로드 방식 ("marzip" 또는 "json")
    # "isils_mode": ISILS 데이터 로드 방식 ("marzip" 또는 "json")
    options = {
        "plot": "sils",
        "sils_mode": "marzip",
        "isils_mode": "json"
    }

    # FileInputManager 인스턴스 생성 (각 폴더를 직접 입력)
    file_manager = FileInputManager(sils_folder=sils_folder, isils_folder=isils_folder)

    # SILS 폴더 내 파일 목록 가져오기 (옵션에 따라 marzip 또는 json 파일)
    sils_files = file_manager.get_sils_files(mode=options["sils_mode"])

    # 각 SILS 파일에 대해 처리 (ISILS 파일은 동일한 기본 이름을 가진 것으로 가정)
    for sils_file in sils_files:
        base_name = os.path.splitext(os.path.basename(sils_file))[0]
        print(f"Processing {base_name} ...")

        # SILS 데이터 로드 (옵션에 따라)
        sils_data = file_manager.load_sils_data(sils_file, mode=options["sils_mode"])
        
        # ISILS 파일 경로 구성 (같은 기본 이름, 옵션에 따른 확장자)
        isils_ext = ".marzip" if options["isils_mode"] == "marzip" else ".json"
        isils_file = os.path.join(isils_folder, base_name + isils_ext)
        # ISILS 데이터 로드 (옵션에 따라)
        isils_data = file_manager.load_isils_data(isils_file, mode=options["isils_mode"])
        
        if sils_data is None and isils_data is None:
            print(f"{base_name}: 데이터 로드 실패, 스킵합니다.")
            continue

        # 결과 플롯 파일 이름 패턴 생성 (예: plot_result/scen_301_event{}.png)
        output_pattern = os.path.join(result_dir, f"{base_name}_event{{}}.png")
        
        # RoutePlotter 인스턴스 생성 후 플롯 생성 (플롯 옵션은 options["plot"] 사용)
        route_plotter = RoutePlotter(sils_json_data=sils_data, isils_json_data=isils_data)
        route_plotter.plot_all(output_pattern, option=options["plot"])
