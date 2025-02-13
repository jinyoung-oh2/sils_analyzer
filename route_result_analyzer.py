import os
import csv
import json
import math
import re
from route_extracter import RouteExtractor
from file_input_manager import FileInputManager

class RouteResultAnalyzer(RouteExtractor):
    """
    SILS와 ISILS 데이터를 분석하여, 각 파일별로
    ca_path_gen_fail 플래그를 기준으로 "Success", "Fail", 또는 "NA"를 판정하는 클래스.
    - 이벤트가 0개이면 결과는 "NA"
    - 이벤트가 1개이면, 해당 이벤트의 플래그가 True이면 "NA", False이면 "Success"
    - 이벤트가 여러 개이면, 모든 플래그가 False이면 "Success", 하나라도 True가 있으면 "Fail"
    """
    def __init__(self, sils_json_data, isils_json_data):
        super().__init__(sils_json_data, isils_json_data)

    def analyze_dataset(self, events_info):
        """
        events_info 리스트를 받아 ca_path_gen_fail 플래그에 기반해 결과를 도출합니다.
        """
        flags = [event.get("ca_path_gen_fail") for event in events_info if event.get("ca_path_gen_fail") is not None]
        count = len(flags)
        if count == 0:
            return "NA"
        elif count == 1:
            return "NA" if flags[0] is True else "Success"
        else:
            return "Success" if all(flag is False for flag in flags) else "Fail"

    def analyze(self, option="both"):
        """
        옵션에 따라 SILS, ISILS 또는 두 데이터를 분석합니다.
        반환 예시:
          {"SILS": "Success", "ISILS": "Fail"}
        """
        analysis = {}
        if option in ("sils", "both"):
            analysis["SILS"] = self.analyze_dataset(self.sils_events_info)
        if option in ("isils", "both"):
            analysis["ISILS"] = self.analyze_dataset(self.isils_events_info)
        return analysis

def write_csv(results, output_csv):
    """
    results: 리스트의 딕셔너리, 각 항목은 {"File": <파일명>, "Result": <결과>} 형태
    output_csv: 저장할 CSV 파일 경로
    """
    fieldnames = ["File", "Result"]
    with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

class RouteAnalysisRunner:
    """
    SILS와 ISILS 파일들을 읽어 분석을 수행하고,
    각각의 결과를 별도의 CSV 파일로 저장하는 클래스.
    분석 옵션에 따라 SILS 또는 ISILS 또는 두 데이터를 분석합니다.
    """
    def __init__(self, sils_folder, isils_folder, options):
        self.sils_folder = sils_folder
        self.isils_folder = isils_folder
        self.options = options
        self.file_manager = FileInputManager(sils_folder=sils_folder, isils_folder=isils_folder)
        
        parent_dir = os.path.dirname(sils_folder)
        folder_name = os.path.basename(parent_dir)
        self.result_dir = os.path.join("analysis_result", folder_name)
        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)
        # 분석 대상에 따라 결과 CSV 파일 생성
        self.output_sils_csv = os.path.join(self.result_dir, "route_analysis_sils.csv")
        self.output_isils_csv = os.path.join(self.result_dir, "route_analysis_isils.csv")

    def add_summary_row(self, results):
        """
        결과 리스트에 요약 행을 추가합니다.
        예: Success: 3, Fail: 2, NA: 1
        """
        count_success = sum(1 for r in results if r["Result"] == "Success")
        count_fail = sum(1 for r in results if r["Result"] == "Fail")
        count_na = sum(1 for r in results if r["Result"] == "NA")
        summary_str = f"Success: {count_success}, Fail: {count_fail}, NA: {count_na}"
        results.append({"File": "Summary", "Result": summary_str})
        return results

    def run(self):
        """
        파일 목록을 자연 순서대로 처리하여 분석을 수행하고,
        각각의 결과를 별도의 CSV 파일로 저장합니다.
        """
        analyze_option = self.options["analyze"]
        sils_files = sorted(
            self.file_manager.get_sils_files(mode=self.options["sils_mode"]),
            key=lambda f: FileInputManager.natural_sort_key(os.path.basename(f))
        )
        sils_results = []
        isils_results = []

        for sils_file in sils_files:
            base_name = os.path.splitext(os.path.basename(sils_file))[0]
            print(f"Processing {base_name} ...")
            
            # SILS 데이터 로드
            sils_data = self.file_manager.load_sils_data(sils_file, mode=self.options["sils_mode"])
            
            # ISILS 파일 경로 구성 (같은 기본 이름)
            isils_ext = ".marzip" if self.options["isils_mode"] == "marzip" else ".json"
            isils_file = os.path.join(self.isils_folder, base_name + isils_ext)
            isils_data = self.file_manager.load_isils_data(isils_file, mode=self.options["isils_mode"])
            
            if sils_data is None and isils_data is None:
                print(f"{base_name}: 데이터 로드 실패, 스킵합니다.")
                continue
            
            analyzer = RouteResultAnalyzer(sils_json_data=sils_data, isils_json_data=isils_data)
            # 실제 분석은 옵션에 맞게 수행
            analysis = analyzer.analyze(option=analyze_option)
            
            if analyze_option in ("sils", "both"):
                sils_result = analysis.get("SILS", "N/A")
                sils_results.append({"File": base_name, "Result": sils_result})
            if analyze_option in ("isils", "both"):
                isils_result = analysis.get("ISILS", "N/A")
                isils_results.append({"File": base_name, "Result": isils_result})
        
        # 결과 CSV 파일 생성: 옵션에 따라 해당 결과만 저장하고, 마지막에 요약 행 추가
        if analyze_option in ("sils", "both") and sils_results:
            sils_results = self.add_summary_row(sils_results)
            write_csv(sils_results, self.output_sils_csv)
            print(f"SILS 분석 결과가 {self.output_sils_csv}에 저장되었습니다.")
        if analyze_option in ("isils", "both") and isils_results:
            isils_results = self.add_summary_row(isils_results)
            write_csv(isils_results, self.output_isils_csv)
            print(f"ISILS 분석 결과가 {self.output_isils_csv}에 저장되었습니다.")

if __name__ == "__main__":
    # 폴더 경로 설정 (직접 입력)
    sils_folder = "sils_results/ver013_20250213_6_20250213T104604/output"  # SILS 파일들이 위치한 폴더
    isils_folder = "output/2025-02-10 04:56:56.934941"                      # ISILS 파일들이 위치한 폴더
    
    # 옵션 설정
    # "analyze": 분석 대상 ("both", "sils", "isils")
    # "sils_mode": SILS 데이터 로드 방식 ("marzip" 또는 "json"), None이면 로드 안 함
    # "isils_mode": ISILS 데이터 로드 방식 ("marzip" 또는 "json"), None이면 로드 안 함
    options = {
        "analyze": "sils",   # 여기서 "sils"로 설정하면 SILS 데이터만 분석합니다.
        "sils_mode": "marzip",
        "isils_mode": None
    }
    
    runner = RouteAnalysisRunner(sils_folder, isils_folder, options)
    runner.run()
