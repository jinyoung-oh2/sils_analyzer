import json

def safe_get(data, keys, default=None):
    """
    중첩 딕셔너리에서 키 체인을 따라 안전하게 값을 가져옵니다.
    """
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
            if data == default:
                return default
        else:
            return default
    return data

class RouteExtractor:
    """
    SILS와 ISILS JSON 데이터에서 Base Route, Own Ship의 정적 정보,
    그리고 이벤트 관련 정보를 통합하여 추출하는 클래스입니다.
    
    이벤트 관련 정보는 각 이벤트에서 아래 데이터를 추출합니다.
      - safe_route:  cagaData → eventData → safe_path_info → route
      - target_ships:  cagaData → eventData → timeSeriesData → targetShips (리스트 평탄화 적용)
      - own_ship_event:  cagaData → eventData → timeSeriesData → ownShip
      - ca_path_gen_fail:  cagaData → eventData → caPathGenFail
      - is_near_target:  cagaData → eventData → isNearTarget
    """
    def __init__(self, sils_json_data, isils_json_data):
        self.base_route = self.extract_base_route(sils_json_data)
        self.own_ship_static_sils = self.extract_own_ship_static_info(sils_json_data)
        self.own_ship_static_isils = self.extract_own_ship_static_info(isils_json_data)
        
        # 이벤트 정보를 통합 추출
        self.sils_events_info = self.extract_events_info(sils_json_data)
        self.isils_events_info = self.extract_events_info(isils_json_data)

    def flatten(self, item):
        """
        재귀적으로 리스트를 평탄화하여 모든 중첩을 풀어줍니다.
        예: [[a, b], c, [d, [e, f]]] => [a, b, c, d, e, f]
        """
        if isinstance(item, list):
            result = []
            for sub in item:
                result.extend(self.flatten(sub))
            return result
        else:
            return [item]

    def extract_base_route(self, data):
        """
        Base Route 추출 (trafficSituation → ownShip → waypoints)
        """
        return safe_get(data, ["trafficSituation", "ownShip", "waypoints"], default=[])

    def extract_own_ship_static_info(self, data):
        """
        Own Ship의 정적(static) 정보 추출 (trafficSituation → ownShip → static)
        """
        return safe_get(data, ["trafficSituation", "ownShip", "static"], default={})

    def extract_events_info(self, data):
        """
        이벤트 정보를 통합하여 추출합니다.
        각 이벤트에서 아래 데이터를 딕셔너리 형태로 추출하여 리스트로 반환합니다.
        """
        events = []
        event_data = safe_get(data, ["cagaData", "eventData"], default=[])
        if isinstance(event_data, list):
            for event in event_data:
                event_info = {}
                event_info["safe_route"] = safe_get(event, ["safe_path_info", "route"])
                
                # targetShips: 리스트가 아닐 경우 리스트로 변환 후 평탄화 적용
                target_ships = safe_get(event, ["timeSeriesData", "targetShips"], default=[])
                if not isinstance(target_ships, list):
                    target_ships = [target_ships]
                event_info["target_ships"] = self.flatten(target_ships)
                
                event_info["own_ship_event"] = safe_get(event, ["timeSeriesData", "ownShip"])
                event_info["ca_path_gen_fail"] = safe_get(event, ["caPathGenFail"])
                event_info["is_near_target"] = safe_get(event, ["isNearTarget"])
                events.append(event_info)
        return events
