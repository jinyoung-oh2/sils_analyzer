import math
import os
import csv
from route_extracter import RouteExtractor, JSONLoader
from route_plotter import RouteExtractor
from targets_from_marzip import TargetsFromMarzip


class RouteComparer(RouteExtractor):
    """
    SILS와 ISILS의 Safe Path와 Own Ship 데이터를 비교하여,
    각 route의 waypoint 갯수, 각 waypoint마다의 거리 오차 (미터 단위)의 최대값(max error)과 합계(sum error),
    그리고 Own Ship의 거리 차이를 계산하고 CSV 파일로 저장하는 클래스.
    """
    def __init__(self, sils_json_data, isils_json_data):
        super().__init__(sils_json_data, isils_json_data)

    def haversine(self, lat1, lon1, lat2, lon2):
        """
        두 좌표 간의 거리를 미터 단위로 계산하는 함수 (Haversine 공식)
        """
        R = 6371000  # 지구 반경 (미터)
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def compare_routes(self):
        """
        각 route별로 SILS와 ISILS의 각 waypoint 간의 거리 차이를 계산하여,
        waypoint 갯수, 최대 오차(max error) 및 오차 합계(sum error)를 리스트로 반환.
        """
        results = []
        # 두 safe_paths의 route 갯수는 같지 않을 수 있으므로, 최소 갯수만 비교
        num_routes = min(len(self.sils_safe_paths), len(self.isils_safe_paths))
        for i in range(num_routes):
            route_sils = self.sils_safe_paths[i]
            route_isils = self.isils_safe_paths[i]
            n = min(len(route_sils), len(route_isils))
            error_sum = 0.0
            max_error = 0.0
            for j in range(n):
                lat1 = route_sils[j]["position"]["latitude"]
                lon1 = route_sils[j]["position"]["longitude"]
                lat2 = route_isils[j]["position"]["latitude"]
                lon2 = route_isils[j]["position"]["longitude"]
                d = self.haversine(lat1, lon1, lat2, lon2)
                error_sum += d
                if d > max_error:
                    max_error = d
            results.append({
                "route_index": i,
                "waypoint_count_sils": len(route_sils),
                "waypoint_count_isils": len(route_isils),
                "max_error_m": max_error,
                "sum_error_m": error_sum
            })
        return results

    def compare_ownship(self):
        """
        두 Own Ship 위치 간의 거리 차이를 미터 단위로 계산.
        """
        if self.sils_ship_position and self.isils_ship_position:
            lat1 = self.sils_ship_position["latitude"]
            lon1 = self.sils_ship_position["longitude"]
            lat2 = self.isils_ship_position["latitude"]
            lon2 = self.isils_ship_position["longitude"]
            return self.haversine(lat1, lon1, lat2, lon2)
        else:
            return None

    def write_csv(self, csv_filename):
        """
        비교 결과를 CSV 파일로 저장.
        첫 부분은 각 route에 대한 비교 결과,
        마지막 부분에 Own Ship 거리 차이를 기록.
        """
        route_results = self.compare_routes()
        ownship_diff = self.compare_ownship()
        with open(csv_filename, "w", newline="") as csvfile:
            fieldnames = ["Route Index", "Waypoint Count SILS", "Waypoint Count ISILS", "Max Error (m)", "Sum Error (m)"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for res in route_results:
                writer.writerow({
                    "Route Index": res["route_index"],
                    "Waypoint Count SILS": res["waypoint_count_sils"],
                    "Waypoint Count ISILS": res["waypoint_count_isils"],
                    "Max Error (m)": res["max_error_m"],
                    "Sum Error (m)": res["sum_error_m"]
                })
            # 빈 행 삽입
            writer.writerow({})
            writer.writerow({"Route Index": "Ownship Diff (m)", "Waypoint Count SILS": ownship_diff})
        print(f"CSV 결과가 {csv_filename}에 저장되었습니다.")


# --- 배치 처리 예제 (폴더 입력받아 처리) ---
if __name__ == "__main__":
    # marzip 파일들이 있는 폴더와 ISILS JSON 파일들이 있는 폴더 경로
    marzip_folder = "scenarios_marzip/output"
    isils_json_folder = "output/2025-02-10 04:56:56.934941"

    # 결과 이미지를 저장할 폴더 생성 (없으면 생성)
    result_dir = "result"
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    # CSV 결과 파일 경로
    csv_output_file = os.path.join(result_dir, "comparison_results.csv")

    # 배치 처리 결과들을 저장할 리스트 (각 파일의 비교 결과)
    all_route_comparisons = []
    all_ownship_diffs = []

    # marzip_folder 내의 모든 .marzip 파일에 대해 처리
    for filename in os.listdir(marzip_folder):
        if filename.endswith(".marzip"):
            marzip_file = os.path.join(marzip_folder, filename)
            # marzip 파일의 base 이름 (예: "scen_301")
            base_name = os.path.splitext(filename)[0]
            # 대응하는 ISILS JSON 파일은 isils_json_folder 내에 base_name + ".json" 형태로 가정
            isils_json_file = os.path.join(isils_json_folder, f"{base_name}.json")
            if not os.path.exists(isils_json_file):
                print(f"Warning: ISILS JSON 파일이 {marzip_file}에 대해 존재하지 않습니다.")
                continue

            # marzip 파일 처리
            marzip_data = TargetsFromMarzip(marzip_file).extract_and_read_marzip()
            sils_json_data = marzip_data["simulation_result"]
            isils_json_data = JSONLoader(json_file=isils_json_file).load()

            # 비교 결과 계산 (RouteComparer 용 데이터 준비)
            comparer = RouteComparer(sils_json_data, isils_json_data)
            # 여기서 compare_routes()를 호출하여 route_results를 구함
            route_results = comparer.compare_routes()
            ownship_diff = comparer.compare_ownship()

            # 각 marzip 파일에 대한 결과에 base_name 추가
            for res in route_results:
                res["base_name"] = base_name
            all_route_comparisons.extend(route_results)
            all_ownship_diffs.append({"base_name": base_name, "ownship_diff_m": ownship_diff})

    # CSV 파일 생성: 경로 비교 결과와 Own Ship 차이 결과를 하나의 CSV에 기록
    with open(csv_output_file, "w", newline="") as csvfile:
        fieldnames = ["base_name", "Route Index", "Waypoint Count SILS", "Waypoint Count ISILS", "Max Error (m)", "Sum Error (m)", "Ownship Diff (m)"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        # 각 route 비교 결과에 해당 marzip 파일의 ownship diff를 추가 (같은 base_name)
        for res in all_route_comparisons:
            own_diff = next((item["ownship_diff_m"] for item in all_ownship_diffs if item["base_name"] == res["base_name"]), None)
            row = {
                "base_name": res["base_name"],
                "Route Index": res["route_index"],
                "Waypoint Count SILS": res["waypoint_count_sils"],
                "Waypoint Count ISILS": res["waypoint_count_isils"],
                "Max Error (m)": res["max_error_m"],
                "Sum Error (m)": res["sum_error_m"],
                "Ownship Diff (m)": own_diff
            }
            writer.writerow(row)
    print(f"CSV 결과가 {csv_output_file}에 저장되었습니다.")
