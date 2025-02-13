import os
import json
from targets_from_marzip import TargetsFromMarzip
import re

class FileInputManager:
    """
    파일 입력 관련 기능을 제공하는 클래스.
    """
    def __init__(self, sils_folder, isils_folder):
        """
        :param sils_folder: SILS 파일들이 위치한 폴더 경로  
                           (marzip 파일이 있거나, json 파일이 있을 수 있음)
        :param isils_folder: ISILS 파일들이 위치한 폴더 경로  
                           (marzip 파일이 있거나, json 파일이 있을 수 있음)
        """
        self.sils_folder = sils_folder
        self.isils_folder = isils_folder

    @staticmethod
    def natural_sort_key(s):
        """
        파일 이름 등 문자열 내 숫자들을 정수로 변환하여 자연 정렬할 수 있는 키를 생성합니다.
        예: "scen_1", "scen_2", "scen_10" -> ["scen_", 1, "scen_", 2, "scen_", 10]
        """
        return [int(text) if text.isdigit() else text.lower() for text in re.split('(\d+)', s)]


    def get_files(self, folder, extension):
        """
        지정한 폴더 내의 특정 확장자를 가진 파일들의 전체 경로 리스트를 반환.
        """
        if not os.path.exists(folder):
            raise FileNotFoundError(f"폴더를 찾을 수 없습니다: {folder}")
        return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(extension)]

    def get_sils_files(self, mode="marzip"):
        """
        SILS 폴더 내의 파일 목록을 반환.
        mode가 "marzip"이면 ".marzip", "json"이면 ".json" 파일을 찾음.
        mode가 None이면 빈 리스트를 반환.
        """
        if mode is None:
            return []
        ext = ".marzip" if mode == "marzip" else ".json"
        return self.get_files(self.sils_folder, ext)

    def get_isils_files(self, mode="json"):
        """
        ISILS 폴더 내의 파일 목록을 반환.
        mode가 "marzip"이면 ".marzip", "json"이면 ".json" 파일을 찾음.
        mode가 None이면 빈 리스트를 반환.
        """
        if mode is None:
            return []
        ext = ".marzip" if mode == "marzip" else ".json"
        return self.get_files(self.isils_folder, ext)

    def load_marzip(self, file_path):
        """
        단일 marzip 파일을 로드하여 데이터를 반환.
        """
        try:
            data = TargetsFromMarzip(file_path).extract_and_read_marzip()
            return data
        except Exception as e:
            print(f"마르지프 파일 로드 오류 ({file_path}): {e}")
            return None

    def load_json(self, file_path):
        """
        단일 JSON 파일을 로드하여 데이터를 반환.
        """
        try:
            with open(file_path, 'r', encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"JSON 파일 로드 오류 ({file_path}): {e}")
            return None

    def load_sils_data(self, file_path, mode="marzip"):
        """
        SILS 데이터를 로드하는 함수.
        
        :param file_path: 기준 파일 경로 (SILS 폴더 내 파일)
        :param mode: "marzip"이면 marzip 내부에서, "json"이면 해당 json 파일에서 로드.
                     mode가 None이면 None 반환.
        :return: SILS 데이터 (dict) 또는 None
        """
        if mode is None:
            return None

        if mode == "marzip":
            data = self.load_marzip(file_path)
            return data.get("simulation_result") if data else None
        elif mode == "json":
            return self.load_json(file_path)
        else:
            raise ValueError("mode는 'marzip' 또는 'json'이어야 합니다.")

    def load_isils_data(self, file_path, mode="json"):
        """
        ISILS 데이터를 로드하는 함수.
        
        :param file_path: 기준 파일 경로 (ISILS 폴더 내 파일)
        :param mode: "json"이면 해당 json 파일에서, "marzip"이면 marzip 내부에서 로드.
                     mode가 None이면 None 반환.
        :return: ISILS 데이터 (dict) 또는 None
        """
        if mode is None:
            return None

        if mode == "json":
            return self.load_json(file_path)
        elif mode == "marzip":
            data = self.load_marzip(file_path)
            # isils 데이터가 marzip 내부에 있다면 "isils_result" 키로 관리한다고 가정
            return data.get("isils_result") if data else None
        else:
            raise ValueError("mode는 'json' 또는 'marzip'이어야 합니다.")
