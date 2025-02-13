import math
import os
import json
import matplotlib
matplotlib.use("Agg")  # GUI 백엔드 설정 (파일로 저장)
import matplotlib.pyplot as plt
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
        num_events = len(self.sils_safe_paths)  # SILS Safe Path 기준 이벤트 수
        for idx in range(num_events):
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # ISILS Safe Path (option이 "both" 또는 "isils"인 경우)
            if option in ("both", "isils") and idx < len(self.isils_safe_paths):
                route_isils = self.isils_safe_paths[idx]
                lat_isils, lon_isils = self.get_route_coordinates(route_isils)
                ax.plot(lon_isils, lat_isils, marker='o', linestyle=':', 
                        color='dodgerblue', label='ISILS Safe Path')
            
            # SILS Safe Path (option이 "both" 또는 "sils"인 경우)
            if option in ("both", "sils") and idx < len(self.sils_safe_paths):
                route_sils = self.sils_safe_paths[idx]
                lat_sils, lon_sils = self.get_route_coordinates(route_sils)
                ax.plot(lon_sils, lat_sils, marker='o', linestyle=':', 
                        color='darkorange', label='SILS Safe Path')
            
            # Base Route (공통)
            if self.base_route:
                lat_base, lon_base = self.get_route_coordinates(self.base_route)
                ax.plot(lon_base, lat_base, marker='o', linestyle='-', 
                        color='black', label='Base Route')
            
            # Own Ship 표시
            if option in ("both", "sils") and idx < len(self.sils_own_ship) and self.sils_own_ship[idx]:
                try:
                    sils_lat = self.sils_own_ship[idx]["position"]["latitude"]
                    sils_lon = self.sils_own_ship[idx]["position"]["longitude"]
                    ax.scatter(sils_lon, sils_lat, color='crimson', marker='*', s=150, label='SILS Own Ship')
                except Exception as e:
                    print(f"Warning: SILS own ship position error: {e}")
            if option in ("both", "isils") and idx < len(self.isils_own_ship) and self.isils_own_ship[idx]:
                try:
                    isils_lat = self.isils_own_ship[idx]["position"]["latitude"]
                    isils_lon = self.isils_own_ship[idx]["position"]["longitude"]
                    ax.scatter(isils_lon, isils_lat, color='limegreen', marker='*', s=150, label='ISILS Own Ship')
                except Exception as e:
                    print(f"Warning: ISILS own ship position error: {e}")
            
            # SILS Target Ships
            if option in ("both", "sils") and idx < len(self.sils_target_ships):
                for tidx, target in enumerate(self.flatten(self.sils_target_ships[idx])):
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
            if option in ("both", "isils") and idx < len(self.isils_target_ships):
                for tidx, target in enumerate(self.flatten(self.isils_target_ships[idx])):
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
    sils_folder = "sils_results/ver013_dnv_20250213T131633/output"      # SILS 파일들이 위치한 폴더 (marzip 또는 json)
    isils_folder = "output/2025-02-10 04:56:56.934941"                   # ISILS 파일들이 위치한 폴더 (보통 json)
    
    result_dir = "plot_result"
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    # 옵션 딕셔너리 설정
    # "plot": 플롯 대상 ("both", "sils", "isils")
    # "sils_mode": SILS 데이터 로드 방식 ("marzip" 또는 "json")
    # "isils_mode": ISILS 데이터 로드 방식 ("marzip" 또는 "json")
    options = {
        "plot": "sils",
        "sils_mode": "json",
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
