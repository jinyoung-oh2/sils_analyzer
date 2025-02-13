import os
import zipfile
import json
import shutil
from datetime import datetime

import pyarrow as pa
import pyarrow.ipc as ipc


class TargetsFromMarzip:
    """
    (.marzip) 파일에서 데이터를 추출하는 클래스

    예상 데이터 형식 예시:
    - timeseries_dataset:
        {
            'lon': 1.0752216810515859e-37,
            'lat': -6.149712445530087e-08,
            'sog': 10.0,
            'timeStamp': datetime(2024, 10, 1, 10, 0, 10),
            'cog': 359.9999998410674,
            'heading': 359.9999998410674,
            'id': 0,
            'scenario_id': 310
        }
    - static_dataset:
        {
            'id': 1,
            'length': 100.0,
            'width': 20.0,
            'shipType': '70',
            'a': 50,
            'b': 50,
            'c': 10,
            'd': 10,
            'name': 'Ship 1',
            'ownShip': False,
            'scenario_id': 310
        }
    """

    def __init__(self, file_path):
        """
        :param file_path: .marzip 파일의 경로
        """
        self.file_path = file_path
        self.simulation_result = {}

    def _read_arrow_file(self, file_path):
        """
        주어진 Arrow 파일을 읽어 pyarrow Table로 반환.
        IPC File Format이 실패하면 Streaming Format으로 읽음.
        """
        with open(file_path, 'rb') as f:
            try:
                reader = ipc.RecordBatchFileReader(f)
                return reader.read_all()
            except pa.lib.ArrowInvalid:
                # 파일 포인터 재설정 후 스트리밍 포맷 시도
                f.seek(0)
                try:
                    reader = ipc.RecordBatchStreamReader(f)
                    return reader.read_all()
                except pa.lib.ArrowInvalid as e:
                    raise e

    def extract_and_read_marzip(self):
        """
        .marzip 파일을 압축해제하여 각 파일의 데이터를 읽은 후,
        timeseries 및 static 데이터셋을 반환한다.
        또한 result.json 파일의 내용은 simulation_result에 저장한다.
        
        :return: dict
            {
                "timeseries_dataset": [...],
                "static_dataset": [...]
            }
        """
        extracted_files = []
        extract_dir = None

        # 파일이 ZIP 형식인지 확인
        if zipfile.is_zipfile(self.file_path):
            with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
                # .marzip 확장자를 제거한 디렉토리명 사용
                extract_dir = os.path.splitext(self.file_path)[0]
                zip_ref.extractall(extract_dir)
                extracted_files = [
                    os.path.join(extract_dir, name) for name in zip_ref.namelist()
                ]
        else:
            raise ValueError("제공된 파일은 올바른 .marzip 아카이브가 아닙니다.")

        timeseries_dataset = []
        static_dataset = []

        # 압축 해제된 파일들을 순회하며 데이터 읽기
        for file in extracted_files:
            if file.endswith('timeseries.arrow'):
                try:
                    table = self._read_arrow_file(file)
                    # to_pylist()로 각 row를 dict로 변환하여 리스트에 추가
                    timeseries_dataset.extend(table.to_pylist())
                except Exception as e:
                    print(f"파일 {file} 읽기 오류: {e}")
            elif file.endswith('static.arrow'):
                try:
                    table = self._read_arrow_file(file)
                    static_dataset.extend(table.to_pylist())
                except Exception as e:
                    print(f"파일 {file} 읽기 오류: {e}")
            elif file.endswith('.json'):
                try:
                    with open(file, 'r') as json_file:
                        self.simulation_result = json.load(json_file)
                except Exception as e:
                    print(f"JSON 파일 {file} 읽기 오류: {e}")

        # 압축 해제한 디렉토리 삭제
        if extract_dir and os.path.exists(extract_dir):
            try:
                shutil.rmtree(extract_dir)
            except Exception as e:
                print(f"추출된 디렉토리 삭제 실패: {e}")

        return {
            "timeseries_dataset": timeseries_dataset,
            "static_dataset": static_dataset,
            "simulation_result": self.simulation_result

        }


if __name__ == "__main__":
    file_path = "scenarios/marzip/output.marzip"  # 사용할 파일 경로로 수정
    try:
        target_information = TargetsFromMarzip(file_path).extract_and_read_marzip()
        print("파일 처리가 성공적으로 완료되었습니다.")
    except Exception as e:
        print(f"파일 처리에 실패했습니다: {e}")
